
-- ==============================================================================
-- ASTRA SENSE – ORBITAL GUARD
-- Supabase Stored Procedures & Reconciliation Functions
-- Version: 00003_reconciliation_and_triggers.sql
-- Description: Atomic inventory reconciliation and timestamp triggers
-- ==============================================================================

-- 1. Automatic Timestamp Update Trigger Function

CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


-- Attach timestamp triggers to mutable tables

DROP TRIGGER IF EXISTS trigger_update_astronauts_time
ON public.astronauts;

CREATE TRIGGER trigger_update_astronauts_time
    BEFORE UPDATE ON public.astronauts
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();


DROP TRIGGER IF EXISTS trigger_update_inventory_time
ON public.medical_inventory;

CREATE TRIGGER trigger_update_inventory_time
    BEFORE UPDATE ON public.medical_inventory
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();


DROP TRIGGER IF EXISTS trigger_update_recovery_time
ON public.recovery_timelines;

CREATE TRIGGER trigger_update_recovery_time
    BEFORE UPDATE ON public.recovery_timelines
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();


-- 2. Transactional Inventory Ledger Reconciliation Function

CREATE OR REPLACE FUNCTION public.reconcile_inventory_transaction(
    p_transaction_id VARCHAR(64),
    p_item_id VARCHAR(32),
    p_delta_quantity INTEGER,
    p_operation_type VARCHAR(32),
    p_authorized_by VARCHAR(64),
    p_patient_id VARCHAR(32) DEFAULT NULL,
    p_timestamp_met VARCHAR(32) DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$

DECLARE
    v_existing_ledger RECORD;
    v_item RECORD;
    v_new_stock INTEGER;
    v_new_status TEXT;

BEGIN

    -- Check for duplicate transaction (Idempotency check)

    SELECT *
    INTO v_existing_ledger
    FROM public.cloud_sync_ledger
    WHERE transaction_id = p_transaction_id;

    IF FOUND THEN

        SELECT stock, status
        INTO v_item
        FROM public.medical_inventory
        WHERE id = p_item_id;

        RETURN jsonb_build_object(
            'status', 'IDEMPOTENT_IGNORED',
            'transaction_id', p_transaction_id,
            'message', 'Transaction already reconciled in cloud ledger.',
            'current_stock', v_item.stock,
            'item_status', v_item.status
        );

    END IF;


    -- Fetch item from inventory and lock row

    SELECT *
    INTO v_item
    FROM public.medical_inventory
    WHERE id = p_item_id
    FOR UPDATE;

    IF NOT FOUND THEN

        -- Record conflict: Item missing in cloud

        INSERT INTO public.cloud_sync_conflicts (
            id,
            entity_type,
            record_id,
            local_payload,
            conflict_reason,
            resolution_status
        )
        VALUES (
            'CONF-' || p_transaction_id,
            'medical_inventory',
            p_item_id,
            jsonb_build_object(
                'transaction_id', p_transaction_id,
                'delta', p_delta_quantity,
                'operation', p_operation_type
            ),
            'Inventory item ' || p_item_id ||
            ' does not exist in cloud database.',
            'UNRESOLVED'
        );

        RETURN jsonb_build_object(
            'status', 'CONFLICT_RECORDED',
            'reason', 'ITEM_NOT_FOUND',
            'item_id', p_item_id
        );

    END IF;


    -- Calculate new stock

    v_new_stock := v_item.stock + p_delta_quantity;


    -- Negative stock validation

    IF v_new_stock < 0 THEN

        -- Record conflict: Overdrawn inventory

        INSERT INTO public.cloud_sync_conflicts (
            id,
            entity_type,
            record_id,
            local_payload,
            cloud_payload,
            conflict_reason,
            resolution_status
        )
        VALUES (
            'CONF-' || p_transaction_id,
            'medical_inventory',
            p_item_id,
            jsonb_build_object(
                'transaction_id', p_transaction_id,
                'delta', p_delta_quantity,
                'requested_by', p_authorized_by
            ),
            jsonb_build_object(
                'available_stock', v_item.stock,
                'current_status', v_item.status
            ),
            'Transaction would result in negative inventory balance (' ||
            v_new_stock ||
            '). Preserved for manual review.',
            'UNRESOLVED'
        );

        RETURN jsonb_build_object(
            'status', 'CONFLICT_RECORDED',
            'reason', 'NEGATIVE_STOCK_DEFICIT',
            'available_stock', v_item.stock,
            'requested_delta', p_delta_quantity
        );

    END IF;


    -- Determine updated stock warning status

    v_new_status := v_item.status;

    IF v_new_stock <= v_item."minSafeStock" THEN

        v_new_status := 'Low Reserve Warning';

    ELSIF
        v_new_stock > v_item."minSafeStock"
        AND v_item.status = 'Low Reserve Warning'
    THEN

        v_new_status := 'Optimal';

    END IF;


    -- Apply inventory adjustment

    UPDATE public.medical_inventory
    SET
        stock = v_new_stock,
        status = v_new_status,
        updated_at = NOW()
    WHERE id = p_item_id;


    -- Append to immutable transaction ledger

    INSERT INTO public.cloud_sync_ledger (
        transaction_id,
        item_id,
        delta_quantity,
        operation_type,
        authorized_by,
        patient_id,
        timestamp_met,
        created_at
    )
    VALUES (
        p_transaction_id,
        p_item_id,
        p_delta_quantity,
        p_operation_type,
        p_authorized_by,
        p_patient_id,
        p_timestamp_met,
        NOW()
    );


    -- Return successful reconciliation result

    RETURN jsonb_build_object(
        'status', 'RECONCILED',
        'transaction_id', p_transaction_id,
        'item_id', p_item_id,
        'delta', p_delta_quantity,
        'previous_stock', v_item.stock,
        'new_stock', v_new_stock,
        'new_status', v_new_status
    );

END;
$$;


-- 3. Security Hardening

REVOKE ALL ON FUNCTION public.reconcile_inventory_transaction(
    VARCHAR,
    VARCHAR,
    INTEGER,
    VARCHAR,
    VARCHAR,
    VARCHAR,
    VARCHAR
) FROM PUBLIC, anon;

GRANT EXECUTE ON FUNCTION public.reconcile_inventory_transaction(
    VARCHAR,
    VARCHAR,
    INTEGER,
    VARCHAR,
    VARCHAR,
    VARCHAR,
    VARCHAR
) TO service_role;

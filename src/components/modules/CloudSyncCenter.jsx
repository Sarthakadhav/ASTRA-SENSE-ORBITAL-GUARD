import React, { useState } from 'react';
import { 
  Cloud, CloudOff, RefreshCw, AlertTriangle, CheckCircle2, 
  Clock, Database, ArrowRight, Shield, Layers, HelpCircle, AlertCircle
} from 'lucide-react';
import { useMission } from '../../context/MissionContext';

export const CloudSyncCenter = () => {
  const {
    syncStatus,
    syncMetrics,
    streamHealth,
    syncConflicts,
    outboxEvents,
    isSyncing,
    triggerManualSync,
    retryFailedSync,
    resolveConflictAction,
    refreshSyncData,
    currentUser
  } = useMission();

  const [filterEntity, setFilterEntity] = useState('ALL');
  const [showSetupGuide, setShowSetupGuide] = useState(false);
  const [actionMessage, setActionMessage] = useState(null);

  const getStatusBadge = (state) => {
    switch (state) {
      case 'CLOUD_CONNECTED':
        return {
          label: 'CLOUD CONNECTED',
          bg: 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800/50',
          dot: 'bg-emerald-500'
        };
      case 'SYNC_PENDING':
        return {
          label: `SYNC PENDING (${syncStatus.pending_count})`,
          bg: 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800/50',
          dot: 'bg-amber-500'
        };
      case 'SYNC_IN_PROGRESS':
        return {
          label: 'SYNC IN PROGRESS',
          bg: 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/40 dark:text-blue-300 dark:border-blue-800/50',
          dot: 'bg-blue-500 animate-pulse'
        };
      case 'CONFLICT_DETECTED':
        return {
          label: `CONFLICT DETECTED (${syncStatus.unresolved_conflicts})`,
          bg: 'bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-800/50',
          dot: 'bg-rose-500'
        };
      case 'SYNC_FAILED':
        return {
          label: 'SYNC FAILED',
          bg: 'bg-red-50 text-red-700 border-red-200 dark:bg-red-950/40 dark:text-red-300 dark:border-red-800/50',
          dot: 'bg-red-500'
        };
      case 'LOCAL_ONLY':
      default:
        return {
          label: 'LOCAL ONLY (OFFLINE-FIRST)',
          bg: 'bg-slate-100 text-slate-700 border-slate-200 dark:bg-neutral-800 dark:text-slate-300 dark:border-neutral-700',
          dot: 'bg-slate-400'
        };
    }
  };

  const badge = getStatusBadge(syncStatus.pipeline_state);

  const handleManualSyncClick = async () => {
    setActionMessage('Initiating batch upload to Supabase...');
    const res = await triggerManualSync();
    if (res && res.status === 'COMPLETED') {
      setActionMessage(`Batch completed: ${res.synced} synced, ${res.failed} failed.`);
    } else {
      setActionMessage(res?.message || 'Sync batch executed.');
    }
    setTimeout(() => setActionMessage(null), 5000);
  };

  const handleRetryClick = async () => {
    setActionMessage('Queuing failed outbox events for retry...');
    const res = await retryFailedSync();
    setActionMessage(res?.message || 'Retry queued.');
    setTimeout(() => setActionMessage(null), 5000);
  };

  const filteredEvents = outboxEvents.filter(evt => {
    if (filterEntity === 'ALL') return true;
    return evt.entity_type === filterEntity;
  });

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-gray-100 dark:border-[#24252a] gap-3">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs uppercase tracking-wider text-gray-400 font-medium">
              Module 8 – Cloud Synchronization & Data Security
            </span>
            <span className={`px-2 py-0.5 text-[10px] font-mono font-bold tracking-wider rounded-md border inline-flex items-center space-x-1.5 ${badge.bg}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${badge.dot}`}></span>
              <span>{badge.label}</span>
            </span>
          </div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mt-1">
            Hybrid Database Synchronization Center
          </h2>
          <p className="text-xs text-gray-400 mt-0.5">
            Local SQLite Write-Ahead Logging (WAL) acts as the autonomous microgravity flight core. Supabase PostgreSQL serves as the delay-tolerant cloud backup and mission control replication target.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => setShowSetupGuide(!showSetupGuide)}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-gray-200 dark:border-[#333] text-gray-600 dark:text-gray-300 text-xs hover:bg-gray-50 dark:hover:bg-[#202126] transition-colors"
          >
            <HelpCircle className="w-3.5 h-3.5 text-gray-400" />
            <span>Setup Guide</span>
          </button>

          <button
            onClick={handleRetryClick}
            disabled={isSyncing || syncStatus.failed_count === 0}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-gray-200 dark:border-[#333] text-gray-600 dark:text-gray-300 text-xs hover:bg-gray-50 dark:hover:bg-[#202126] transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin' : ''}`} />
            <span>Retry Failed</span>
          </button>

          <button
            onClick={handleManualSyncClick}
            disabled={isSyncing}
            className="flex items-center space-x-1.5 px-4 py-1.5 rounded-lg bg-neutral-900 text-white dark:bg-white dark:text-neutral-900 text-xs font-medium hover:bg-neutral-800 transition-colors shadow-sm disabled:opacity-50"
          >
            <Cloud className="w-3.5 h-3.5" />
            <span>{isSyncing ? 'Syncing...' : 'Sync Outbox Now'}</span>
          </button>
        </div>
      </div>

      {/* Action Notification Banner */}
      {actionMessage && (
        <div className="p-3 rounded-xl bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-900/40 text-xs text-blue-900 dark:text-blue-200 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse"></span>
            <span>{actionMessage}</span>
          </div>
          <button onClick={() => setActionMessage(null)} className="text-xs text-blue-500 hover:underline">
            Dismiss
          </button>
        </div>
      )}

      {/* Architecture & Offline Guarantee Card */}
      <div className="bg-white dark:bg-[#1a1b1f] border border-gray-100 dark:border-[#27282e] rounded-2xl p-5 shadow-sm space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-start space-x-3.5">
            <div className="p-2.5 rounded-xl bg-gray-50 dark:bg-[#202126] text-gray-700 dark:text-gray-200 border border-gray-100 dark:border-[#2a2c33] shrink-0">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                Offline-First Dual Database Architecture
              </h3>
              <p className="text-xs text-gray-400 mt-0.5 leading-relaxed">
                Critical astronaut health decisions never block on internet connectivity. Telemetry ingestion, Isolation Forest scoring, and safety rules execute locally in SQLite WAL mode (&lt;1ms). Pending records are queued in the transactional outbox and uploaded whenever connectivity opens.
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3 bg-gray-50/70 dark:bg-[#202126] px-4 py-2.5 rounded-xl border border-gray-100 dark:border-[#2a2c33] text-xs shrink-0">
            <div className="text-center">
              <div className="font-semibold text-gray-900 dark:text-gray-100">SQLite 3 (WAL)</div>
              <div className="text-[10px] text-gray-400">Microgravity Core</div>
            </div>
            <ArrowRight className="w-3.5 h-3.5 text-gray-400" />
            <div className="text-center">
              <div className="font-semibold text-gray-900 dark:text-gray-100">Supabase (PostgreSQL)</div>
              <div className="text-[10px] text-gray-400">Earth Ground Sync</div>
            </div>
          </div>
        </div>
      </div>

      {/* Setup Guide Accordion (If Toggled) */}
      {showSetupGuide && (
        <div className="bg-white dark:bg-[#1a1b1f] border border-amber-200/60 dark:border-amber-900/40 rounded-2xl p-6 shadow-sm space-y-4">
          <div className="flex items-start justify-between">
            <div className="flex items-center space-x-2">
              <Shield className="w-4 h-4 text-amber-600 dark:text-amber-400" />
              <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                Supabase Project Setup & Security Configuration
              </h3>
            </div>
            <button
              onClick={() => setShowSetupGuide(false)}
              className="text-xs text-gray-400 hover:text-gray-600"
            >
              Close Guide
            </button>
          </div>

          <p className="text-xs text-gray-600 dark:text-gray-300 leading-relaxed">
            To connect a live cloud database to ORBITAL GUARD, configure your Supabase project using the official migrations:
          </p>

          <ol className="list-decimal list-inside text-xs text-gray-600 dark:text-gray-300 space-y-2">
            <li>
              <strong>Create a Supabase Project:</strong> Log in to <span className="font-mono text-neutral-900 dark:text-neutral-100">supabase.com</span>, create a new project, and retrieve the Project URL and Service Role Key from <em>Project Settings &gt; API</em>.
            </li>
            <li>
              <strong>Execute Version-Controlled Migrations:</strong> In the Supabase SQL Editor, run the migration scripts located in <span className="font-mono text-neutral-900 dark:text-neutral-100">supabase/migrations/</span> in order:
              <ul className="list-disc list-inside pl-4 pt-1 space-y-0.5 text-gray-500">
                <li><span className="font-mono">00001_initial_schema.sql</span> (Creates tables, foreign keys, and indexes)</li>
                <li><span className="font-mono">00002_row_level_security.sql</span> (Enables RLS and access policies)</li>
                <li><span className="font-mono">00003_reconciliation_and_triggers.sql</span> (Configures transaction reconciliation)</li>
              </ul>
            </li>
            <li>
              <strong>Set Backend Environment Variables:</strong> In your <span className="font-mono text-neutral-900 dark:text-neutral-100">backend/.env</span> file, configure:
              <pre className="mt-1 p-2.5 rounded-lg bg-gray-50 dark:bg-[#121316] font-mono text-[11px] text-gray-800 dark:text-gray-200 overflow-x-auto">
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-backend-service-role-secret-key
SUPABASE_ANON_KEY=your-anon-public-key
              </pre>
            </li>
            <li>
              <strong>Run Initial Migration Backfill:</strong> Run <span className="font-mono">python scripts/migrate_sqlite_to_supabase.py</span> to upload all existing historical telemetry, astronaut profiles, and dispensations.
            </li>
          </ol>
        </div>
      )}

      {/* KPI Metrics Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3.5">
        <div className="bg-white dark:bg-[#1a1b1f] border border-gray-100 dark:border-[#27282e] rounded-xl p-4 shadow-sm space-y-1">
          <span className="text-[11px] uppercase tracking-wider text-gray-400 font-medium block">
            Cloud Connection
          </span>
          <div className="text-base font-semibold text-gray-900 dark:text-gray-100">
            {syncStatus.cloud_status}
          </div>
          <span className="text-[10px] text-gray-400 block truncate">
            {syncStatus.cloud_configured ? 'Target Configured' : 'Local Standalone Mode'}
          </span>
        </div>

        <div className="bg-white dark:bg-[#1a1b1f] border border-gray-100 dark:border-[#27282e] rounded-xl p-4 shadow-sm space-y-1">
          <span className="text-[11px] uppercase tracking-wider text-gray-400 font-medium block">
            Outbox Pending
          </span>
          <div className="text-base font-semibold text-amber-600 dark:text-amber-400">
            {syncStatus.pending_count}
          </div>
          <span className="text-[10px] text-gray-400 block">
            {syncStatus.retry_count} retrying
          </span>
        </div>

        <div className="bg-white dark:bg-[#1a1b1f] border border-gray-100 dark:border-[#27282e] rounded-xl p-4 shadow-sm space-y-1">
          <span className="text-[11px] uppercase tracking-wider text-gray-400 font-medium block">
            Confirmed Synced
          </span>
          <div className="text-base font-semibold text-emerald-600 dark:text-emerald-400">
            {syncStatus.synced_count}
          </div>
          <span className="text-[10px] text-gray-400 block">
            Persistent in cloud
          </span>
        </div>

        <div className="bg-white dark:bg-[#1a1b1f] border border-gray-100 dark:border-[#27282e] rounded-xl p-4 shadow-sm space-y-1">
          <span className="text-[11px] uppercase tracking-wider text-gray-400 font-medium block">
            Failed Events
          </span>
          <div className={`text-base font-semibold ${syncStatus.failed_count > 0 ? 'text-rose-600' : 'text-gray-900 dark:text-gray-100'}`}>
            {syncStatus.failed_count}
          </div>
          <span className="text-[10px] text-gray-400 block">
            Max retries exceeded
          </span>
        </div>

        <div className="bg-white dark:bg-[#1a1b1f] border border-gray-100 dark:border-[#27282e] rounded-xl p-4 shadow-sm space-y-1">
          <span className="text-[11px] uppercase tracking-wider text-gray-400 font-medium block">
            Unresolved Conflicts
          </span>
          <div className={`text-base font-semibold ${syncStatus.unresolved_conflicts > 0 ? 'text-rose-600' : 'text-gray-900 dark:text-gray-100'}`}>
            {syncStatus.unresolved_conflicts}
          </div>
          <span className="text-[10px] text-gray-400 block">
            Requires human review
          </span>
        </div>
      </div>

      {/* Phase 3: High-Resolution Observability & Quality Gauges */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
        <div className="bg-white dark:bg-[#1a1b1f] border border-gray-100 dark:border-[#27282e] rounded-xl p-4 shadow-sm space-y-2">
          <div className="flex items-center justify-between text-xs text-gray-500">
            <span className="font-medium uppercase tracking-wider text-[10px]">Sync System Health</span>
            <span className="font-mono font-bold text-emerald-500">
              {syncMetrics?.system_health_score ?? 100}%
            </span>
          </div>
          <div className="w-full bg-gray-100 dark:bg-[#25262c] h-2 rounded-full overflow-hidden">
            <div
              className="bg-emerald-500 h-full rounded-full transition-all duration-500"
              style={{ width: `${syncMetrics?.system_health_score ?? 100}%` }}
            ></div>
          </div>
          <div className="flex justify-between text-[10px] text-gray-400 pt-1">
            <span>Protocol: {syncMetrics?.protocol || 'PostgREST / HTTPS'}</span>
            <span>Latency: {syncMetrics?.latency_ms ?? 14.2}ms</span>
          </div>
        </div>

        <div className="bg-white dark:bg-[#1a1b1f] border border-gray-100 dark:border-[#27282e] rounded-xl p-4 shadow-sm space-y-2">
          <div className="flex items-center justify-between text-xs text-gray-500">
            <span className="font-medium uppercase tracking-wider text-[10px]">Outbox Backlog Buffer</span>
            <span className="font-mono font-bold text-blue-500">
              {syncMetrics?.outbox_backlog_pct ?? 0}%
            </span>
          </div>
          <div className="w-full bg-gray-100 dark:bg-[#25262c] h-2 rounded-full overflow-hidden">
            <div
              className="bg-blue-500 h-full rounded-full transition-all duration-500"
              style={{ width: `${Math.min(100, Math.max(2, syncMetrics?.outbox_backlog_pct ?? 0))}%` }}
            ></div>
          </div>
          <div className="flex justify-between text-[10px] text-gray-400 pt-1">
            <span>DLQ Isolated: {syncMetrics?.dead_letter_events ?? 0}</span>
            <span>Total Events: {syncMetrics?.total_outbox_events ?? 394}</span>
          </div>
        </div>

        <div className="bg-white dark:bg-[#1a1b1f] border border-gray-100 dark:border-[#27282e] rounded-xl p-4 shadow-sm space-y-2">
          <div className="flex items-center justify-between text-xs text-gray-500">
            <span className="font-medium uppercase tracking-wider text-[10px]">Telemetry Stream Quality</span>
            <span className="font-mono font-bold text-emerald-500">
              {streamHealth?.stream_quality_score ?? 100}%
            </span>
          </div>
          <div className="w-full bg-gray-100 dark:bg-[#25262c] h-2 rounded-full overflow-hidden">
            <div
              className="bg-emerald-500 h-full rounded-full transition-all duration-500"
              style={{ width: `${streamHealth?.stream_quality_score ?? 100}%` }}
            ></div>
          </div>
          <div className="flex justify-between text-[10px] text-gray-400 pt-1">
            <span>Gaps: {streamHealth?.sequence_gaps_count ?? 0}</span>
            <span>Deduplicated: {streamHealth?.duplicates_dropped_count ?? 0}</span>
          </div>
        </div>
      </div>

      {/* Unresolved Conflicts Section (If Any) */}
      {syncConflicts && syncConflicts.length > 0 && (
        <div className="bg-white dark:bg-[#1a1b1f] border border-rose-200 dark:border-rose-900/50 rounded-2xl p-6 shadow-sm space-y-4">
          <div className="flex items-center space-x-2 text-rose-700 dark:text-rose-300">
            <AlertCircle className="w-5 h-5" />
            <h3 className="text-sm font-semibold">
              Unresolved Cloud Synchronization Conflicts ({syncConflicts.length})
            </h3>
          </div>
          <p className="text-xs text-gray-500">
            To prevent accidental data loss, conflicting local and cloud updates are preserved for authorized clinical review.
          </p>

          <div className="space-y-3">
            {syncConflicts.map(conf => (
              <div 
                key={conf.id}
                className="p-4 rounded-xl bg-rose-50/50 dark:bg-rose-950/20 border border-rose-100 dark:border-rose-900/40 text-xs space-y-2.5"
              >
                <div className="flex items-center justify-between">
                  <div className="font-semibold text-gray-900 dark:text-gray-100">
                    Conflict {conf.id} • {conf.entity_type} ({conf.record_id})
                  </div>
                  <span className="text-[10px] text-gray-400">{conf.created_at}</span>
                </div>
                <div className="text-rose-800 dark:text-rose-300">
                  Reason: {conf.conflict_reason}
                </div>
                <div className="flex items-center space-x-2 pt-2 border-t border-rose-100 dark:border-rose-900/40">
                  <button
                    onClick={() => resolveConflictAction(conf.id, 'RESOLVED_LOCAL')}
                    className="px-2.5 py-1 rounded bg-neutral-900 text-white dark:bg-white dark:text-neutral-900 text-[11px] font-medium"
                  >
                    Keep Local (Flight Mode)
                  </button>
                  <button
                    onClick={() => resolveConflictAction(conf.id, 'RESOLVED_CLOUD')}
                    className="px-2.5 py-1 rounded border border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-200 text-[11px]"
                  >
                    Accept Cloud (Earth Override)
                  </button>
                  <button
                    onClick={() => resolveConflictAction(conf.id, 'RESOLVED_MERGE')}
                    className="px-2.5 py-1 rounded border border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-200 text-[11px]"
                  >
                    Acknowledge & Mark Resolved
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Outbox Queue Live Audit Table */}
      <div className="bg-white dark:bg-[#1a1b1f] border border-gray-100 dark:border-[#27282e] rounded-2xl p-6 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
              Local Transactional Outbox Queue ({outboxEvents.length} Recent Events)
            </h3>
            <p className="text-xs text-gray-400 mt-0.5">
              Live inspection of events committed to local SQLite and queued for Supabase replication.
            </p>
          </div>

          <div className="flex items-center space-x-1.5 bg-gray-50 dark:bg-[#1e2025] p-1 rounded-lg border border-gray-100 dark:border-[#28292e] text-xs">
            {['ALL', 'telemetry_history', 'medical_inventory', 'health_alerts', 'incidents', 'astronauts'].map(type => (
              <button
                key={type}
                onClick={() => setFilterEntity(type)}
                className={`px-2.5 py-1 rounded-md transition-colors ${
                  filterEntity === type
                    ? 'bg-white dark:bg-[#15161a] text-gray-900 dark:text-white font-medium shadow-sm'
                    : 'text-gray-500 hover:text-gray-900 dark:hover:text-white'
                }`}
              >
                {type === 'ALL' ? 'All' : type.replace('_', ' ')}
              </button>
            ))}
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="text-gray-400 uppercase tracking-wider border-b border-gray-50 dark:border-[#24252a] text-[11px]">
                <th className="pb-3 font-normal">Event ID</th>
                <th className="pb-3 font-normal">Entity</th>
                <th className="pb-3 font-normal">Record ID</th>
                <th className="pb-3 font-normal">Operation</th>
                <th className="pb-3 font-normal">Attempts</th>
                <th className="pb-3 font-normal">Created At</th>
                <th className="pb-3 font-normal text-right">Outbox Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50 dark:divide-[#24252a]">
              {filteredEvents.length === 0 ? (
                <tr>
                  <td colSpan="7" className="py-8 text-center text-gray-400">
                    No outbox events matching filter. All transactions are up to date.
                  </td>
                </tr>
              ) : (
                filteredEvents.map(evt => {
                  const isSuccess = evt.status === 'SYNCED';
                  const isPending = evt.status === 'PENDING' || evt.status === 'PROCESSING';
                  const isRetry = evt.status === 'RETRY';
                  const isFailed = evt.status === 'FAILED';

                  return (
                    <tr key={evt.id} className="hover:bg-gray-50/50 dark:hover:bg-[#202126]">
                      <td className="py-3 font-mono text-[11px] text-gray-600 dark:text-gray-300">
                        {evt.id}
                      </td>
                      <td className="py-3 font-medium text-gray-900 dark:text-gray-100">
                        {evt.entity_type}
                      </td>
                      <td className="py-3 font-mono text-[11px] text-gray-500">
                        {evt.record_id}
                      </td>
                      <td className="py-3 font-semibold text-gray-700 dark:text-gray-300">
                        {evt.operation}
                      </td>
                      <td className="py-3 text-gray-500">
                        {evt.attempt_count}
                      </td>
                      <td className="py-3 text-gray-400">
                        {evt.created_at}
                      </td>
                      <td className="py-3 text-right">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-mono font-medium ${
                          isSuccess
                            ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300'
                            : isPending
                            ? 'bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300'
                            : isRetry
                            ? 'bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300'
                            : 'bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300'
                        }`}>
                          {evt.status}
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};


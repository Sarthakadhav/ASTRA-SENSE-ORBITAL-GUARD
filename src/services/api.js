/**
 * ORBITAL GUARD / ASTRA SENSE API Client
 * Connects React frontend directly to the Python FastAPI backend.
 * All critical safety and monitoring logic functions 100% offline.
 */

const API_BASE = '/api/v1';

const getHeaders = (extra = {}) => {
  const token = localStorage.getItem('orbital_auth_token');
  const headers = { 'Content-Type': 'application/json', ...extra };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
};

export const orbitalApi = {
  // --- Module 1 & 2: Telemetry & Simulator ---
  async ingestTelemetry(packet) {
    const res = await fetch(`${API_BASE}/telemetry/ingest`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(packet)
    });
    if (!res.ok) throw new Error(`Telemetry ingest failed: ${res.statusText}`);
    return res.json();
  },

  async getSimulationScenarios() {
    const res = await fetch(`${API_BASE}/telemetry/simulator/scenarios`, {
      headers: getHeaders()
    });
    if (!res.ok) throw new Error(`Failed to load simulation scenarios: ${res.statusText}`);
    return res.json();
  },

  async stepSimulation(astronautId = 'AST-01', scenarioMode = 'NORMAL', tick = 0, customParams = null) {
    const res = await fetch(`${API_BASE}/telemetry/simulator/step`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({
        astronaut_id: astronautId,
        scenario_mode: scenarioMode,
        tick,
        custom_params: customParams
      })
    });
    if (!res.ok) throw new Error(`Simulator step failed: ${res.statusText}`);
    return res.json();
  },

  async resetSimulation(astronautId = null) {
    const url = astronautId
      ? `${API_BASE}/telemetry/simulator/reset?astronaut_id=${encodeURIComponent(astronautId)}`
      : `${API_BASE}/telemetry/simulator/reset`;
    const res = await fetch(url, { method: 'POST', headers: getHeaders() });
    if (!res.ok) throw new Error(`Simulator reset failed: ${res.statusText}`);
    return res.json();
  },

  async getTelemetryHistory(astronautId = 'AST-01', limit = 50) {
    const res = await fetch(`${API_BASE}/telemetry/history/${astronautId}?limit=${limit}`, {
      headers: getHeaders()
    });
    if (!res.ok) throw new Error(`Get telemetry history failed: ${res.statusText}`);
    return res.json();
  },

  async getLatestTelemetry(astronautId = 'AST-01') {
    const res = await fetch(`${API_BASE}/telemetry/latest/${astronautId}`, {
      headers: getHeaders()
    });
    if (!res.ok) throw new Error(`Get latest telemetry failed: ${res.statusText}`);
    return res.json();
  },

  // --- Module 2: Health & ML Anomaly Detection ---
  async getAstronautHealth(astronautId) {
    const res = await fetch(`${API_BASE}/health/${astronautId}`, {
      headers: getHeaders()
    });
    if (!res.ok) throw new Error(`Get astronaut health failed: ${res.statusText}`);
    return res.json();
  },

  async getPersonalBaseline(astronautId) {
    const res = await fetch(`${API_BASE}/health/${astronautId}/baseline`, {
      headers: getHeaders()
    });
    if (!res.ok) throw new Error(`Get personal baseline failed: ${res.statusText}`);
    return res.json();
  },

  async runIsolationForest(payload) {
    const res = await fetch(`${API_BASE}/ml/isolation-forest`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error(`ML scoring failed: ${res.statusText}`);
    return res.json();
  },

  // --- Module 3: Crew Profiles & Readiness ---
  async getCrew() {
    const res = await fetch(`${API_BASE}/crew`, { headers: getHeaders() });
    if (!res.ok) throw new Error(`Get crew failed: ${res.statusText}`);
    return res.json();
  },

  async getCrewReadiness() {
    const res = await fetch(`${API_BASE}/crew/readiness`, { headers: getHeaders() });
    if (!res.ok) throw new Error(`Get readiness failed: ${res.statusText}`);
    return res.json();
  },

  async redistributeWorkload(primaryId = 'AST-01', backupId = 'AST-02', approvedBy = 'Cmdr. Sarah Chen', reason = 'Elevated neuro-fatigue and cognitive latency drift (+185ms)') {
    const res = await fetch(`${API_BASE}/crew/redistribute`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({
        primary_astronaut_id: primaryId,
        backup_astronaut_id: backupId,
        approved_by: approvedBy,
        reason: reason
      })
    });
    if (!res.ok) throw new Error(`Redistribution failed: ${res.statusText}`);
    return res.json();
  },

  async resetCrewSimulation() {
    const res = await fetch(`${API_BASE}/crew/reset`, { method: 'POST', headers: getHeaders() });
    if (!res.ok) throw new Error(`Crew reset failed: ${res.statusText}`);
    return res.json();
  },

  // --- Module 4: Med Vault ---
  async getInventory() {
    const res = await fetch(`${API_BASE}/inventory`, { headers: getHeaders() });
    if (!res.ok) throw new Error(`Get inventory failed: ${res.statusText}`);
    return res.json();
  },

  async consumeInventory(itemId, quantity = 1, reason = 'Emergency consumption', authorizedBy = 'Dr. Elena Vance', patientId = 'AST-01') {
    const res = await fetch(`${API_BASE}/inventory/consume`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({
        item_id: itemId,
        quantity,
        reason,
        authorized_by: authorizedBy,
        patient_id: patientId
      })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Consume inventory failed: ${res.statusText}`);
    }
    return res.json();
  },

  async replenishInventory(itemId, quantity, authorizedBy = 'Cmdr. Sarah Chen', notes = 'Station restock') {
    const res = await fetch(`${API_BASE}/inventory/replenish`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({
        item_id: itemId,
        quantity,
        authorized_by: authorizedBy,
        notes
      })
    });
    if (!res.ok) throw new Error(`Replenish inventory failed: ${res.statusText}`);
    return res.json();
  },

  async createInventoryItem(itemData) {
    const res = await fetch(`${API_BASE}/inventory/item`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(itemData)
    });
    if (!res.ok) throw new Error(`Create inventory item failed: ${res.statusText}`);
    return res.json();
  },

  async getDispensations() {
    const res = await fetch(`${API_BASE}/inventory/dispensations`, { headers: getHeaders() });
    if (!res.ok) throw new Error(`Get dispensations failed: ${res.statusText}`);
    return res.json();
  },

  // --- Module 5: Hybrid Flight AI Assistant & SOP Retrieval ---
  async askAssistant(question, astronautId = 'AST-01') {
    const res = await fetch(`${API_BASE}/assistant/ask`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ question, astronaut_id: astronautId, include_vitals: true })
    });
    if (!res.ok) throw new Error(`Assistant query failed: ${res.statusText}`);
    return res.json();
  },

  // --- Module 6: Alerts & Incidents ---
  async getAlerts(statusFilter = null) {
    const url = statusFilter ? `${API_BASE}/alerts?status_filter=${statusFilter}` : `${API_BASE}/alerts`;
    const res = await fetch(url, { headers: getHeaders() });
    if (!res.ok) throw new Error(`Get alerts failed: ${res.statusText}`);
    return res.json();
  },

  async acknowledgeAlert(alertId, officerId = 'Cmdr. Sarah Chen', notes = '') {
    const res = await fetch(`${API_BASE}/alerts/${alertId}/acknowledge`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ officer_id: officerId, notes })
    });
    if (!res.ok) throw new Error(`Acknowledge alert failed: ${res.statusText}`);
    return res.json();
  },

  async resolveAlert(alertId, officerId = 'Cmdr. Sarah Chen', resolutionNotes = 'Condition returned to nominal') {
    const res = await fetch(`${API_BASE}/alerts/${alertId}/resolve`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ officer_id: officerId, resolution_notes: resolutionNotes })
    });
    if (!res.ok) throw new Error(`Resolve alert failed: ${res.statusText}`);
    return res.json();
  },

  async getIncidents() {
    const res = await fetch(`${API_BASE}/incidents`, { headers: getHeaders() });
    if (!res.ok) throw new Error(`Get incidents failed: ${res.statusText}`);
    return res.json();
  },

  async createIncident(incidentData) {
    const res = await fetch(`${API_BASE}/incidents`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(incidentData)
    });
    if (!res.ok) throw new Error(`Create incident failed: ${res.statusText}`);
    return res.json();
  },

  async resolveIncident(incidentId, notes = 'Issue verified and resolved locally.', resolvedBy = 'Cmdr. Sarah Chen') {
    const res = await fetch(`${API_BASE}/incidents/${incidentId}/resolve`, {
      method: 'PATCH',
      headers: getHeaders(),
      body: JSON.stringify({ resolution_notes: notes, resolved_by: resolvedBy })
    });
    if (!res.ok) throw new Error(`Resolve incident failed: ${res.statusText}`);
    return res.json();
  },

  async getRecoveryTimelines() {
    const res = await fetch(`${API_BASE}/recovery`, { headers: getHeaders() });
    if (!res.ok) throw new Error(`Get recovery timelines failed: ${res.statusText}`);
    return res.json();
  },

  // --- DSN Earth Sync ---
  async getDsnQueue() {
    const res = await fetch(`${API_BASE}/dsn/queue`, { headers: getHeaders() });
    if (!res.ok) throw new Error(`Get DSN queue failed: ${res.statusText}`);
    return res.json();
  },

  async syncDsnQueue() {
    const res = await fetch(`${API_BASE}/dsn/sync-queue`, { method: 'POST', headers: getHeaders() });
    if (!res.ok) throw new Error(`DSN sync failed: ${res.statusText}`);
    return res.json();
  },

  // --- Authentication ---
  async login(username, password) {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Authentication failed');
    }
    const data = await res.json();
    if (data.token) {
      localStorage.setItem('orbital_auth_token', data.token);
    }
    return data;
  },

  async getCurrentUser() {
    const res = await fetch(`${API_BASE}/auth/me`, { headers: getHeaders() });
    if (!res.ok) throw new Error(`Get user info failed: ${res.statusText}`);
    return res.json();
  },

  async logout() {
    const res = await fetch(`${API_BASE}/auth/logout`, { method: 'POST', headers: getHeaders() });
    localStorage.removeItem('orbital_auth_token');
    return res.json();
  },

  // --- System & Drills ---
  async getSystemStatus() {
    const res = await fetch(`${API_BASE}/system/status`, { headers: getHeaders() });
    if (!res.ok) throw new Error(`System status failed: ${res.statusText}`);
    return res.json();
  },

  async triggerEmergencyDrill(scenarioId = 'SCENARIO-02') {
    const res = await fetch(`${API_BASE}/simulation/drill`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ scenario_id: scenarioId })
    });
    if (!res.ok) throw new Error(`Drill failed: ${res.statusText}`);
    return res.json();
  },

  // --- Phase 2: Supabase Cloud Synchronization & Security ---
  async getSyncStatus() {
    const res = await fetch(`${API_BASE}/sync/status`, { headers: getHeaders() });
    if (!res.ok) throw new Error(`Get sync status failed: ${res.statusText}`);
    return res.json();
  },

  async getSyncMetrics() {
    const res = await fetch(`${API_BASE}/sync/metrics`, { headers: getHeaders() });
    if (!res.ok) throw new Error(`Get sync metrics failed: ${res.statusText}`);
    return res.json();
  },

  async getTelemetryStreamHealth() {
    const res = await fetch(`${API_BASE}/telemetry/stream-health`, { headers: getHeaders() });
    if (!res.ok) throw new Error(`Get stream health failed: ${res.statusText}`);
    return res.json();
  },

  async triggerSync() {
    const res = await fetch(`${API_BASE}/sync/trigger`, {
      method: 'POST',
      headers: getHeaders()
    });
    if (!res.ok) throw new Error(`Trigger sync failed: ${res.statusText}`);
    return res.json();
  },

  async retrySync() {
    const res = await fetch(`${API_BASE}/sync/retry`, {
      method: 'POST',
      headers: getHeaders()
    });
    if (!res.ok) throw new Error(`Retry sync failed: ${res.statusText}`);
    return res.json();
  },

  async getSyncConflicts() {
    const res = await fetch(`${API_BASE}/sync/conflicts`, { headers: getHeaders() });
    if (!res.ok) throw new Error(`Get conflicts failed: ${res.statusText}`);
    return res.json();
  },

  async resolveConflict(conflictId, resolutionChoice, resolvedBy = 'Flight Surgeon Dr. Robert Vance') {
    const res = await fetch(`${API_BASE}/sync/conflicts/resolve`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({
        conflict_id: conflictId,
        resolution_choice: resolutionChoice,
        resolved_by: resolvedBy
      })
    });
    if (!res.ok) throw new Error(`Resolve conflict failed: ${res.statusText}`);
    return res.json();
  },

  async getOutboxEvents(limit = 50) {
    const res = await fetch(`${API_BASE}/sync/outbox?limit=${limit}`, { headers: getHeaders() });
    if (!res.ok) throw new Error(`Get outbox failed: ${res.statusText}`);
    return res.json();
  }
};

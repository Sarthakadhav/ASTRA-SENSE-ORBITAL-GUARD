import React, { useState } from 'react';
import { 
  Plus, CheckCircle, Radio, Clock, Shield, AlertTriangle, 
  Send, Database, RefreshCw, Check 
} from 'lucide-react';
import { useMission } from '../../context/MissionContext';

export const MissionContinuity = () => {
  const { 
    incidents, recoveryTimelines, logIncident, 
    resolveIncidentAction, syncDsn, crew, currentUser, isBackendOnline 
  } = useMission();

  const [filterSeverity, setFilterSeverity] = useState('ALL');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [resolveModalInc, setResolveModalInc] = useState(null);
  const [resolveNotes, setResolveNotes] = useState('Protocol completed and vitals restored to baseline.');

  const [newInc, setNewInc] = useState({
    severity: 'WARNING',
    type: 'Elevated Neuro-Fatigue',
    targetAstronautId: 'AST-01',
    targetAstronautName: 'Dr. Elena Vance',
    summary: 'Resting heart rate drift and missing sleep debt observed.',
    actionsTaken: 'Initiated 8-hour acoustic-isolated sleep cycle.'
  });

  const [syncingDsn, setSyncingDsn] = useState(false);
  const [dsnNotice, setDsnNotice] = useState('');

  const filteredIncidents = incidents.filter(inc => {
    if (filterSeverity === 'ALL') return true;
    return inc.severity === filterSeverity;
  });

  const pendingDsnCount = incidents.filter(inc => 
    inc.syncStatus && (inc.syncStatus.includes('Queue') || inc.syncStatus.includes('Cached') || inc.syncStatus.includes('locally'))
  ).length;

  const handleCreateSubmit = async (e) => {
    e.preventDefault();
    if (!newInc.summary.trim()) return;
    const targetAst = crew.find(a => a.id === newInc.targetAstronautId);
    try {
      await logIncident({
        severity: newInc.severity,
        type: newInc.type,
        targetAstronautId: newInc.targetAstronautId,
        targetAstronautName: targetAst ? targetAst.name : newInc.targetAstronautName,
        summary: newInc.summary,
        assignedOfficer: currentUser.name,
        actionsTaken: newInc.actionsTaken ? [newInc.actionsTaken] : []
      });
      setShowCreateModal(false);
      setNewInc({
        severity: 'WARNING',
        type: 'Elevated Neuro-Fatigue',
        targetAstronautId: 'AST-01',
        targetAstronautName: 'Dr. Elena Vance',
        summary: '',
        actionsTaken: ''
      });
    } catch (err) {
      alert(`Error creating incident: ${err.message}`);
    }
  };

  const handleResolveSubmit = async (e) => {
    e.preventDefault();
    if (!resolveModalInc) return;
    try {
      await resolveIncidentAction(resolveModalInc.id, resolveNotes);
      setResolveModalInc(null);
    } catch (err) {
      alert(`Error resolving incident: ${err.message}`);
    }
  };

  const handleDsnSync = async () => {
    setSyncingDsn(true);
    try {
      const res = await syncDsn();
      setDsnNotice(`DSN uplink complete! Synced ${res?.synced_events_count || pendingDsnCount} event records across Goldstone DSN antenna.`);
      setTimeout(() => setDsnNotice(''), 4000);
    } catch (err) {
      setDsnNotice(`DSN sync error: ${err.message}`);
    } finally {
      setSyncingDsn(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* DSN Batch Sync Status Banner */}
      <div className="p-4 rounded-2xl bg-white dark:bg-[#1a1b1f] border border-gray-100 dark:border-[#27282e] flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-sm">
        <div className="flex items-center space-x-3.5">
          <div className="w-9 h-9 rounded-xl bg-neutral-900 text-white dark:bg-white dark:text-neutral-900 flex items-center justify-center shrink-0">
            <Radio className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-semibold text-xs text-gray-900 dark:text-gray-100">
                NASA Deep Space Network (DSN) Outbox
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-gray-100 dark:bg-[#25272e] text-gray-600 dark:text-gray-300">
                14m 22s Earth-Mars Delay
              </span>
            </div>
            <p className="text-xs text-gray-400 mt-0.5">
              {pendingDsnCount > 0 
                ? `${pendingDsnCount} incident records safely preserved in local SQLite, queued for Earth window.`
                : 'All clinical and telemetry records synced with Houston Mission Control.'}
            </p>
          </div>
        </div>

        <button
          onClick={handleDsnSync}
          disabled={syncingDsn || pendingDsnCount === 0}
          className="flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-neutral-900 text-white dark:bg-white dark:text-neutral-900 text-xs font-medium hover:bg-neutral-800 disabled:opacity-40 transition-colors shadow-sm self-start sm:self-auto"
        >
          {syncingDsn ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
          <span>Transmit Batch across DSN</span>
        </button>
      </div>

      {dsnNotice && (
        <div className="p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300 text-xs flex items-center space-x-2">
          <Check className="w-4 h-4" />
          <span>{dsnNotice}</span>
        </div>
      )}

      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-gray-100 dark:border-[#24252a] gap-3">
        <div>
          <span className="text-xs uppercase tracking-wider text-gray-400 font-medium">
            Module 6 – Mission Continuity
          </span>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mt-0.5">
            Incident Management & Recovery Tracker
          </h2>
          <p className="text-xs text-gray-400 mt-0.5">
            Complete audit trail of spaceflight health anomalies, clinical countermeasure steps, and rehabilitation trajectories.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center space-x-1 px-3.5 py-1.5 rounded-xl bg-neutral-900 text-white dark:bg-white dark:text-neutral-900 text-xs font-medium hover:bg-neutral-800 transition-colors shadow-sm"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Log Incident</span>
          </button>
        </div>
      </div>

      {/* Recovery Timelines */}
      <div className="bg-white dark:bg-[#1a1b1f] border border-gray-100 dark:border-[#27282e] rounded-2xl p-6 shadow-sm space-y-4">
        <div>
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
            Crew Rest & Recovery Progress
          </h3>
          <p className="text-xs text-gray-400 mt-0.5">
            Track when resting crew members will be fully recovered and ready to resume duties.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          {recoveryTimelines.map((rec, idx) => (
            <div 
              key={idx}
              className="p-5 rounded-xl bg-gray-50/70 dark:bg-[#202126] space-y-3"
            >
              <div className="flex justify-between items-baseline">
                <span className="font-medium text-gray-900 dark:text-gray-100 text-sm">
                  {rec.name}
                </span>
                <span className="font-semibold text-gray-800 dark:text-gray-200">
                  {rec.progressPercent}%
                </span>
              </div>

              <div className="w-full bg-gray-200 dark:bg-[#333] h-1.5 rounded-full overflow-hidden">
                <div
                  className="h-full bg-neutral-900 dark:bg-gray-100 rounded-full"
                  style={{ width: `${rec.progressPercent}%` }}
                />
              </div>

              <div className="space-y-1 text-gray-500 dark:text-gray-400">
                <div><strong>Protocol:</strong> {rec.protocol}</div>
                <div><strong>Current Step:</strong> {rec.currentStep}</div>
                <div><strong>Projected Return:</strong> {rec.projectedFullRecoveryMET}</div>
                <div><strong>Target:</strong> {rec.sleepDebtTarget}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Incident History Table */}
      <div className="bg-white dark:bg-[#1a1b1f] border border-gray-100 dark:border-[#27282e] rounded-2xl p-6 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-2 border-b border-gray-50 dark:border-[#24252a] gap-2">
          <div>
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
              Recent Health Events & Care Log
            </h3>
            <p className="text-xs text-gray-400 mt-0.5">
              Locally persisted clinical events queued for transmission across Deep Space Network.
            </p>
          </div>

          <div className="flex items-center space-x-1.5 text-xs">
            {['ALL', 'CRITICAL', 'WARNING', 'ADVISORY', 'NOMINAL'].map(sev => (
              <button
                key={sev}
                onClick={() => setFilterSeverity(sev)}
                className={`px-2.5 py-1 rounded-lg transition-colors ${
                  filterSeverity === sev
                    ? 'bg-neutral-900 text-white dark:bg-white dark:text-neutral-900 font-medium'
                    : 'text-gray-500 hover:text-gray-900 dark:hover:text-white'
                }`}
              >
                {sev}
              </button>
            ))}
          </div>
        </div>

        <div className="divide-y divide-gray-50 dark:divide-[#24252a] text-xs">
          {filteredIncidents.map(inc => {
            const isResolved = inc.resolutionStatus === 'Resolved' || inc.resolutionStatus === 'Auto-Recovered';
            return (
              <div key={inc.id} className="py-3.5 space-y-1.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium ${
                      inc.severity === 'CRITICAL'
                        ? 'bg-rose-50 text-rose-800 dark:bg-rose-950/40 dark:text-rose-300'
                        : inc.severity === 'WARNING'
                        ? 'bg-amber-50 text-amber-800 dark:bg-amber-950/40 dark:text-amber-300'
                        : 'bg-gray-50 text-gray-700 dark:bg-neutral-800 dark:text-gray-300'
                    }`}>
                      {inc.severity}
                    </span>
                    <span className="font-semibold text-gray-900 dark:text-gray-100">
                      {inc.type}
                    </span>
                    <span className="text-gray-400">
                      — {inc.targetAstronautName}
                    </span>
                  </div>
                  <div className="flex items-center space-x-2 text-gray-400">
                    <Clock className="w-3 h-3" />
                    <span>{inc.timestamp}</span>
                  </div>
                </div>

                <p className="text-gray-600 dark:text-gray-300 leading-relaxed">
                  {inc.summary}
                </p>

                {inc.actionsTaken && inc.actionsTaken.length > 0 && (
                  <div className="pt-1 text-[11px] text-gray-500 space-y-0.5">
                    {inc.actionsTaken.map((act, i) => (
                      <div key={i} className="flex items-center space-x-1">
                        <span>•</span>
                        <span>{act}</span>
                      </div>
                    ))}
                  </div>
                )}

                <div className="flex flex-col sm:flex-row sm:items-center justify-between text-gray-400 text-[11px] pt-1 gap-2">
                  <div className="flex items-center space-x-3">
                    <span>Officer: <strong className="text-gray-700 dark:text-gray-300">{inc.assignedOfficer}</strong></span>
                    <span>Status: <strong className={isResolved ? 'text-emerald-600' : 'text-amber-600'}>{inc.resolutionStatus}</strong></span>
                    <span className="text-emerald-700 dark:text-emerald-400 font-medium">{inc.syncStatus}</span>
                  </div>

                  {!isResolved && (
                    <button
                      onClick={() => setResolveModalInc(inc)}
                      className="self-start sm:self-auto px-2.5 py-1 rounded bg-gray-100 dark:bg-[#202126] hover:bg-gray-200 text-gray-700 dark:text-gray-200 font-medium transition-colors"
                    >
                      Resolve Incident
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Modal: Create Incident */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-[#1a1b1f] border border-gray-100 dark:border-[#2a2c33] rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-xl">
            <h3 className="font-semibold text-sm text-gray-900 dark:text-gray-100">
              Log Mission Health Incident in Local Flight Ledger
            </h3>

            <form onSubmit={handleCreateSubmit} className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-gray-600 dark:text-gray-400 mb-1">Severity</label>
                  <select
                    value={newInc.severity}
                    onChange={e => setNewInc(d => ({ ...d, severity: e.target.value }))}
                    className="w-full px-3 py-2 rounded-lg bg-gray-50 dark:bg-[#202126] border border-gray-200 dark:border-[#333] text-gray-900 dark:text-gray-100"
                  >
                    <option value="CRITICAL">CRITICAL</option>
                    <option value="WARNING">WARNING</option>
                    <option value="ADVISORY">ADVISORY</option>
                    <option value="NOMINAL">NOMINAL</option>
                  </select>
                </div>
                <div>
                  <label className="block text-gray-600 dark:text-gray-400 mb-1">Target Astronaut</label>
                  <select
                    value={newInc.targetAstronautId}
                    onChange={e => {
                      const id = e.target.value;
                      const ast = crew.find(a => a.id === id);
                      setNewInc(d => ({ ...d, targetAstronautId: id, targetAstronautName: ast ? ast.name : '' }));
                    }}
                    className="w-full px-3 py-2 rounded-lg bg-gray-50 dark:bg-[#202126] border border-gray-200 dark:border-[#333] text-gray-900 dark:text-gray-100"
                  >
                    {crew.map(ast => (
                      <option key={ast.id} value={ast.id}>{ast.name} ({ast.role})</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-gray-600 dark:text-gray-400 mb-1">Incident Type / Category</label>
                <input
                  type="text" required
                  placeholder="e.g. Acute Fatigue Drift / SpO2 Transient Dip"
                  value={newInc.type}
                  onChange={e => setNewInc(d => ({ ...d, type: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg bg-gray-50 dark:bg-[#202126] border border-gray-200 dark:border-[#333] text-gray-900 dark:text-gray-100"
                />
              </div>

              <div>
                <label className="block text-gray-600 dark:text-gray-400 mb-1">Summary & Clinical Findings</label>
                <textarea
                  rows="3" required
                  placeholder="Describe physiological drift or operational context..."
                  value={newInc.summary}
                  onChange={e => setNewInc(d => ({ ...d, summary: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg bg-gray-50 dark:bg-[#202126] border border-gray-200 dark:border-[#333] text-gray-900 dark:text-gray-100"
                />
              </div>

              <div>
                <label className="block text-gray-600 dark:text-gray-400 mb-1">Actions Taken</label>
                <input
                  type="text"
                  placeholder="e.g. Moved to quiet sleep pod, verified ECLSS regulator"
                  value={newInc.actionsTaken}
                  onChange={e => setNewInc(d => ({ ...d, actionsTaken: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg bg-gray-50 dark:bg-[#202126] border border-gray-200 dark:border-[#333] text-gray-900 dark:text-gray-100"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-3 border-t border-gray-100 dark:border-[#2a2c33]">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 rounded-lg border border-gray-200 dark:border-[#333] text-gray-600 dark:text-gray-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-neutral-900 text-white dark:bg-white dark:text-neutral-900 font-medium"
                >
                  Save Incident
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Resolve Incident */}
      {resolveModalInc && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-[#1a1b1f] border border-gray-100 dark:border-[#2a2c33] rounded-2xl max-w-md w-full p-6 space-y-4 shadow-xl">
            <h3 className="font-semibold text-sm text-gray-900 dark:text-gray-100">
              Resolve Incident: {resolveModalInc.type}
            </h3>
            <p className="text-xs text-gray-500">
              Sign off on resolution and record completion notes for {resolveModalInc.targetAstronautName}.
            </p>

            <form onSubmit={handleResolveSubmit} className="space-y-3 text-xs">
              <div>
                <label className="block text-gray-600 dark:text-gray-400 mb-1">Resolution Notes</label>
                <textarea
                  rows="3" required
                  value={resolveNotes}
                  onChange={e => setResolveNotes(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-gray-50 dark:bg-[#202126] border border-gray-200 dark:border-[#333] text-gray-900 dark:text-gray-100"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setResolveModalInc(null)}
                  className="px-4 py-2 rounded-lg border border-gray-200 dark:border-[#333] text-gray-600 dark:text-gray-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-neutral-900 text-white dark:bg-white dark:text-neutral-900 font-medium"
                >
                  Confirm Resolution
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

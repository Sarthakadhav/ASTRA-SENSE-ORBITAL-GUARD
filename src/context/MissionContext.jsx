import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { CREW_DATA, CREW_READINESS_METRICS, CREW_TREND_HISTORY } from '../data/mockCrew';
import { MEDICAL_INVENTORY, SIMULATED_EMERGENCY_SCENARIOS } from '../data/mockInventory';
import { RECENT_INCIDENTS, RECOVERY_TIMELINES } from '../data/mockIncidents';
import { orbitalApi } from '../services/api';

const MissionContext = createContext();

export const MissionProvider = ({ children }) => {
  const [crew, setCrew] = useState(CREW_DATA);
  const [selectedAstronautId, setSelectedAstronautId] = useState('AST-01');
  const [activeTab, setActiveTab] = useState('dashboard');
  
  // Software Telemetry Simulator state
  const [isEspStreaming, setIsEspStreaming] = useState(true);
  const [simulationRunning, setSimulationRunning] = useState(false);
  const [simulationMode, setSimulationMode] = useState('NORMAL'); // NORMAL | FATIGUE | HYPOXIA | CARDIAC | CUSTOM
  const [simulationSpeed, setSimulationSpeed] = useState(1); // 1x | 2x | 5x
  const [simulationTick, setSimulationTick] = useState(0);
  const [sensorNoiseLevel, setSensorNoiseLevel] = useState('low'); // 'low' | 'moderate' | 'high'
  const [latestPacket, setLatestPacket] = useState(null);
  const [latestIngestResult, setLatestIngestResult] = useState(null);
  const [customParams, setCustomParams] = useState({
    heart_rate_bpm: 72.0,
    spo2_pct: 98.0,
    skin_temp_c: 36.6,
    hrv_ms: 55.0,
    sleep_debt_h: 0.5,
    latency_drift_ms: 0.0,
    impedance_ohms: 480.0
  });

  // Connectivity & DSN
  const [dsnLatencySeconds, setDsnLatencySeconds] = useState(862); // 14 mins 22 secs Earth-Mars delay
  const [activeDrill, setActiveDrill] = useState(null);
  const [isBackendOnline, setIsBackendOnline] = useState(false);
  const [activeAlerts, setActiveAlerts] = useState([]);

  // Operational Readiness state
  const [crewReadiness, setCrewReadiness] = useState(CREW_READINESS_METRICS);
  
  // Inventory state
  const [inventory, setInventory] = useState(MEDICAL_INVENTORY);
  const [dispensations, setDispensations] = useState([]);
  
  // Incidents and recovery logs
  const [incidents, setIncidents] = useState(RECENT_INCIDENTS);
  const [recoveryTimelines, setRecoveryTimelines] = useState(RECOVERY_TIMELINES);
  
  // Workload redistribution state
  const [isRedistributed, setIsRedistributed] = useState(false);

  // Phase 2: Cloud Synchronization (Supabase)
  const [syncStatus, setSyncStatus] = useState({
    pipeline_state: 'LOCAL_ONLY',
    status_label: 'LOCAL_ONLY',
    message: 'Local SQLite flight database active.',
    cloud_configured: false,
    cloud_connected: false,
    cloud_status: 'NOT_CONFIGURED',
    pending_count: 0,
    synced_count: 0,
    failed_count: 0,
    retry_count: 0,
    unresolved_conflicts: 0,
    last_successful_sync: null,
    last_error: null,
    outbox_summary: {}
  });
  const [syncConflicts, setSyncConflicts] = useState([]);
  const [outboxEvents, setOutboxEvents] = useState([]);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncMetrics, setSyncMetrics] = useState(null);
  const [streamHealth, setStreamHealth] = useState(null);

  // Authentication & Role
  const [currentUser, setCurrentUser] = useState({
    username: 'tester',
    name: 'Flight Systems Tester',
    role: 'tester',
    permissions: {
      can_redistribute_workload: true,
      can_dispense_inventory: true,
      can_resolve_incidents: true,
      can_run_simulations: true,
      can_trigger_drills: true
    }
  });

  // Mission Elapsed Time (MET) counter
  const [met, setMet] = useState({ days: 142, hours: 4, mins: 36, secs: 18 });

  useEffect(() => {
    const timer = setInterval(() => {
      setMet(prev => {
        let { days, hours, mins, secs } = prev;
        secs += 1;
        if (secs >= 60) {
          secs = 0;
          mins += 1;
        }
        if (mins >= 60) {
          mins = 0;
          hours += 1;
        }
        if (hours >= 24) {
          hours = 0;
          days += 1;
        }
        return { days, hours, mins, secs };
      });
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Fetch initial state from backend on mount
  const refreshBackendData = useCallback(async () => {
    try {
      const statusRes = await orbitalApi.getSystemStatus();
      if (statusRes && statusRes.status === 'OPERATIONAL') {
        setIsBackendOnline(true);
      }

      const [crewRes, readinessRes, invRes, incRes, alertRes] = await Promise.all([
        orbitalApi.getCrew().catch(() => null),
        orbitalApi.getCrewReadiness().catch(() => null),
        orbitalApi.getInventory().catch(() => null),
        orbitalApi.getIncidents().catch(() => null),
        orbitalApi.getAlerts().catch(() => null)
      ]);

      if (crewRes && Array.isArray(crewRes) && crewRes.length > 0) {
        setCrew(crewRes);
      }
      if (readinessRes) {
        setCrewReadiness(readinessRes);
      }
      if (invRes && Array.isArray(invRes) && invRes.length > 0) {
        setInventory(invRes);
      }
      if (incRes && Array.isArray(incRes) && incRes.length > 0) {
        setIncidents(incRes);
      }
      if (alertRes && Array.isArray(alertRes)) {
        setActiveAlerts(alertRes);
      }

      const dispRes = await orbitalApi.getDispensations().catch(() => []);
      if (Array.isArray(dispRes)) {
        setDispensations(dispRes);
      }
    } catch (err) {
      console.warn("Backend not reachable or running in local offline mock mode:", err.message);
      setIsBackendOnline(false);
    }
  }, []);

  // Phase 2 & 3: Cloud Sync Methods & Observability
  const refreshSyncData = useCallback(async () => {
    try {
      const [status, metrics, health] = await Promise.all([
        orbitalApi.getSyncStatus(),
        orbitalApi.getSyncMetrics().catch(() => null),
        orbitalApi.getTelemetryStreamHealth().catch(() => null)
      ]);
      setSyncStatus(status);
      if (metrics) setSyncMetrics(metrics);
      if (health) setStreamHealth(health);
      if (status.unresolved_conflicts > 0) {
        const conflicts = await orbitalApi.getSyncConflicts();
        setSyncConflicts(conflicts);
      } else {
        setSyncConflicts([]);
      }
      const outbox = await orbitalApi.getOutboxEvents(50);
      setOutboxEvents(outbox);
    } catch {
      setSyncStatus(prev => ({
        ...prev,
        pipeline_state: 'LOCAL_ONLY',
        status_label: 'LOCAL_ONLY',
        cloud_connected: false
      }));
    }
  }, []);

  const triggerManualSync = useCallback(async () => {
    setIsSyncing(true);
    try {
      const res = await orbitalApi.triggerSync();
      await refreshSyncData();
      return res;
    } catch (err) {
      console.warn("Manual sync error:", err);
    } finally {
      setIsSyncing(false);
    }
  }, [refreshSyncData]);

  const retryFailedSync = useCallback(async () => {
    setIsSyncing(true);
    try {
      const res = await orbitalApi.retrySync();
      await refreshSyncData();
      return res;
    } finally {
      setIsSyncing(false);
    }
  }, [refreshSyncData]);

  const resolveConflictAction = useCallback(async (conflictId, resolutionChoice) => {
    try {
      const res = await orbitalApi.resolveConflict(conflictId, resolutionChoice, currentUser.name);
      await refreshSyncData();
      return res;
    } catch (err) {
      console.warn("Conflict resolution error:", err);
    }
  }, [currentUser.name, refreshSyncData]);

  useEffect(() => {
    refreshBackendData();
    refreshSyncData();
    const syncInterval = setInterval(refreshSyncData, 15000);
    return () => clearInterval(syncInterval);
  }, [refreshBackendData, refreshSyncData]);

  // Execute a single simulation step through backend ingestion
  const stepSimulation = useCallback(async (customTick = null) => {
    const currentTick = customTick !== null ? customTick : simulationTick;
    try {
      const res = await orbitalApi.stepSimulation(
        selectedAstronautId,
        simulationMode,
        currentTick,
        simulationMode === 'CUSTOM' ? customParams : null
      );

      if (res && res.packet) {
        setLatestPacket(res.packet);
        setLatestIngestResult(res.ingest_result);
        setSimulationTick(prev => prev + 1);

        // Update astronaut's live vitals in state
        setCrew(prevCrew =>
          prevCrew.map(ast => {
            if (ast.id === selectedAstronautId) {
              const stream = res.packet.sensor_stream;
              return {
                ...ast,
                condition: res.ingest_result.is_anomaly
                  ? (res.ingest_result.safety_alert ? 'Alert Triggered' : 'Unusual Pattern (Needs Rest)')
                  : (ast.conditionSeverity === 'warning' ? ast.condition : 'Healthy'),
                conditionSeverity: res.ingest_result.is_anomaly
                  ? (res.ingest_result.safety_alert && res.ingest_result.safety_alert.includes('Critical') ? 'critical' : 'warning')
                  : ast.conditionSeverity,
                vitals: {
                  ...ast.vitals,
                  heartRate: stream.heart_rate_bpm,
                  spo2: stream.spo2_pct,
                  temperature: stream.skin_temp_c,
                  hrv: stream.hrv_ms || ast.vitals.hrv,
                  sleepDebtHours: stream.sleep_debt_h !== undefined ? stream.sleep_debt_h : ast.vitals.sleepDebtHours,
                  respiration: stream.respiration_rate || ast.vitals.respiration
                },
                mlModel: {
                  ...ast.mlModel,
                  anomalyScore: res.ingest_result.anomaly_score,
                  status: res.ingest_result.is_anomaly ? 'Physiological Outlier' : 'Nominal Baseline'
                }
              };
            }
            return ast;
          })
        );

        // Refresh active alerts if an alert was generated
        if (res.ingest_result.safety_alert) {
          const freshAlerts = await orbitalApi.getAlerts().catch(() => null);
          if (freshAlerts) setActiveAlerts(freshAlerts);
        }
      }
    } catch (err) {
      console.warn("Simulator step offline fallback:", err);
      // Fallback local perturbation
      setSimulationTick(prev => prev + 1);
    }
  }, [selectedAstronautId, simulationMode, simulationTick, customParams]);

  // Software simulator running loop
  const simTimerRef = useRef(null);
  useEffect(() => {
    if (!simulationRunning) {
      if (simTimerRef.current) clearInterval(simTimerRef.current);
      return;
    }

    const intervalMs = Math.max(200, Math.round(1000 / simulationSpeed));
    simTimerRef.current = setInterval(() => {
      stepSimulation();
    }, intervalMs);

    return () => {
      if (simTimerRef.current) clearInterval(simTimerRef.current);
    };
  }, [simulationRunning, simulationSpeed, stepSimulation]);

  // Organic micro-fluctuations when simulator is not running but stream is active
  useEffect(() => {
    if (simulationRunning || !isEspStreaming) return;

    const interval = setInterval(() => {
      setCrew(prevCrew =>
        prevCrew.map(ast => {
          const hrJitter = (Math.random() - 0.5) * 1.2;
          const tempJitter = (Math.random() - 0.5) * 0.04;
          const hrvJitter = (Math.random() - 0.5) * 0.8;

          let currentHR = ast.vitals.heartRate;
          if (ast.id === 'AST-01' && isRedistributed) {
            currentHR = Math.max(68, currentHR - 0.1);
          }

          return {
            ...ast,
            vitals: {
              ...ast.vitals,
              heartRate: Math.round((currentHR + hrJitter) * 10) / 10,
              temperature: Math.round((ast.vitals.temperature + tempJitter) * 100) / 100,
              hrv: Math.max(15, Math.round((ast.vitals.hrv + hrvJitter) * 10) / 10),
            }
          };
        })
      );
    }, 1500);

    return () => clearInterval(interval);
  }, [simulationRunning, isEspStreaming, isRedistributed]);

  // Execute Workload Redistribution
  const applyWorkloadRedistribution = useCallback(async () => {
    try {
      const res = await orbitalApi.redistributeWorkload('AST-01', 'AST-02');
      setIsRedistributed(true);
      if (res && res.new_crew_readiness_score) {
        setCrewReadiness(prev => ({
          ...prev,
          overallScore: res.new_crew_readiness_score,
          statusDescription: 'Stable - Dr. Vance is resting while Cmdr. Chen covers duties',
          aiRecommendation: 'Workload transfer complete! Commander Chen is covering medical duties. Dr. Vance will rest for 8 hours.'
        }));
      }
      refreshBackendData();
    } catch (err) {
      console.warn("Backend redistribution unavailable, applying locally:", err);
      setIsRedistributed(true);
      setCrew(prev =>
        prev.map(ast => {
          if (ast.id === 'AST-01') {
            return {
              ...ast,
              condition: 'Resting & Recovering',
              conditionSeverity: 'nominal',
              isReassigned: true,
              recommendation: 'Duties safely handed over to Cmdr. Sarah Chen. Quiet rest period is active.',
              readinessScore: 78
            };
          }
          if (ast.id === 'AST-02') {
            return {
              ...ast,
              responsibilities: [
                ...ast.responsibilities,
                { id: 'RESP-01-TRANSFER', title: '[Covering for Vance] Daily Health Checkups', priority: 'High', canDelegate: false }
              ]
            };
          }
          return ast;
        })
      );
      setCrewReadiness(prev => ({
        ...prev,
        overallScore: 82,
        statusDescription: 'Stable - Dr. Vance is resting while Cmdr. Chen covers duties',
        aiRecommendation: 'Workload transfer complete! Commander Chen is covering medical duties. Dr. Vance will rest for 8 hours.'
      }));
    }
  }, [refreshBackendData]);

  // Consume / Dispense Inventory
  const consumeItem = useCallback(async (itemId, quantity = 1, reason = 'Clinical consumption', patientId = 'AST-01') => {
    try {
      const res = await orbitalApi.consumeInventory(itemId, quantity, reason, currentUser.name, patientId);
      setInventory(prev =>
        prev.map(item => item.id === itemId ? { ...item, stock: res.remaining_stock, status: res.inventory_status } : item)
      );
      const updatedDispensations = await orbitalApi.getDispensations().catch(() => []);
      if (Array.isArray(updatedDispensations)) setDispensations(updatedDispensations);
      return res;
    } catch (err) {
      // Local fallback
      setInventory(prev =>
        prev.map(item => {
          if (item.id === itemId) {
            const nextStock = Math.max(0, item.stock - quantity);
            return { ...item, stock: nextStock, status: nextStock <= item.minSafeStock ? 'Low Reserve Warning' : item.status };
          }
          return item;
        })
      );
      throw err;
    }
  }, [currentUser]);

  // Replenish Inventory
  const replenishItem = useCallback(async (itemId, quantity = 5, notes = 'Station restock') => {
    try {
      const res = await orbitalApi.replenishInventory(itemId, quantity, currentUser.name, notes);
      setInventory(prev =>
        prev.map(item => item.id === itemId ? { ...item, stock: res.new_stock, status: res.inventory_status } : item)
      );
      return res;
    } catch (err) {
      setInventory(prev =>
        prev.map(item => item.id === itemId ? { ...item, stock: item.stock + quantity, status: 'Nominal' } : item)
      );
      throw err;
    }
  }, [currentUser]);

  // Add Inventory Item
  const addItem = useCallback(async (itemData) => {
    try {
      const res = await orbitalApi.createInventoryItem(itemData);
      setInventory(prev => [...prev, { ...itemData, status: 'Nominal' }]);
      return res;
    } catch (err) {
      setInventory(prev => [...prev, { ...itemData, status: 'Nominal' }]);
      throw err;
    }
  }, []);

  // Log Incident
  const logIncident = useCallback(async (incidentData) => {
    try {
      const res = await orbitalApi.createIncident(incidentData);
      refreshBackendData();
      return res;
    } catch (err) {
      const newInc = {
        id: `INC-2026-${Date.now().toString().slice(-4)}`,
        timestamp: `MET ${met.days}d ${String(met.hours).padStart(2, '0')}:${String(met.mins).padStart(2, '0')}`,
        severity: incidentData.severity || 'WARNING',
        type: incidentData.type || 'Custom Health Event',
        targetAstronautId: incidentData.targetAstronautId || 'AST-01',
        targetAstronautName: incidentData.targetAstronautName || 'Dr. Elena Vance',
        summary: incidentData.summary || 'Logged manually.',
        resolutionStatus: 'Active - Action Pending',
        syncStatus: 'Queued for Earth DSN Sync',
        assignedOfficer: currentUser.name,
        actionsTaken: incidentData.actionsTaken || []
      };
      setIncidents(prev => [newInc, ...prev]);
    }
  }, [currentUser, met, refreshBackendData]);

  // Resolve Incident
  const resolveIncidentAction = useCallback(async (incidentId, notes) => {
    try {
      const res = await orbitalApi.resolveIncident(incidentId, notes, currentUser.name);
      refreshBackendData();
      return res;
    } catch (err) {
      setIncidents(prev =>
        prev.map(inc => inc.id === incidentId ? { ...inc, resolutionStatus: 'Resolved' } : inc)
      );
    }
  }, [currentUser, refreshBackendData]);

  // Sync DSN Queue
  const syncDsn = useCallback(async () => {
    try {
      const res = await orbitalApi.syncDsnQueue();
      setIncidents(prev =>
        prev.map(inc => ({ ...inc, syncStatus: 'Synced with Houston Mission Control' }))
      );
      return res;
    } catch (err) {
      setIncidents(prev =>
        prev.map(inc => ({ ...inc, syncStatus: 'Synced with Houston Mission Control' }))
      );
    }
  }, []);

  // Trigger emergency drill scenario
  const triggerDrill = useCallback(async (scenarioId) => {
    const drill = SIMULATED_EMERGENCY_SCENARIOS.find(s => s.id === scenarioId);
    if (!drill) return;

    setActiveDrill(drill);
    try {
      await orbitalApi.triggerEmergencyDrill(scenarioId);
      refreshBackendData();
    } catch (err) {
      console.warn("Backend drill trigger unavailable, applying locally:", err);
      if (scenarioId === 'SCENARIO-02') {
        setCrew(prev =>
          prev.map(ast => ({
            ...ast,
            vitals: {
              ...ast.vitals,
              spo2: Math.max(88, ast.vitals.spo2 - 7),
              heartRate: ast.vitals.heartRate + 25,
              respiration: ast.vitals.respiration + 6
            }
          }))
        );
        setCrewReadiness(prev => ({
          ...prev,
          overallScore: 48,
          statusDescription: 'URGENT ALERT: Low Cabin Air Pressure Detected',
          aiRecommendation: 'Put on oxygen masks right away. Pause all routine work until pressure stabilizes.'
        }));
      }
    }
  }, [refreshBackendData]);

  // Reset simulation state
  const resetAllSimulations = useCallback(async () => {
    setSimulationRunning(false);
    setSimulationTick(0);
    setSimulationMode('NORMAL');
    try {
      await orbitalApi.resetCrewSimulation();
      await orbitalApi.resetSimulation();
      refreshBackendData();
    } catch (err) {
      setCrew(CREW_DATA);
      setCrewReadiness(CREW_READINESS_METRICS);
      setIsRedistributed(false);
      setActiveDrill(null);
      setInventory(MEDICAL_INVENTORY);
    }
  }, [refreshBackendData]);

  // Role Switcher
  const switchRole = useCallback(async (roleName, password = null) => {
    const pwd = password || (roleName === 'student' ? 'Student2026!' : roleName === 'tester' ? 'Tester2026!' : 'Faculty2026!');
    try {
      const res = await orbitalApi.login(roleName, pwd);
      setCurrentUser({
        username: res.username,
        name: res.name,
        role: res.role,
        permissions: res.permissions
      });
      return res;
    } catch (err) {
      console.warn("Local auth fallback:", err.message);
      const fallbackRoles = {
        student: { role: 'student', name: 'Astronaut Trainee', can_redistribute_workload: false, can_dispense_inventory: false, can_resolve_incidents: false },
        tester: { role: 'tester', name: 'Flight Systems Tester', can_redistribute_workload: true, can_dispense_inventory: true, can_resolve_incidents: true },
        faculty: { role: 'faculty', name: 'Prof. Flight Director', can_redistribute_workload: true, can_dispense_inventory: true, can_resolve_incidents: true }
      };
      const r = fallbackRoles[roleName] || fallbackRoles.tester;
      setCurrentUser({
        username: roleName,
        name: r.name,
        role: r.role,
        permissions: r
      });
    }
  }, []);

  const selectedAstronaut = crew.find(a => a.id === selectedAstronautId) || crew[0];

  return (
    <MissionContext.Provider
      value={{
        crew,
        selectedAstronaut,
        selectedAstronautId,
        setSelectedAstronautId,
        activeTab,
        setActiveTab,
        crewReadiness,
        isEspStreaming,
        setIsEspStreaming,
        sensorNoiseLevel,
        setSensorNoiseLevel,
        dsnLatencySeconds,
        activeDrill,
        inventory,
        setInventory,
        dispensations,
        consumeItem,
        replenishItem,
        addItem,
        incidents,
        logIncident,
        resolveIncidentAction,
        syncDsn,
        recoveryTimelines,
        isRedistributed,
        applyWorkloadRedistribution,
        triggerDrill,
        resetAllSimulations,
        met,
        trendHistory: CREW_TREND_HISTORY,
        // Simulator Controls & State
        simulationRunning,
        setSimulationRunning,
        simulationMode,
        setSimulationMode,
        simulationSpeed,
        setSimulationSpeed,
        simulationTick,
        stepSimulation,
        latestPacket,
        latestIngestResult,
        customParams,
        setCustomParams,
        isBackendOnline,
        activeAlerts,
        currentUser,
        switchRole,
        refreshBackendData,
        isSimulatedData: true,
        // Phase 2 & 3: Cloud Sync State, Observability & Actions
        syncStatus,
        syncMetrics,
        streamHealth,
        syncConflicts,
        outboxEvents,
        isSyncing,
        refreshSyncData,
        triggerManualSync,
        retryFailedSync,
        resolveConflictAction
      }}
    >
      {children}
    </MissionContext.Provider>
  );
};

export const useMission = () => {
  const context = useContext(MissionContext);
  if (!context) {
    throw new Error('useMission must be used within a MissionProvider');
  }
  return context;
};

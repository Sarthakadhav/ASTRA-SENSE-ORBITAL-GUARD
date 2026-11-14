import React, { useState } from 'react';
import { 
  Play, Pause, Square, RotateCcw, FastForward, Activity, 
  AlertTriangle, Shield, Sliders, CheckCircle, Database 
} from 'lucide-react';
import { useMission } from '../../context/MissionContext';
import { EcgWaveform } from '../common/EcgWaveform';

export const HardwareSimulator = () => {
  const { 
    crew, selectedAstronaut, selectedAstronautId, setSelectedAstronautId,
    simulationRunning, setSimulationRunning,
    simulationMode, setSimulationMode,
    simulationSpeed, setSimulationSpeed,
    simulationTick, stepSimulation,
    resetAllSimulations,
    latestPacket, latestIngestResult,
    customParams, setCustomParams,
    isBackendOnline
  } = useMission();

  const [activeTab, setActiveTab] = useState('controls'); // 'controls' | 'custom' | 'json'

  const scenarioModes = [
    {
      id: 'NORMAL',
      label: 'Mode A: Normal Operation',
      desc: 'Stable readings representing a healthy astronaut at nominal baseline in microgravity.',
      color: 'border-emerald-500/50 bg-emerald-50/30 dark:bg-emerald-950/20'
    },
    {
      id: 'FATIGUE',
      label: 'Mode B: Fatigue Scenario',
      desc: 'Cumulative sleep debt (6.4h), HRV reduction, resting pulse drift (+31%), cognitive latency drift (+185ms).',
      color: 'border-amber-500/50 bg-amber-50/30 dark:bg-amber-950/20'
    },
    {
      id: 'HYPOXIA',
      label: 'Mode C: Hypoxia Scenario',
      desc: 'Controlled abnormal SpO2 drop (<88%) and compensatory tachycardia to exercise deterministic safety alerting and SOP-HYPOXIA-02.',
      color: 'border-blue-500/50 bg-blue-50/30 dark:bg-blue-950/20'
    },
    {
      id: 'CARDIAC',
      label: 'Mode D: Cardiac Irregularity',
      desc: 'Acute sustained tachycardia (>130 bpm) with depressed HRV and ectopic Lead-II ECG waveform to test arrhythmia safety rules and SOP-ARRHYTHMIA-03.',
      color: 'border-rose-500/50 bg-rose-50/30 dark:bg-rose-950/20'
    },
    {
      id: 'CUSTOM',
      label: 'Mode E: Custom Simulation',
      desc: 'User-configured physiological parameters and sensor noise bounds to test specific clinical decision support workflows.',
      color: 'border-purple-500/50 bg-purple-50/30 dark:bg-purple-950/20'
    }
  ];

  return (
    <div className="space-y-6">
      {/* Prominent Simulated Data Indicator Header */}
      <div className="p-4 rounded-2xl bg-amber-50/80 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900/50 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-sm">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-xl bg-amber-500 text-white flex items-center justify-center font-bold text-sm shadow-sm">
            SIM
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-semibold text-xs tracking-wider text-amber-900 dark:text-amber-200 uppercase">
                Software Telemetry Simulation Engine
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-amber-200/60 dark:bg-amber-900/60 text-amber-900 dark:text-amber-200">
                100% SOFTWARE-ONLY
              </span>
            </div>
            <p className="text-xs text-amber-800/90 dark:text-amber-300 mt-0.5">
              All physiological measurements are synthetically generated and validated through the backend SQLite pipeline.
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2 text-xs">
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-white/80 dark:bg-[#1a1b1f] border border-amber-200 dark:border-amber-900/50 text-gray-700 dark:text-gray-300">
            <Database className="w-3.5 h-3.5 text-emerald-500" />
            <span>SQLite WAL: <strong>{isBackendOnline ? 'Online (Persistent)' : 'Local Fallback'}</strong></span>
          </span>
        </div>
      </div>

      {/* Header bar with primary controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-gray-100 dark:border-[#24252a] gap-3">
        <div>
          <span className="text-xs uppercase tracking-wider text-gray-400 font-medium">
            Telemetry Feed Simulator
          </span>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mt-0.5">
            Software Bio-Telemetry Simulator
          </h2>
          <p className="text-xs text-gray-400 mt-0.5">
            Exercises deterministic safety checks, Scikit-learn anomaly scoring, and SQLite persistence.
          </p>
        </div>

        {/* Master Simulator Controls */}
        <div className="flex flex-wrap items-center gap-2">
          {!simulationRunning ? (
            <button
              onClick={() => setSimulationRunning(true)}
              className="flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-neutral-900 text-white dark:bg-white dark:text-neutral-900 text-xs font-medium hover:bg-neutral-800 transition-colors shadow-sm"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Start Simulation</span>
            </button>
          ) : (
            <button
              onClick={() => setSimulationRunning(false)}
              className="flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-amber-600 text-white text-xs font-medium hover:bg-amber-700 transition-colors shadow-sm"
            >
              <Pause className="w-3.5 h-3.5 fill-current" />
              <span>Pause Simulation</span>
            </button>
          )}

          <button
            onClick={() => stepSimulation()}
            className="px-3 py-2 rounded-xl border border-gray-200 dark:border-[#333] text-gray-700 dark:text-gray-200 text-xs font-medium hover:bg-gray-50 dark:hover:bg-[#202126] transition-colors"
            title="Inject single packet"
          >
            Step +1
          </button>

          <button
            onClick={resetAllSimulations}
            className="flex items-center space-x-1 px-3 py-2 rounded-xl border border-gray-200 dark:border-[#333] text-gray-600 dark:text-gray-300 text-xs hover:bg-gray-50 dark:hover:bg-[#202126] transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset</span>
          </button>

          {/* Speed Selector */}
          <div className="flex items-center bg-gray-100 dark:bg-[#202126] p-1 rounded-xl text-xs">
            {[1, 2, 5].map(spd => (
              <button
                key={spd}
                onClick={() => setSimulationSpeed(spd)}
                className={`px-2.5 py-1 rounded-lg transition-colors font-medium ${
                  simulationSpeed === spd
                    ? 'bg-white dark:bg-[#15161a] text-gray-900 dark:text-white shadow-sm'
                    : 'text-gray-500 hover:text-gray-900 dark:hover:text-white'
                }`}
              >
                {spd}x
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Astronaut & Mode Configuration */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Left: Astronaut Selector */}
        <div className="bg-white dark:bg-[#1a1b1f] border border-gray-100 dark:border-[#27282e] rounded-2xl p-5 shadow-sm space-y-3">
          <span className="text-xs font-medium uppercase tracking-wider text-gray-400 block">
            Target Astronaut
          </span>
          <div className="space-y-2">
            {crew.map(ast => (
              <div
                key={ast.id}
                onClick={() => setSelectedAstronautId(ast.id)}
                className={`p-3 rounded-xl border transition-all cursor-pointer flex items-center justify-between ${
                  selectedAstronautId === ast.id
                    ? 'border-neutral-900 dark:border-white bg-gray-50/80 dark:bg-[#202126] shadow-sm'
                    : 'border-gray-100 dark:border-[#26272c] hover:border-gray-200 dark:hover:border-[#333]'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <img src={ast.photo} alt={ast.name} className="w-9 h-9 rounded-lg object-cover" />
                  <div>
                    <div className="font-medium text-xs text-gray-900 dark:text-gray-100">{ast.name}</div>
                    <div className="text-[11px] text-gray-400">{ast.role} • {ast.id}</div>
                  </div>
                </div>
                <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${
                  ast.conditionSeverity === 'nominal'
                    ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300'
                    : 'bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300'
                }`}>
                  {ast.vitals.heartRate} bpm
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Center & Right: Scenario Selector */}
        <div className="lg:col-span-2 bg-white dark:bg-[#1a1b1f] border border-gray-100 dark:border-[#27282e] rounded-2xl p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-gray-400 block">
              Simulation Scenario (Modes A to E)
            </span>
            <span className="text-xs text-gray-500 font-mono">
              Tick: #{simulationTick} | Status: {simulationRunning ? 'STREAMING ACTIVE' : 'PAUSED'}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {scenarioModes.map(mode => (
              <div
                key={mode.id}
                onClick={() => setSimulationMode(mode.id)}
                className={`p-3.5 rounded-xl border transition-all cursor-pointer ${
                  simulationMode === mode.id
                    ? `${mode.color} border-neutral-900 dark:border-white shadow-sm ring-1 ring-neutral-900 dark:ring-white`
                    : 'border-gray-100 dark:border-[#26272c] bg-gray-50/50 dark:bg-[#202126]/40 hover:border-gray-200'
                }`}
              >
                <div className="font-semibold text-xs text-gray-900 dark:text-gray-100">
                  {mode.label}
                </div>
                <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-1 leading-relaxed">
                  {mode.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Mode E: Custom Parameters Drawer if Custom is selected */}
      {simulationMode === 'CUSTOM' && (
        <div className="bg-white dark:bg-[#1a1b1f] border border-purple-200 dark:border-purple-900/50 rounded-2xl p-6 shadow-sm space-y-4">
          <div className="flex items-center space-x-2">
            <Sliders className="w-4 h-4 text-purple-600" />
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
              Mode E — Custom Physiological Bounds Configuration
            </h3>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
            <div>
              <label className="block text-gray-500 mb-1">Heart Rate ({customParams.heart_rate_bpm} bpm)</label>
              <input
                type="range" min="40" max="180" step="1"
                value={customParams.heart_rate_bpm}
                onChange={e => setCustomParams(p => ({ ...p, heart_rate_bpm: parseFloat(e.target.value) }))}
                className="w-full accent-neutral-900 dark:accent-white"
              />
            </div>
            <div>
              <label className="block text-gray-500 mb-1">SpO₂ Oxygen ({customParams.spo2_pct}%)</label>
              <input
                type="range" min="75" max="100" step="0.5"
                value={customParams.spo2_pct}
                onChange={e => setCustomParams(p => ({ ...p, spo2_pct: parseFloat(e.target.value) }))}
                className="w-full accent-neutral-900 dark:accent-white"
              />
            </div>
            <div>
              <label className="block text-gray-500 mb-1">HRV / RMSSD ({customParams.hrv_ms} ms)</label>
              <input
                type="range" min="10" max="90" step="1"
                value={customParams.hrv_ms}
                onChange={e => setCustomParams(p => ({ ...p, hrv_ms: parseFloat(e.target.value) }))}
                className="w-full accent-neutral-900 dark:accent-white"
              />
            </div>
            <div>
              <label className="block text-gray-500 mb-1">Sleep Debt ({customParams.sleep_debt_h} h)</label>
              <input
                type="range" min="0" max="12" step="0.2"
                value={customParams.sleep_debt_h}
                onChange={e => setCustomParams(p => ({ ...p, sleep_debt_h: parseFloat(e.target.value) }))}
                className="w-full accent-neutral-900 dark:accent-white"
              />
            </div>
          </div>
        </div>
      )}

      {/* Real-time Telemetry Ingestion Output Stage */}
      <div className="bg-white dark:bg-[#1a1b1f] border border-gray-100 dark:border-[#27282e] rounded-2xl p-6 shadow-sm space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-gray-50 dark:border-[#24252a] gap-2">
          <div>
            <span className="text-xs uppercase tracking-wider text-gray-400 font-medium">
              Live Pipeline Ingestion
            </span>
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mt-0.5">
              Live Stream: {selectedAstronaut.name} ({simulationMode} Active)
            </h3>
          </div>

          <div className="flex items-center space-x-3 text-xs">
            <span className="text-gray-400">
              Packet ID: <strong className="font-mono text-gray-800 dark:text-gray-200">#{latestPacket ? latestPacket.packet_id : 142000}</strong>
            </span>
            <span className={`px-2 py-0.5 rounded text-[11px] font-medium ${
              latestIngestResult?.is_anomaly
                ? 'bg-amber-100 text-amber-800 dark:bg-amber-950/50 dark:text-amber-300'
                : 'bg-emerald-50 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-300'
            }`}>
              {latestIngestResult ? (latestIngestResult.is_anomaly ? 'ANOMALY DETECTED' : 'NOMINAL INGEST') : 'PIPELINE READY'}
            </span>
          </div>
        </div>

        {/* Dynamic ECG Waveform */}
        <div className="space-y-1">
          <div className="flex justify-between text-xs text-gray-400">
            <span>Synthetic Lead-II Electrocardiogram (mV)</span>
            <span>Sampling: 10 Hz Real-Time Loop</span>
          </div>
          <EcgWaveform
            heartRate={selectedAstronaut.vitals.heartRate}
            isAbnormal={simulationMode === 'CARDIAC' || selectedAstronaut.conditionSeverity !== 'nominal'}
            height={70}
          />
        </div>

        {/* Vitals Telemetry Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <div className="p-3.5 rounded-xl bg-gray-50/70 dark:bg-[#202126] text-center">
            <span className="text-[10px] text-gray-400 uppercase tracking-wide block">Heart Rate</span>
            <span className="text-lg font-semibold text-gray-900 dark:text-gray-100 mt-0.5 block">
              {selectedAstronaut.vitals.heartRate} <span className="text-xs font-normal text-gray-400">bpm</span>
            </span>
            <span className="text-[10px] text-gray-400">Base: {selectedAstronaut.vitals.heartRateBaseline}</span>
          </div>

          <div className="p-3.5 rounded-xl bg-gray-50/70 dark:bg-[#202126] text-center">
            <span className="text-[10px] text-gray-400 uppercase tracking-wide block">SpO₂ Oxygen</span>
            <span className="text-lg font-semibold text-gray-900 dark:text-gray-100 mt-0.5 block">
              {selectedAstronaut.vitals.spo2}%
            </span>
            <span className="text-[10px] text-gray-400">Base: {selectedAstronaut.vitals.spo2Baseline}%</span>
          </div>

          <div className="p-3.5 rounded-xl bg-gray-50/70 dark:bg-[#202126] text-center">
            <span className="text-[10px] text-gray-400 uppercase tracking-wide block">Recovery (HRV)</span>
            <span className="text-lg font-semibold text-gray-900 dark:text-gray-100 mt-0.5 block">
              {selectedAstronaut.vitals.hrv} <span className="text-xs font-normal text-gray-400">ms</span>
            </span>
            <span className="text-[10px] text-gray-400">Base: {selectedAstronaut.vitals.hrvBaseline}</span>
          </div>

          <div className="p-3.5 rounded-xl bg-gray-50/70 dark:bg-[#202126] text-center">
            <span className="text-[10px] text-gray-400 uppercase tracking-wide block">Core Temp</span>
            <span className="text-lg font-semibold text-gray-900 dark:text-gray-100 mt-0.5 block">
              {selectedAstronaut.vitals.temperature}°C
            </span>
            <span className="text-[10px] text-gray-400">Base: {selectedAstronaut.vitals.tempBaseline}°C</span>
          </div>

          <div className="p-3.5 rounded-xl bg-gray-50/70 dark:bg-[#202126] text-center">
            <span className="text-[10px] text-gray-400 uppercase tracking-wide block">Sleep Debt (72h)</span>
            <span className="text-lg font-semibold text-gray-900 dark:text-gray-100 mt-0.5 block">
              {selectedAstronaut.vitals.sleepDebtHours}h
            </span>
            <span className="text-[10px] text-gray-400">Target: &lt; 1.0h</span>
          </div>

          <div className="p-3.5 rounded-xl bg-gray-50/70 dark:bg-[#202126] text-center">
            <span className="text-[10px] text-gray-400 uppercase tracking-wide block">ML Anomaly Score</span>
            <span className={`text-lg font-semibold mt-0.5 block tabular-nums ${
              selectedAstronaut.mlModel.anomalyScore < 0 ? 'text-amber-600' : 'text-gray-900 dark:text-gray-100'
            }`}>
              {selectedAstronaut.mlModel.anomalyScore > 0 ? `+${selectedAstronaut.mlModel.anomalyScore}` : selectedAstronaut.mlModel.anomalyScore}
            </span>
            <span className="text-[10px] text-gray-400">Isolation Forest</span>
          </div>
        </div>

        {/* Safety Alert Output if triggered */}
        {latestIngestResult?.safety_alert && (
          <div className="p-4 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900/40 text-xs text-amber-900 dark:text-amber-200 flex items-start space-x-2.5">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold block">Deterministic Safety Alert:</span>
              <p className="mt-0.5 leading-relaxed">{latestIngestResult.safety_alert}</p>
            </div>
          </div>
        )}
      </div>

      {/* Raw JSON Packet Inspection */}
      <div className="bg-white dark:bg-[#1a1b1f] border border-gray-100 dark:border-[#27282e] rounded-2xl p-6 shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
            Raw Telemetry Packet Payload (Ingested by FastAPI / SQLite)
          </h3>
          <span className="text-xs text-gray-400 font-mono">CRC32: VALID • IS_SIMULATED: TRUE</span>
        </div>
        <pre className="p-4 rounded-xl bg-gray-50 dark:bg-[#202126] text-xs font-mono text-gray-800 dark:text-gray-200 overflow-x-auto border border-gray-100 dark:border-[#27282e]">
          {JSON.stringify(latestPacket || {
            packet_id: 142001,
            timestamp_met: "142:04:36:18",
            astronaut_id: selectedAstronautId,
            is_simulated: true,
            sensor_stream: {
              ecg_lead2_mv: 1.14,
              spo2_pct: selectedAstronaut.vitals.spo2,
              heart_rate_bpm: selectedAstronaut.vitals.heartRate,
              skin_temp_c: selectedAstronaut.vitals.temperature,
              hrv_ms: selectedAstronaut.vitals.hrv,
              sleep_debt_h: selectedAstronaut.vitals.sleepDebtHours,
              imu_accel_g: [0.02, 0.04, 0.01],
              impedance_ohms: 480
            },
            battery_level_pct: 94,
            crc32_valid: true
          }, null, 2)}
        </pre>
      </div>
    </div>
  );
};

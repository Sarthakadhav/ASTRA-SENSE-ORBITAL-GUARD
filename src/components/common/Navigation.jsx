import React from 'react';
import { useMission } from '../../context/MissionContext';

export const Navigation = () => {
  const { activeTab, setActiveTab, crewReadiness, syncStatus } = useMission();

  const getSyncBadge = () => {
    if (syncStatus?.unresolved_conflicts > 0) return 'Conflict';
    if (syncStatus?.pending_count > 0) return `${syncStatus.pending_count}`;
    return null;
  };

  const navItems = [
    { id: 'dashboard', label: 'Dashboard' },
    { id: 'crew-matrix', label: 'Crew Matrix', badge: crewReadiness.overallScore < 70 ? 'Alert' : null },
    { id: 'health-monitoring', label: 'Live Telemetry' },
    { id: 'ai-intelligence', label: 'AI Baseline' },
    { id: 'mission-medic', label: 'Medical Assistant' },
    { id: 'med-vault', label: 'Med Vault' },
    { id: 'mission-incidents', label: 'Incidents' },
    { id: 'recovery-tracker', label: 'Recovery' },
    { id: 'hardware-sim', label: 'Telemetry Simulator' },
    { id: 'cloud-sync', label: 'Cloud Sync', badge: getSyncBadge() }
  ];

  return (
    <nav className="w-full bg-white dark:bg-[#15161a] border-b border-gray-100 dark:border-[#26272c]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex space-x-1 sm:space-x-4 overflow-x-auto no-scrollbar py-2">
          {navItems.map(item => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`px-3 py-1.5 rounded-md text-xs transition-colors whitespace-nowrap flex items-center space-x-1.5 ${
                  isActive
                    ? 'font-medium text-gray-900 bg-gray-100 dark:text-white dark:bg-[#23252b]'
                    : 'text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200'
                }`}
              >
                <span>{item.label}</span>
                {item.badge && (
                  <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-mono inline-block ${
                    item.badge === 'Conflict' 
                      ? 'bg-rose-500 text-white' 
                      : (item.badge === 'Alert' ? 'bg-amber-500 text-white' : 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300')
                  }`}>
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>
    </nav>
  );
};

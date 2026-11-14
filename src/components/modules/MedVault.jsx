import React, { useState } from 'react';
import { 
  Plus, Minus, RefreshCw, Search, AlertTriangle, Shield, 
  Package, History, Check, Database 
} from 'lucide-react';
import { useMission } from '../../context/MissionContext';
import { SIMULATED_EMERGENCY_SCENARIOS } from '../../data/mockInventory';

export const MedVault = () => {
  const { 
    inventory, dispensations, consumeItem, replenishItem, 
    addItem, crew, currentUser, isBackendOnline 
  } = useMission();

  const [activeView, setActiveView] = useState('inventory'); // 'inventory' | 'dispensations' | 'scenarios'
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [lowStockOnly, setLowStockOnly] = useState(false);
  const [activeScenarioId, setActiveScenarioId] = useState('SCENARIO-01');

  // Modals state
  const [dispenseModalItem, setDispenseModalItem] = useState(null);
  const [dispenseQty, setDispenseQty] = useState(1);
  const [dispensePatient, setDispensePatient] = useState('AST-01');
  const [dispenseReason, setDispenseReason] = useState('Clinical Protocol Step 4 (Fatigue Countermeasure)');
  const [dispenseSuccess, setDispenseSuccess] = useState('');

  const [replenishModalItem, setReplenishModalItem] = useState(null);
  const [replenishQty, setReplenishQty] = useState(5);
  const [replenishNotes, setReplenishNotes] = useState('Cargo Resupply Pod 2 restock');

  const [showAddModal, setShowAddModal] = useState(false);
  const [newItemData, setNewItemData] = useState({
    id: `MED-0${inventory.length + 1}`,
    category: 'Pharmaceuticals',
    name: '',
    indication: '',
    stock: 20,
    unit: 'tablets',
    minSafeStock: 5,
    shelfLifeDays: 360,
    vitalUrgency: 'Medium',
    location: 'Med-Bay Drawer C-1',
    contraindications: 'None documented'
  });

  const categories = ['All', 'Pharmaceuticals', 'Critical Equipment', 'Wearable Hardware', 'Supplies'];

  // Filtering
  const filteredInventory = inventory.filter(item => {
    const matchesCat = selectedCategory === 'All' || item.category === selectedCategory;
    const matchesSearch = item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          (item.indication && item.indication.toLowerCase().includes(searchQuery.toLowerCase()));
    const matchesLow = lowStockOnly ? item.stock <= item.minSafeStock : true;
    return matchesCat && matchesSearch && matchesLow;
  });

  const selectedScenario = SIMULATED_EMERGENCY_SCENARIOS.find(s => s.id === activeScenarioId) || SIMULATED_EMERGENCY_SCENARIOS[0];

  const handleDispenseSubmit = async (e) => {
    e.preventDefault();
    if (!dispenseModalItem) return;
    try {
      await consumeItem(dispenseModalItem.id, dispenseQty, dispenseReason, dispensePatient);
      setDispenseSuccess(`Successfully dispensed ${dispenseQty} ${dispenseModalItem.unit} of ${dispenseModalItem.name}`);
      setTimeout(() => {
        setDispenseSuccess('');
        setDispenseModalItem(null);
      }, 2000);
    } catch (err) {
      alert(`Error dispensing: ${err.message}`);
    }
  };

  const handleReplenishSubmit = async (e) => {
    e.preventDefault();
    if (!replenishModalItem) return;
    try {
      await replenishItem(replenishModalItem.id, replenishQty, replenishNotes);
      setReplenishModalItem(null);
    } catch (err) {
      alert(`Error replenishing: ${err.message}`);
    }
  };

  const handleAddItemSubmit = async (e) => {
    e.preventDefault();
    if (!newItemData.name.trim()) return;
    try {
      await addItem(newItemData);
      setShowAddModal(false);
      setNewItemData({
        id: `MED-0${inventory.length + 2}`,
        category: 'Pharmaceuticals',
        name: '',
        indication: '',
        stock: 20,
        unit: 'tablets',
        minSafeStock: 5,
        shelfLifeDays: 360,
        vitalUrgency: 'Medium',
        location: 'Med-Bay Drawer C-1',
        contraindications: 'None documented'
      });
    } catch (err) {
      alert(`Error adding item: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Sample Mission Inventory Notice */}
      <div className="p-3.5 rounded-2xl bg-gray-50 dark:bg-[#1a1b1f] border border-gray-200 dark:border-[#2a2c33] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
        <div className="flex items-center space-x-2">
          <Package className="w-4 h-4 text-gray-500" />
          <span className="text-gray-600 dark:text-gray-300">
            <strong>Sample Mission Inventory:</strong> Preloaded clinical inventory for Trans-Mars Coast flight deck simulation. Persisted to SQLite table <code className="font-mono text-[11px]">medical_inventory</code>.
          </span>
        </div>
        <span className="text-[11px] px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 font-medium">
          SQLite Persistent Storage
        </span>
      </div>

      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-gray-100 dark:border-[#24252a] gap-3">
        <div>
          <span className="text-xs uppercase tracking-wider text-gray-400 font-medium">
            Module 4 – Medical Logistics
          </span>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mt-0.5">
            Med Vault: Inventory & Dispensation
          </h2>
          <p className="text-xs text-gray-400 mt-0.5">
            Track pharmaceuticals, surgical gear, and replacement bio-wearable straps. Manage emergency stock consumption and replenishment.
          </p>
        </div>

        {/* View Switcher & Add Item Button */}
        <div className="flex items-center space-x-2 text-xs">
          <div className="flex bg-gray-100 dark:bg-[#202126] p-1 rounded-xl">
            <button
              onClick={() => setActiveView('inventory')}
              className={`px-3 py-1.5 rounded-lg font-medium transition-colors ${
                activeView === 'inventory'
                  ? 'bg-white dark:bg-[#15161a] text-gray-900 dark:text-white shadow-sm'
                  : 'text-gray-500 hover:text-gray-900 dark:hover:text-white'
              }`}
            >
              Stowage ({inventory.length})
            </button>
            <button
              onClick={() => setActiveView('dispensations')}
              className={`px-3 py-1.5 rounded-lg font-medium transition-colors ${
                activeView === 'dispensations'
                  ? 'bg-white dark:bg-[#15161a] text-gray-900 dark:text-white shadow-sm'
                  : 'text-gray-500 hover:text-gray-900 dark:hover:text-white'
              }`}
            >
              Dispensations ({dispensations.length})
            </button>
            <button
              onClick={() => setActiveView('scenarios')}
              className={`px-3 py-1.5 rounded-lg font-medium transition-colors ${
                activeView === 'scenarios'
                  ? 'bg-white dark:bg-[#15161a] text-gray-900 dark:text-white shadow-sm'
                  : 'text-gray-500 hover:text-gray-900 dark:hover:text-white'
              }`}
            >
              Scenarios
            </button>
          </div>

          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center space-x-1 px-3 py-1.5 rounded-xl bg-neutral-900 text-white dark:bg-white dark:text-neutral-900 font-medium hover:bg-neutral-800 transition-colors shadow-sm"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Item</span>
          </button>
        </div>
      </div>

      {activeView === 'inventory' && (
        <>
          {/* Search & Filter Bar */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 text-xs">
            <div className="relative flex-1 max-w-sm">
              <Search className="w-3.5 h-3.5 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="Search medication or equipment..."
                className="w-full pl-9 pr-3 py-2 rounded-xl bg-white dark:bg-[#1a1b1f] border border-gray-200 dark:border-[#333] text-gray-900 dark:text-gray-100 focus:outline-none focus:border-neutral-900"
              />
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {/* Category pills */}
              <div className="flex items-center space-x-1 bg-gray-50 dark:bg-[#1e2025] p-1 rounded-lg border border-gray-100 dark:border-[#28292e] overflow-x-auto no-scrollbar">
                {categories.map(cat => (
                  <button
                    key={cat}
                    onClick={() => setSelectedCategory(cat)}
                    className={`px-2.5 py-1 rounded-md transition-colors whitespace-nowrap ${
                      selectedCategory === cat
                        ? 'bg-white dark:bg-[#15161a] text-gray-900 dark:text-white font-medium shadow-sm'
                        : 'text-gray-500 hover:text-gray-900 dark:hover:text-white'
                    }`}
                  >
                    {cat}
                  </button>
                ))}
              </div>

              {/* Low Stock Toggle */}
              <button
                onClick={() => setLowStockOnly(!lowStockOnly)}
                className={`px-3 py-1.5 rounded-lg border font-medium transition-colors ${
                  lowStockOnly
                    ? 'bg-amber-500 text-white border-amber-600'
                    : 'bg-white dark:bg-[#1a1b1f] border-gray-200 dark:border-[#333] text-gray-700 dark:text-gray-300'
                }`}
              >
                Low Stock Only
              </button>
            </div>
          </div>

          {/* Inventory Table */}
          <div className="bg-white dark:bg-[#1a1b1f] border border-gray-100 dark:border-[#27282e] rounded-2xl p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                  Med Vault Stowage Inventory
                </h3>
                <p className="text-xs text-gray-400 mt-0.5">
                  Showing {filteredInventory.length} classified items in habitat lockers.
                </p>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="text-gray-400 uppercase tracking-wider border-b border-gray-50 dark:border-[#24252a] text-[11px]">
                    <th className="pb-3 font-normal">Item</th>
                    <th className="pb-3 font-normal">Category</th>
                    <th className="pb-3 font-normal">In Stock</th>
                    <th className="pb-3 font-normal">Expires In</th>
                    <th className="pb-3 font-normal">Locker</th>
                    <th className="pb-3 font-normal">Status</th>
                    <th className="pb-3 font-normal text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50 dark:divide-[#24252a]">
                  {filteredInventory.map(item => {
                    const isLow = item.stock <= item.minSafeStock;
                    return (
                      <tr key={item.id} className="hover:bg-gray-50/50 dark:hover:bg-[#202126]">
                        <td className="py-3">
                          <span className="font-medium text-gray-900 dark:text-gray-100 block">
                            {item.name}
                          </span>
                          <span className="text-gray-400 text-[11px]">
                            {item.indication}
                          </span>
                        </td>
                        <td className="py-3 text-gray-500">
                          {item.category}
                        </td>
                        <td className="py-3">
                          <span className={`font-semibold ${isLow ? 'text-amber-600' : 'text-gray-900 dark:text-gray-100'}`}>
                            {item.stock} {item.unit}
                          </span>
                          <span className="text-gray-400 text-[10px] block">
                            Min Safe: {item.minSafeStock}
                          </span>
                        </td>
                        <td className="py-3 text-gray-500">
                          {item.shelfLifeDays} days
                        </td>
                        <td className="py-3 text-gray-500">
                          {item.location}
                        </td>
                        <td className="py-3">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                            isLow
                              ? 'bg-amber-50 text-amber-800 dark:bg-amber-950/40 dark:text-amber-300'
                              : 'bg-gray-50 text-gray-700 dark:bg-neutral-800 dark:text-gray-300'
                          }`}>
                            {item.status}
                          </span>
                        </td>
                        <td className="py-3 text-right">
                          <div className="flex items-center justify-end space-x-1.5">
                            <button
                              onClick={() => {
                                setDispenseModalItem(item);
                                setDispenseQty(1);
                              }}
                              className="px-2.5 py-1 rounded bg-neutral-900 text-white dark:bg-white dark:text-neutral-900 text-[11px] font-medium hover:bg-neutral-800 transition-colors"
                            >
                              Dispense
                            </button>
                            <button
                              onClick={() => {
                                setReplenishModalItem(item);
                                setReplenishQty(5);
                              }}
                              className="px-2 py-1 rounded border border-gray-200 dark:border-[#333] text-gray-600 dark:text-gray-300 text-[11px] hover:bg-gray-50 transition-colors"
                              title="Restock"
                            >
                              <RefreshCw className="w-3 h-3" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* Dispensations Audit Log View */}
      {activeView === 'dispensations' && (
        <div className="bg-white dark:bg-[#1a1b1f] border border-gray-100 dark:border-[#27282e] rounded-2xl p-6 shadow-sm space-y-4">
          <div>
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
              Medical Dispensation History (Audit Ledger)
            </h3>
            <p className="text-xs text-gray-400 mt-0.5">
              Every dose, bandage, or scanner checked out is recorded with authorized officer and patient context.
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="text-gray-400 uppercase tracking-wider border-b border-gray-50 dark:border-[#24252a] text-[11px]">
                  <th className="pb-3 font-normal">Timestamp</th>
                  <th className="pb-3 font-normal">Item</th>
                  <th className="pb-3 font-normal">Quantity</th>
                  <th className="pb-3 font-normal">Patient</th>
                  <th className="pb-3 font-normal">Reason</th>
                  <th className="pb-3 font-normal text-right">Authorized Officer</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50 dark:divide-[#24252a]">
                {dispensations.length === 0 ? (
                  <tr>
                    <td colSpan="6" className="py-6 text-center text-gray-400">
                      No dispensations recorded yet. Click "Dispense" on any item to log consumption.
                    </td>
                  </tr>
                ) : (
                  dispensations.map(disp => (
                    <tr key={disp.id} className="hover:bg-gray-50/50 dark:hover:bg-[#202126]">
                      <td className="py-3 font-mono text-gray-500">{disp.timestamp_met}</td>
                      <td className="py-3 font-medium text-gray-900 dark:text-gray-100">{disp.item_name}</td>
                      <td className="py-3 font-semibold">{disp.quantity} units</td>
                      <td className="py-3 text-gray-600 dark:text-gray-300">{disp.patient_astronaut_id || 'Crew'}</td>
                      <td className="py-3 text-gray-500">{disp.reason}</td>
                      <td className="py-3 text-right font-medium text-gray-900 dark:text-gray-100">{disp.authorized_by}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Emergency Scenario Supply Calculator View */}
      {activeView === 'scenarios' && (
        <div className="bg-white dark:bg-[#1a1b1f] border border-gray-100 dark:border-[#27282e] rounded-2xl p-6 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-gray-50 dark:border-[#24252a] gap-2">
            <div>
              <span className="text-xs uppercase tracking-wider text-gray-400 font-medium">
                Contingency Planning
              </span>
              <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mt-0.5">
                Emergency Supply Calculator (What-If Scenarios)
              </h3>
            </div>

            <div className="flex items-center space-x-1.5 text-xs">
              {SIMULATED_EMERGENCY_SCENARIOS.map(sc => (
                <button
                  key={sc.id}
                  onClick={() => setActiveScenarioId(sc.id)}
                  className={`px-2.5 py-1 rounded-md transition-colors ${
                    activeScenarioId === sc.id
                      ? 'bg-neutral-900 text-white dark:bg-white dark:text-neutral-900 font-medium'
                      : 'text-gray-500 hover:text-gray-900 dark:hover:text-white'
                  }`}
                >
                  {sc.name.split(' ')[1] || sc.name}
                </button>
              ))}
            </div>
          </div>

          <div className="p-4 rounded-xl bg-gray-50/70 dark:bg-[#202126] space-y-2 text-xs">
            <div className="flex justify-between items-baseline">
              <span className="font-medium text-gray-900 dark:text-gray-100 text-sm">
                {selectedScenario.name}
              </span>
              <span className="text-gray-500">
                Recovery Forecast: <strong>{selectedScenario.predictedRecoveryHours} hours</strong>
              </span>
            </div>
            <p className="text-gray-600 dark:text-gray-300">
              {selectedScenario.description}
            </p>
            <div className="pt-2 flex flex-wrap gap-2 text-[11px]">
              <span className="text-gray-400">Required:</span>
              {selectedScenario.requiredSupplies.map((req, idx) => (
                <span key={idx} className="px-2 py-0.5 rounded bg-white dark:bg-[#15161a] border border-gray-200 dark:border-[#333] text-gray-700 dark:text-gray-300">
                  {req.item} ({req.qty})
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Modal: Dispense Medication */}
      {dispenseModalItem && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-[#1a1b1f] border border-gray-100 dark:border-[#2a2c33] rounded-2xl max-w-md w-full p-6 space-y-4 shadow-xl">
            <h3 className="font-semibold text-sm text-gray-900 dark:text-gray-100">
              Dispense Medication: {dispenseModalItem.name}
            </h3>
            <p className="text-xs text-gray-500">
              Current stock: {dispenseModalItem.stock} {dispenseModalItem.unit}. Minimum safe reserve: {dispenseModalItem.minSafeStock}.
            </p>

            {dispenseSuccess ? (
              <div className="p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300 text-xs flex items-center space-x-2">
                <Check className="w-4 h-4" />
                <span>{dispenseSuccess}</span>
              </div>
            ) : (
              <form onSubmit={handleDispenseSubmit} className="space-y-3 text-xs">
                <div>
                  <label className="block text-gray-600 dark:text-gray-400 mb-1">Dispensation Quantity ({dispenseModalItem.unit})</label>
                  <input
                    type="number" min="1" max={dispenseModalItem.stock}
                    value={dispenseQty}
                    onChange={e => setDispenseQty(parseInt(e.target.value) || 1)}
                    className="w-full px-3 py-2 rounded-lg bg-gray-50 dark:bg-[#202126] border border-gray-200 dark:border-[#333] text-gray-900 dark:text-gray-100"
                  />
                </div>

                <div>
                  <label className="block text-gray-600 dark:text-gray-400 mb-1">Target Patient</label>
                  <select
                    value={dispensePatient}
                    onChange={e => setDispensePatient(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-gray-50 dark:bg-[#202126] border border-gray-200 dark:border-[#333] text-gray-900 dark:text-gray-100"
                  >
                    {crew.map(ast => (
                      <option key={ast.id} value={ast.id}>{ast.name} ({ast.role})</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-gray-600 dark:text-gray-400 mb-1">Clinical Protocol / Reason</label>
                  <input
                    type="text"
                    value={dispenseReason}
                    onChange={e => setDispenseReason(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-gray-50 dark:bg-[#202126] border border-gray-200 dark:border-[#333] text-gray-900 dark:text-gray-100"
                  />
                </div>

                <div className="flex justify-end space-x-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setDispenseModalItem(null)}
                    className="px-4 py-2 rounded-lg border border-gray-200 dark:border-[#333] text-gray-600 dark:text-gray-300"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 rounded-lg bg-neutral-900 text-white dark:bg-white dark:text-neutral-900 font-medium"
                  >
                    Confirm Dispense
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {/* Modal: Replenish Stock */}
      {replenishModalItem && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-[#1a1b1f] border border-gray-100 dark:border-[#2a2c33] rounded-2xl max-w-md w-full p-6 space-y-4 shadow-xl">
            <h3 className="font-semibold text-sm text-gray-900 dark:text-gray-100">
              Restock Item: {replenishModalItem.name}
            </h3>

            <form onSubmit={handleReplenishSubmit} className="space-y-3 text-xs">
              <div>
                <label className="block text-gray-600 dark:text-gray-400 mb-1">Replenish Quantity ({replenishModalItem.unit})</label>
                <input
                  type="number" min="1"
                  value={replenishQty}
                  onChange={e => setReplenishQty(parseInt(e.target.value) || 1)}
                  className="w-full px-3 py-2 rounded-lg bg-gray-50 dark:bg-[#202126] border border-gray-200 dark:border-[#333] text-gray-900 dark:text-gray-100"
                />
              </div>

              <div>
                <label className="block text-gray-600 dark:text-gray-400 mb-1">Restock Batch Note</label>
                <input
                  type="text"
                  value={replenishNotes}
                  onChange={e => setReplenishNotes(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-gray-50 dark:bg-[#202126] border border-gray-200 dark:border-[#333] text-gray-900 dark:text-gray-100"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setReplenishModalItem(null)}
                  className="px-4 py-2 rounded-lg border border-gray-200 dark:border-[#333] text-gray-600 dark:text-gray-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-neutral-900 text-white dark:bg-white dark:text-neutral-900 font-medium"
                >
                  Restock
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Add New Supply Item */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-[#1a1b1f] border border-gray-100 dark:border-[#2a2c33] rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-xl max-h-[90vh] overflow-y-auto">
            <h3 className="font-semibold text-sm text-gray-900 dark:text-gray-100">
              Add New Medical Supply to Med Vault
            </h3>

            <form onSubmit={handleAddItemSubmit} className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-gray-600 dark:text-gray-400 mb-1">Item ID</label>
                  <input
                    type="text"
                    value={newItemData.id}
                    onChange={e => setNewItemData(d => ({ ...d, id: e.target.value }))}
                    className="w-full px-3 py-2 rounded-lg bg-gray-50 dark:bg-[#202126] border border-gray-200 dark:border-[#333] text-gray-900 dark:text-gray-100"
                  />
                </div>
                <div>
                  <label className="block text-gray-600 dark:text-gray-400 mb-1">Category</label>
                  <select
                    value={newItemData.category}
                    onChange={e => setNewItemData(d => ({ ...d, category: e.target.value }))}
                    className="w-full px-3 py-2 rounded-lg bg-gray-50 dark:bg-[#202126] border border-gray-200 dark:border-[#333] text-gray-900 dark:text-gray-100"
                  >
                    <option value="Pharmaceuticals">Pharmaceuticals</option>
                    <option value="Critical Equipment">Critical Equipment</option>
                    <option value="Wearable Hardware">Wearable Hardware</option>
                    <option value="Supplies">Supplies</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-gray-600 dark:text-gray-400 mb-1">Item Name</label>
                <input
                  type="text" required
                  placeholder="e.g. Hydrocortisone 100mg"
                  value={newItemData.name}
                  onChange={e => setNewItemData(d => ({ ...d, name: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg bg-gray-50 dark:bg-[#202126] border border-gray-200 dark:border-[#333] text-gray-900 dark:text-gray-100"
                />
              </div>

              <div>
                <label className="block text-gray-600 dark:text-gray-400 mb-1">Clinical Indication</label>
                <input
                  type="text"
                  placeholder="e.g. Acute allergic reaction / anaphylaxis"
                  value={newItemData.indication}
                  onChange={e => setNewItemData(d => ({ ...d, indication: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg bg-gray-50 dark:bg-[#202126] border border-gray-200 dark:border-[#333] text-gray-900 dark:text-gray-100"
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-gray-600 dark:text-gray-400 mb-1">Initial Stock</label>
                  <input
                    type="number" min="1"
                    value={newItemData.stock}
                    onChange={e => setNewItemData(d => ({ ...d, stock: parseInt(e.target.value) || 0 }))}
                    className="w-full px-3 py-2 rounded-lg bg-gray-50 dark:bg-[#202126] border border-gray-200 dark:border-[#333] text-gray-900 dark:text-gray-100"
                  />
                </div>
                <div>
                  <label className="block text-gray-600 dark:text-gray-400 mb-1">Unit</label>
                  <input
                    type="text"
                    value={newItemData.unit}
                    onChange={e => setNewItemData(d => ({ ...d, unit: e.target.value }))}
                    className="w-full px-3 py-2 rounded-lg bg-gray-50 dark:bg-[#202126] border border-gray-200 dark:border-[#333] text-gray-900 dark:text-gray-100"
                  />
                </div>
                <div>
                  <label className="block text-gray-600 dark:text-gray-400 mb-1">Min Safe Stock</label>
                  <input
                    type="number" min="1"
                    value={newItemData.minSafeStock}
                    onChange={e => setNewItemData(d => ({ ...d, minSafeStock: parseInt(e.target.value) || 1 }))}
                    className="w-full px-3 py-2 rounded-lg bg-gray-50 dark:bg-[#202126] border border-gray-200 dark:border-[#333] text-gray-900 dark:text-gray-100"
                  />
                </div>
              </div>

              <div className="flex justify-end space-x-2 pt-3 border-t border-gray-100 dark:border-[#2a2c33]">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 rounded-lg border border-gray-200 dark:border-[#333] text-gray-600 dark:text-gray-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-neutral-900 text-white dark:bg-white dark:text-neutral-900 font-medium"
                >
                  Save to SQLite
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

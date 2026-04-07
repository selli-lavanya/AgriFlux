"use client";

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import api from '@/lib/api';

export default function DashboardPage() {
  const router = useRouter();
  const { role, token, logout } = useAuthStore();
  
  const [profileData, setProfileData] = useState<any>(null);
  const [farms, setFarms] = useState<any[]>([]);
  const [requests, setRequests] = useState<any[]>([]);
  const [machines, setMachines] = useState<any[]>([]);
  const [labourTeams, setLabourTeams] = useState<any[]>([]);
  
  // Modals / Form State
  const [activeTab, setActiveTab] = useState<'overview' | 'farms' | 'requests' | 'machines' | 'labour'>('overview');
  const [farmForm, setFarmForm] = useState({ name: '', size_acres: '', crop_type: '', crop_stage: 'Vegetative', location_lat: '28.61', location_lng: '77.20' });
  const [reqForm, setReqForm] = useState({ farm_id: '', type: 'machine', required_by_date: '' });
  const [machineForm, setMachineForm] = useState({ type: 'Harvester', capacity_per_day: '' });
  const [labourForm, setLabourForm] = useState({ worker_count: '', skills: 'Manual Harvesting' });

  useEffect(() => {
    if (!token) {
      router.push('/auth/login');
    } else {
      loadDashboardData();
    }
  }, [token]);

  const loadDashboardData = async () => {
    try {
      const profileRes = await api.get('/auth/me');
      setProfileData(profileRes.data);
      
      // Dynamic network fetches based strictly on user permission role
      if (profileRes.data.role === 'farmer') {
        const [farmsRes, reqRes] = await Promise.all([api.get('/farms/'), api.get('/requests/me')]);
        setFarms(farmsRes.data);
        setRequests(reqRes.data);
        if (farmsRes.data.length > 0) setReqForm(prev => ({ ...prev, farm_id: farmsRes.data[0].id.toString() }));
      } else if (profileRes.data.role === 'machine_owner') {
        const machRes = await api.get('/machines/');
        setMachines(machRes.data);
      } else if (profileRes.data.role === 'labour_team') {
        const labRes = await api.get('/labour/');
        setLabourTeams(labRes.data);
      }
    } catch {
      logout();
      router.push('/auth/login');
    }
  };

  const handleCreateFarm = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/farms/', { ...farmForm, size_acres: parseFloat(farmForm.size_acres), location_lat: parseFloat(farmForm.location_lat), location_lng: parseFloat(farmForm.location_lng) });
      alert("Farm Registered!");
      loadDashboardData();
    } catch (err) { alert("Failed to register farm."); }
  };

  const handleCreateRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/requests/', { ...reqForm, farm_id: parseInt(reqForm.farm_id), required_by_date: new Date(reqForm.required_by_date).toISOString() });
      alert("Request Deployed to Priority Engine!");
      loadDashboardData();
    } catch (err) { alert("Failed to create request."); }
  };

  const handleCreateMachine = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/machines/', { ...machineForm, capacity_per_day: parseFloat(machineForm.capacity_per_day) });
      alert("Machinery Asset Registered!");
      loadDashboardData();
    } catch (err) { alert("Failed to register asset."); }
  };

  const handleCreateLabour = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/labour/', { ...labourForm, worker_count: parseInt(labourForm.worker_count) });
      alert("Labour Syndicate Placed on Roster!");
      loadDashboardData();
    } catch (err) { alert("Failed to register roster."); }
  };

  if (!profileData) return <div className="min-h-screen bg-neutral-950 flex items-center justify-center text-emerald-500 animate-pulse font-mono">Syncing Cortex...</div>;

  return (
    <div className="min-h-screen bg-neutral-950 text-white flex">
      {/* Sidebar Navigation */}
      <aside className="w-64 bg-neutral-900 border-r border-neutral-800 flex flex-col p-6 space-y-4">
        <h2 className="text-2xl font-black bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 to-cyan-500 mb-8">AgriFlux</h2>
        
        <button onClick={() => setActiveTab('overview')} className={`text-left px-4 py-3 rounded-xl font-bold transition-colors ${activeTab === 'overview' ? 'bg-emerald-900/40 text-emerald-400 border border-emerald-500/30' : 'text-neutral-500 hover:bg-neutral-800'}`}>Overview</button>
        {role === 'farmer' && (
          <>
            <button onClick={() => setActiveTab('farms')} className={`text-left px-4 py-3 rounded-xl font-bold transition-colors ${activeTab === 'farms' ? 'bg-cyan-900/40 text-cyan-400 border border-cyan-500/30' : 'text-neutral-500 hover:bg-neutral-800'}`}>My Farms</button>
            <button onClick={() => setActiveTab('requests')} className={`text-left px-4 py-3 rounded-xl font-bold transition-colors ${activeTab === 'requests' ? 'bg-indigo-900/40 text-indigo-400 border border-indigo-500/30' : 'text-neutral-500 hover:bg-neutral-800'}`}>Logistics Requests</button>
          </>
        )}
        {role === 'machine_owner' && (
          <button onClick={() => setActiveTab('machines')} className={`text-left px-4 py-3 rounded-xl font-bold transition-colors ${activeTab === 'machines' ? 'bg-amber-900/40 text-amber-400 border border-amber-500/30' : 'text-neutral-500 hover:bg-neutral-800'}`}>Machinery Assets</button>
        )}
        {role === 'labour_team' && (
          <button onClick={() => setActiveTab('labour')} className={`text-left px-4 py-3 rounded-xl font-bold transition-colors ${activeTab === 'labour' ? 'bg-rose-900/40 text-rose-400 border border-rose-500/30' : 'text-neutral-500 hover:bg-neutral-800'}`}>Labour Rosters</button>
        )}
        
        <div className="flex-grow" />
        <button onClick={() => { logout(); router.push('/auth/login'); }} className="text-left px-4 py-3 text-rose-500 hover:bg-rose-950/30 rounded-xl font-bold transition-colors mt-auto">Sever Link</button>
      </aside>

      {/* Main Workspace */}
      <main className="flex-1 p-10 overflow-y-auto">
        <header className="mb-10 pb-6 border-b border-neutral-900">
          <h1 className="text-3xl font-extrabold tracking-tight capitalize">{activeTab} Interface</h1>
          <p className="text-neutral-500 mt-2 text-sm font-mono">Operator ID: {profileData.email} | Clearance: <span className="text-emerald-400 uppercase">{role}</span></p>
        </header>

        {activeTab === 'overview' && (
          <div className="grid grid-cols-2 gap-6">
            <div className="bg-neutral-900 border border-neutral-800 p-6 rounded-2xl shadow-xl">
              <h3 className="text-neutral-500 font-bold uppercase tracking-widest text-xs mb-4">Network Status</h3>
              <p className="text-emerald-400 flex items-center gap-3">
                <span className="relative flex h-3 w-3"><span className="animate-ping absolute h-full w-full rounded-full bg-emerald-400 opacity-75"></span><span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span></span>
                Securely connected to AI API Layer
              </p>
            </div>
            {role === 'machine_owner' && (
              <div className="bg-neutral-900 border border-neutral-800 p-6 rounded-2xl shadow-xl">
                <h3 className="text-neutral-500 font-bold uppercase tracking-widest text-xs mb-4">Total Assets</h3>
                <span className="block text-4xl font-extrabold text-amber-400">{machines.length}</span>
                <span className="text-xs text-neutral-500 uppercase">Registered Hardware</span>
              </div>
            )}
            {role === 'labour_team' && (
              <div className="bg-neutral-900 border border-neutral-800 p-6 rounded-2xl shadow-xl">
                <h3 className="text-neutral-500 font-bold uppercase tracking-widest text-xs mb-4">Total Workforce</h3>
                <span className="block text-4xl font-extrabold text-rose-400">{labourTeams.length}</span>
                <span className="text-xs text-neutral-500 uppercase">Available Groups</span>
              </div>
            )}
          </div>
        )}

        {/* Existing Farmer Tabs (Omitted for brevity in edit, but kept fully functional) */}
        {activeTab === 'farms' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <div className="bg-neutral-900 border border-neutral-800 rounded-3xl p-8">
                <h3 className="text-xl font-bold mb-6 text-cyan-400">Register New Farm</h3>
                <form onSubmit={handleCreateFarm} className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <input required placeholder="Farm Name" className="col-span-2 bg-black border border-neutral-800 p-3 rounded-xl text-sm" value={farmForm.name} onChange={e => setFarmForm({...farmForm, name: e.target.value})} />
                    <input required type="number" step="0.1" placeholder="Size (Acres)" className="bg-black border border-neutral-800 p-3 rounded-xl text-sm" value={farmForm.size_acres} onChange={e => setFarmForm({...farmForm, size_acres: e.target.value})} />
                    <input required placeholder="Crop Type" className="bg-black border border-neutral-800 p-3 rounded-xl text-sm" value={farmForm.crop_type} onChange={e => setFarmForm({...farmForm, crop_type: e.target.value})} />
                    <select className="col-span-2 bg-black border border-neutral-800 p-3 rounded-xl text-sm text-neutral-300" value={farmForm.crop_stage} onChange={e => setFarmForm({...farmForm, crop_stage: e.target.value})}>
                      <option value="Vegetative">Vegetative</option>
                      <option value="Harvest-Ready">Harvest-Ready</option>
                    </select>
                  </div>
                  <button type="submit" className="w-full bg-cyan-600/20 text-cyan-400 font-bold py-3 rounded-xl outline-none">Register Terrain</button>
                </form>
              </div>
              <div className="space-y-4">
                <h3 className="text-xl font-bold text-white mb-6">Registered Database</h3>
                {farms.map(farm => (
                  <div key={farm.id} className="bg-black/50 border border-neutral-800 p-5 rounded-2xl flex justify-between group">
                    <div><h4 className="font-bold text-emerald-100">{farm.name}</h4><p className="text-xs text-neutral-500">{farm.size_acres} Acres</p></div>
                  </div>
                ))}
              </div>
            </div>
        )}

        {activeTab === 'requests' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <div className="bg-neutral-900 border border-neutral-800 rounded-3xl p-8">
                <h3 className="text-xl font-bold mb-6 text-indigo-400">Deploy Request</h3>
                <form onSubmit={handleCreateRequest} className="space-y-4">
                  <select required className="w-full bg-black border border-neutral-800 p-3 rounded-xl text-sm text-neutral-300" value={reqForm.farm_id} onChange={e => setReqForm({...reqForm, farm_id: e.target.value})}>
                    <option value="" disabled>Target Farm...</option>
                    {farms.map(f => <option key={f.id} value={f.id}>{f.name}</option>)}
                  </select>
                  <select required className="w-full bg-black border border-neutral-800 p-3 rounded-xl text-sm" value={reqForm.type} onChange={e => setReqForm({...reqForm, type: e.target.value})}>
                    <option value="machine">Machinery</option>
                    <option value="labour">Labour</option>
                  </select>
                  <input required type="date" className="w-full bg-black border border-neutral-800 p-3 rounded-xl text-sm text-neutral-400" value={reqForm.required_by_date} onChange={e => setReqForm({...reqForm, required_by_date: e.target.value})} />
                  <button type="submit" disabled={!reqForm.farm_id} className="w-full bg-indigo-600/20 text-indigo-400 py-3 rounded-xl font-bold">Signal Engine</button>
                </form>
              </div>
              <div className="space-y-4">
                {requests.map(req => (
                  <div key={req.id} className="bg-black/50 border border-neutral-800 p-5 rounded-2xl">
                    <p className="font-bold uppercase text-indigo-300">{req.type} Requirement</p>
                    <p className="text-xs text-neutral-500 mt-2">Needed by: {req.required_by_date ? req.required_by_date.split('T')[0] : 'TBD'}</p>
                    <p className="text-2xl mt-2 font-black text-white">{req.priority_score.toFixed(1)} <span className="text-[10px] text-neutral-500 uppercase">Score</span></p>
                  </div>
                ))}
              </div>
            </div>
        )}

        {/* Phase 11: Machine Owner Module */}
        {activeTab === 'machines' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <div className="bg-neutral-900 border border-neutral-800 rounded-3xl p-8">
                <h3 className="text-xl font-bold mb-6 text-amber-400">Register Machinery</h3>
                <form onSubmit={handleCreateMachine} className="space-y-4">
                  <select required className="w-full bg-black border border-neutral-800 p-3 rounded-xl text-sm text-neutral-300" value={machineForm.type} onChange={e => setMachineForm({...machineForm, type: e.target.value})}>
                    <option value="Harvester">Heavy Harvester</option>
                    <option value="Tractor">Utility Tractor</option>
                    <option value="Drone">Pesticide Drone</option>
                  </select>
                  <input required type="number" step="0.1" placeholder="Capacity (Acres / Day)" className="w-full bg-black border border-neutral-800 p-3 rounded-xl text-sm" value={machineForm.capacity_per_day} onChange={e => setMachineForm({...machineForm, capacity_per_day: e.target.value})} />
                  <button type="submit" className="w-full bg-amber-600/20 text-amber-400 font-bold py-3 rounded-xl outline-none">Register Hardware Asset</button>
                </form>
              </div>
              <div className="space-y-4">
                <h3 className="text-xl font-bold text-white mb-6">Secured Asset Inventory</h3>
                {machines.map(mach => (
                  <div key={mach.id} className="bg-black/50 border border-neutral-800 p-5 rounded-2xl flex justify-between items-center group shadow-xl">
                    <div>
                      <h4 className="font-bold text-lg text-amber-100">{mach.type}</h4>
                      <p className="text-xs text-neutral-500">Rated Capacity: {mach.capacity_per_day} Acres daily</p>
                    </div>
                    <span className="px-3 py-1 bg-amber-900/30 border border-amber-700/50 text-xs rounded-full text-amber-400">#ACD-{mach.id}</span>
                  </div>
                ))}
              </div>
            </div>
        )}

        {/* Phase 11: Labour Team Module */}
        {activeTab === 'labour' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <div className="bg-neutral-900 border border-neutral-800 rounded-3xl p-8">
                <h3 className="text-xl font-bold mb-6 text-rose-400">Register Syndicate Force</h3>
                <form onSubmit={handleCreateLabour} className="space-y-4">
                  <input required type="number" min="1" placeholder="Total Worker Count" className="w-full bg-black border border-neutral-800 p-3 rounded-xl text-sm" value={labourForm.worker_count} onChange={e => setLabourForm({...labourForm, worker_count: e.target.value})} />
                  <input required placeholder="Primary Skills (e.g. Rice Seeding)" className="w-full bg-black border border-neutral-800 p-3 rounded-xl text-sm" value={labourForm.skills} onChange={e => setLabourForm({...labourForm, skills: e.target.value})} />
                  <button type="submit" className="w-full bg-rose-600/20 text-rose-400 font-bold py-3 rounded-xl outline-none">Mobilize Workforce Roster</button>
                </form>
              </div>
              <div className="space-y-4">
                <h3 className="text-xl font-bold text-white mb-6">Registered Workforce</h3>
                {labourTeams.map(team => (
                  <div key={team.id} className="bg-black/50 border border-neutral-800 p-5 rounded-2xl flex justify-between items-center group shadow-xl">
                    <div>
                      <h4 className="font-bold text-lg text-rose-100">{team.worker_count} Personnel</h4>
                      <p className="text-xs text-neutral-500">Specialization: {team.skills}</p>
                    </div>
                    <span className="px-3 py-1 bg-rose-900/30 border border-rose-700/50 text-xs rounded-full text-rose-400">Active</span>
                  </div>
                ))}
              </div>
            </div>
        )}

      </main>
    </div>
  );
}

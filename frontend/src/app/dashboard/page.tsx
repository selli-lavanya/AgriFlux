"use client";

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import api from '@/lib/api';
import dynamic from 'next/dynamic';
import { fetchAddressFromCoordinates } from '@/lib/geocoder';

const LeafletMap = dynamic(() => import('@/components/MapOverlay'), { ssr: false });
const LocationPickerMap = dynamic(() => import('@/components/LocationPickerMap'), { ssr: false });

export default function DashboardPage() {
  const router = useRouter();
  const { role, token, logout } = useAuthStore();
  
  const [profileData, setProfileData] = useState<any>(null);
  const [farms, setFarms] = useState<any[]>([]);
  const [requests, setRequests] = useState<any[]>([]);
  const [machines, setMachines] = useState<any[]>([]);
  const [labourTeams, setLabourTeams] = useState<any[]>([]);
  const [assignments, setAssignments] = useState<any[]>([]);
  const [calendar, setCalendar] = useState<any[]>([]);
  
  // Phase 10 & 16 Farm Registry State
  const [newFarm, setNewFarm] = useState({ 
    name: '', size_acres: '', location_lat: 28.6139, location_lng: 77.2090, 
    location_label: '', full_address: '', crop_type: '', crop_stage: 'Sowing' 
  });
  const [isResolvingAddress, setIsResolvingAddress] = useState(false);
  
  // Modals / Form State
  const [activeTab, setActiveTab] = useState<'overview' | 'farms' | 'requests' | 'machines' | 'labour' | 'dispatcher' | 'tasks' | 'calendar'>('overview');
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
      const calRes = await api.get('/assignments/availability');
      setCalendar(calRes.data);
      
      if (profileRes.data.role === 'farmer') {
        const [farmsRes, reqRes] = await Promise.all([api.get('/farms/'), api.get('/requests/me')]);
        setFarms(farmsRes.data);
        setRequests(reqRes.data);
        if (farmsRes.data.length > 0) setReqForm(prev => ({ ...prev, farm_id: farmsRes.data[0].id.toString() }));
      } else if (profileRes.data.role === 'machine_owner') {
        const [machRes, assignRes] = await Promise.all([api.get('/machines/'), api.get('/assignments/my-tasks')]);
        setMachines(machRes.data);
        setAssignments(assignRes.data);
      } else if (profileRes.data.role === 'labour_team') {
        const [labRes, assignRes] = await Promise.all([api.get('/labour/'), api.get('/assignments/my-tasks')]);
        setLabourTeams(labRes.data);
        setAssignments(assignRes.data);
      } else if (profileRes.data.role === 'admin') {
        // Phase 12: Admin specific fetches
        const [pendRes, allMachRes, allLabRes, allFarmsRes] = await Promise.all([
          api.get('/requests/pending'),
          api.get('/machines/all'),
          api.get('/labour/all'),
          api.get('/farms/all') // Phase 15 Global mapping
        ]);
        setRequests(pendRes.data);
        setMachines(allMachRes.data);
        setLabourTeams(allLabRes.data);
        setFarms(allFarmsRes.data);
      }
    } catch {
      logout();
      router.push('/auth/login');
    }
  };

  // Farmer Form Logic
  const handleCreateFarm = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = {
        name: newFarm.name,
        size_acres: parseFloat(newFarm.size_acres),
        location_lat: Number(newFarm.location_lat),
        location_lng: Number(newFarm.location_lng),
        location_label: newFarm.location_label || null,
        full_address: newFarm.full_address || null,
        crop_type: newFarm.crop_type,
        crop_stage: newFarm.crop_stage
      };
      await api.post('/farms/', payload);
      const farmsRes = await api.get('/farms/');
      setFarms(farmsRes.data);
      setNewFarm({ name: '', size_acres: '', location_lat: 28.6139, location_lng: 77.2090, location_label: '', full_address: '', crop_type: '', crop_stage: 'Sowing' });
      alert("Farm Registered With Verifiable Location Intelligence!");
    } catch {
      alert("Registration failed");
    }
  };

  const executeBrowserGPS = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition((pos) => {
        handleMapCoordinateChange(pos.coords.latitude, pos.coords.longitude);
      }, () => alert("GPS Permission Denied. Drag the pin manually."));
    }
  };

  const handleMapCoordinateChange = async (lat: number, lng: number) => {
    setNewFarm(prev => ({ ...prev, location_lat: lat, location_lng: lng }));
  };

  const resolveSemanticAddress = async () => {
    setIsResolvingAddress(true);
    const data = await fetchAddressFromCoordinates(newFarm.location_lat, newFarm.location_lng);
    setIsResolvingAddress(false);
    if (data) {
       setNewFarm(prev => ({ ...prev, full_address: data.address, location_label: prev.location_label || data.label }));
    } else {
       alert("Target resides in an unmapped sector entirely.");
    }
  };

  const handleCreateRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/requests/', { ...reqForm, farm_id: parseInt(reqForm.farm_id), required_by_date: new Date(reqForm.required_by_date).toISOString() });
      alert("Request Deployed to Priority Engine!");
      loadDashboardData();
    } catch (err) { alert("Failed to create request."); }
  };

  // Provider Form Logic
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

  const handleCompleteTask = async (id: number) => {
    try {
      await api.put(`/assignments/${id}/complete`);
      alert("Task documented as COMPLETE. Supply Chain Notified.");
      loadDashboardData();
    } catch (err) { alert("Failed to finalize completion report."); }
  };

  // Admin Matching Logic
  const executeEngineTrigger = async () => {
    try {
      const res = await api.post('/requests/trigger-engine');
      alert(`Prioritization Complete: ${res.data.processed_count} requests evaluated!`);
      loadDashboardData();
    } catch { alert("Engine computation failed"); }
  };

  const executeAssignment = async (requestId: number, resourceId: number, type: string) => {
    try {
      await api.post('/assignments/', {
        request_id: requestId,
        resource_id: resourceId,
        resource_type: type,
        scheduled_date: new Date().toISOString()
      });
      alert("Match Successfully Authenticated & Sent!");
      loadDashboardData();
    } catch (err: any) { alert(err.response?.data?.detail || "Failed to secure mapping contract!"); }
  };

  if (!profileData) return <div className="min-h-screen bg-neutral-950 flex items-center justify-center text-emerald-500 animate-pulse font-mono">Syncing Cortex...</div>;

  return (
    <div className="min-h-screen bg-neutral-950 text-white flex">
      {/* Sidebar Navigation */}
      <aside className="w-64 bg-neutral-900 border-r border-neutral-800 flex flex-col p-6 space-y-4">
        <h2 className="text-2xl font-black bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 to-cyan-500 mb-8">AgriFlux</h2>
        <button onClick={() => setActiveTab('overview')} className={`text-left px-4 py-3 rounded-xl font-bold transition-colors ${activeTab === 'overview' ? 'bg-emerald-900/40 text-emerald-400 border border-emerald-500/30' : 'text-neutral-500 hover:bg-neutral-800'}`}>Overview</button>
        <button onClick={() => setActiveTab('calendar')} className={`text-left px-4 py-3 rounded-xl font-bold transition-colors ${activeTab === 'calendar' ? 'bg-fuchsia-900/40 text-fuchsia-400 border border-fuchsia-500/30' : 'text-neutral-500 hover:bg-neutral-800'}`}>Availability Engine</button>
        {role === 'farmer' && (
          <>
            <button onClick={() => setActiveTab('farms')} className={`text-left px-4 py-3 rounded-xl font-bold transition-colors ${activeTab === 'farms' ? 'bg-cyan-900/40 text-cyan-400 border border-cyan-500/30' : 'text-neutral-500 hover:bg-neutral-800'}`}>My Farms</button>
            <button onClick={() => setActiveTab('requests')} className={`text-left px-4 py-3 rounded-xl font-bold transition-colors ${activeTab === 'requests' ? 'bg-indigo-900/40 text-indigo-400 border border-indigo-500/30' : 'text-neutral-500 hover:bg-neutral-800'}`}>Logistics Requests</button>
          </>
        )}
        {role === 'admin' && (
          <button onClick={() => setActiveTab('dispatcher')} className={`text-left px-4 py-3 rounded-xl font-bold transition-colors ${activeTab === 'dispatcher' ? 'bg-purple-900/40 text-purple-400 border border-purple-500/30' : 'text-neutral-500 hover:bg-neutral-800'}`}>System Dispatcher</button>
        )}
        {(role === 'machine_owner' || role === 'admin') && <button onClick={() => setActiveTab('machines')} className={`text-left px-4 py-3 rounded-xl font-bold transition-colors ${activeTab === 'machines' ? 'bg-amber-900/40 text-amber-400 border border-amber-500/30' : 'text-neutral-500 hover:bg-neutral-800'}`}>Machinery Assets</button>}
        {(role === 'labour_team' || role === 'admin') && <button onClick={() => setActiveTab('labour')} className={`text-left px-4 py-3 rounded-xl font-bold transition-colors ${activeTab === 'labour' ? 'bg-rose-900/40 text-rose-400 border border-rose-500/30' : 'text-neutral-500 hover:bg-neutral-800'}`}>Labour Rosters</button>}
        {(role === 'machine_owner' || role === 'labour_team') && (
          <button onClick={() => setActiveTab('tasks')} className={`text-left px-4 py-3 rounded-xl font-bold transition-colors ${activeTab === 'tasks' ? 'bg-indigo-900/40 text-indigo-400 border border-indigo-500/30' : 'text-neutral-500 hover:bg-neutral-800'}`}>My Assignments</button>
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
                Securely connected to Operational API
              </p>
            </div>
            {role === 'admin' && (
              <div className="bg-neutral-900 border border-emerald-900/50 p-6 rounded-2xl shadow-[0_0_15px_rgba(52,211,153,0.1)]">
                 <h3 className="text-emerald-500 font-bold uppercase tracking-widest text-xs mb-4 border-b border-emerald-900/30 pb-2">Admin Overrides</h3>
                 <button onClick={executeEngineTrigger} className="bg-emerald-500 text-black px-6 py-3 font-bold rounded-xl mt-2 hover:bg-emerald-400 transition-colors shadow-lg">Run Priority Recalculation Engine</button>
              </div>
            )}
          </div>
        )}

        {/* Phase 14: Availability Calendar Core */}
        {activeTab === 'calendar' && (
          <div className="space-y-6">
            <h3 className="text-2xl font-bold text-fuchsia-400 border-b border-neutral-800 pb-4">7-Day Supply / Demand Projection</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {calendar.map((day, idx) => (
                <div key={idx} className="bg-neutral-900 border border-fuchsia-900/30 rounded-2xl p-6 shadow-xl relative overflow-hidden">
                  <div className={`absolute top-0 w-full h-1 left-0 ${day.machines.available === 0 || day.labour.available === 0 ? 'bg-rose-500 shadow-[0_0_10px_red]' : 'bg-fuchsia-500'}`} />
                  <h4 className="text-xl text-white font-black uppercase tracking-widest mb-4">{new Date(day.date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}</h4>
                  <div className="space-y-4">
                    <div className="bg-black/50 p-3 rounded-xl border border-neutral-800">
                      <p className="text-xs text-neutral-500 font-bold uppercase mb-1">Machinery Network Matrix</p>
                      <p className="text-lg font-bold text-amber-400">{day.machines.available} <span className="text-xs text-neutral-500">Available</span> / {day.machines.booked} <span className="text-xs text-rose-500">Booked</span></p>
                    </div>
                    <div className="bg-black/50 p-3 rounded-xl border border-neutral-800">
                      <p className="text-xs text-neutral-500 font-bold uppercase mb-1">Labour Network Matrix</p>
                      <p className="text-lg font-bold text-rose-400">{day.labour.available} <span className="text-xs text-neutral-500">Available</span> / {day.labour.booked} <span className="text-xs text-rose-500">Booked</span></p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Farmer Tabs */}
        {activeTab === 'farms' && (
            <div className="bg-neutral-900 border border-neutral-800 rounded-3xl p-8">
              <h3 className="text-xl font-bold mb-6 text-emerald-400">Register New Farm Operation</h3>
              <form onSubmit={handleCreateFarm} className="space-y-6">
                
                {/* Core Attributes */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <input type="text" placeholder="Farm Name (e.g. Omega Fields)" className="w-full bg-black/50 border border-neutral-700/50 p-3 rounded-xl focus:border-emerald-500 focus:outline-none" value={newFarm.name} onChange={e => setNewFarm({...newFarm, name: e.target.value})} required />
                  <input type="number" placeholder="Size (Acres)" className="w-full bg-black/50 border border-neutral-700/50 p-3 rounded-xl focus:border-emerald-500 focus:outline-none" value={newFarm.size_acres} onChange={e => setNewFarm({...newFarm, size_acres: e.target.value})} required />
                  <input type="text" placeholder="Crop Type (e.g. Wheat, Rice)" className="w-full bg-black/50 border border-neutral-700/50 p-3 rounded-xl focus:border-emerald-500 focus:outline-none" value={newFarm.crop_type} onChange={e => setNewFarm({...newFarm, crop_type: e.target.value})} required />
                  <select className="w-full bg-black/50 border border-neutral-700/50 p-3 rounded-xl focus:border-emerald-500 focus:outline-none text-neutral-300" value={newFarm.crop_stage} onChange={e => setNewFarm({...newFarm, crop_stage: e.target.value})}>
                    <option value="Sowing">Sowing Phase</option>
                    <option value="Vegetative">Vegetative Phase</option>
                    <option value="Harvesting">Harvesting Phase</option>
                  </select>
                </div>

                {/* Location Intelligence Canvas */}
                <div className="mt-8 border border-neutral-800 rounded-2xl overflow-hidden bg-black/50">
                   <div className="flex flex-col md:flex-row justify-between items-center p-4 border-b border-neutral-800 bg-neutral-900/50">
                      <h4 className="text-sm font-bold text-gray-300">Geospatial Target</h4>
                      <button type="button" onClick={executeBrowserGPS} className="mt-2 md:mt-0 text-xs font-bold bg-blue-600/20 text-blue-400 hover:bg-blue-600/40 px-3 py-1.5 rounded transition">
                        📡 Ping Mobile GPS
                      </button>
                   </div>
                   <div className="grid grid-cols-1 lg:grid-cols-2">
                       <div className="h-[250px] w-full bg-neutral-800">
                          <LocationPickerMap lat={newFarm.location_lat} lng={newFarm.location_lng} onChange={handleMapCoordinateChange} />
                       </div>
                       <div className="p-6 space-y-4 flex flex-col justify-center">
                          <button type="button" onClick={resolveSemanticAddress} disabled={isResolvingAddress} className="w-full bg-emerald-600/20 text-emerald-400 border border-emerald-900/50 hover:bg-emerald-600/40 font-bold text-sm py-2 rounded-lg transition text-center mb-2 disabled:opacity-50">
                            {isResolvingAddress ? "Resolving OpenStreetMap..." : "Extract Semantic Address"}
                          </button>
                          <div>
                            <label className="text-[10px] font-bold text-gray-500 uppercase">Sector Label (Override)</label>
                            <input type="text" placeholder="e.g. North River Block" className="w-full mt-1 bg-black/80 border border-neutral-800 p-2 rounded focus:border-emerald-500 focus:outline-none text-sm" value={newFarm.location_label} onChange={e => setNewFarm({...newFarm, location_label: e.target.value})} />
                          </div>
                          <div>
                            <label className="text-[10px] font-bold text-gray-500 uppercase">Verifiable Logistics Address</label>
                            <textarea rows={2} placeholder="Resolves automatically via Geocoder..." className="w-full mt-1 bg-black/80 border border-neutral-800 p-2 rounded focus:border-emerald-500 focus:outline-none text-xs text-gray-400" value={newFarm.full_address} onChange={e => setNewFarm({...newFarm, full_address: e.target.value})} />
                          </div>
                       </div>
                   </div>
                </div>

                <button type="submit" className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-3 mt-4 rounded-xl transition-all shadow-lg hover:shadow-emerald-500/30">Commit Farm to Matrix</button>
              </form>

              <div className="mt-12 space-y-4">
                <h3 className="text-xl font-bold mb-4 border-b border-neutral-800 pb-2">Active Territories</h3>
                {farms.map(f => (
                  <div key={f.id} className="bg-neutral-800/50 p-4 rounded-2xl flex justify-between items-center border border-neutral-800">
                    <div>
                      <h4 className="font-bold text-emerald-400">{f.location_label ? `${f.name} (${f.location_label})` : f.name}</h4>
                      <p className="text-xs text-neutral-400 font-mono mt-1">[{f.location_lat.toFixed(4)}, {f.location_lng.toFixed(4)}] • {f.size_acres} Acres • {f.crop_type}</p>
                      {f.full_address && <p className="text-[10px] text-gray-500 mt-1 uppercase max-w-lg truncate">{f.full_address}</p>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
        )}

        {activeTab === 'requests' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Map Layer for farmers */}
              <div className="lg:col-span-2 h-[450px] w-full rounded-2xl overflow-hidden shadow-2xl relative border border-indigo-900/30">
                 <div className="absolute top-2 left-2 z-[500] bg-black/80 p-2 rounded-lg text-xs font-bold uppercase tracking-widest text-indigo-400 border border-indigo-900/50">My Farm Intelligence Map</div>
                 <LeafletMap requests={requests} farms={farms} machines={machines} labourTeams={labourTeams} role={role || ''} />
              </div>
              
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
                  <button type="submit" disabled={!reqForm.farm_id} className="w-full bg-indigo-600/20 text-indigo-400 hover:bg-indigo-500 hover:text-white py-3 rounded-xl font-bold transition-colors">Signal Engine</button>
                </form>
              </div>
              <div className="space-y-4">
                {requests.map(req => (
                  <div key={req.id} className="bg-black/50 border border-neutral-800 p-5 rounded-2xl">
                    <div className="flex justify-between items-start mb-2"><p className="font-bold uppercase text-indigo-300">{req.type} Requirement</p><span className="text-[10px] font-bold px-2 py-1 bg-neutral-800 text-neutral-300 rounded-md">{req.status}</span></div>
                    <p className="text-xs text-neutral-500 mt-2">Needed by: {req.required_by_date ? req.required_by_date.split('T')[0] : 'TBD'}</p>
                    <p className="text-2xl mt-2 font-black text-white">{req.priority_score.toFixed(1)} <span className="text-[10px] text-neutral-500 uppercase">Score</span></p>
                  </div>
                ))}
              </div>
            </div>
        )}

        {/* Phase 11 & 12: Machine / Labour Network Asset Viewer */}
        {activeTab === 'machines' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {role === 'machine_owner' && (
                <div className="bg-neutral-900 border border-neutral-800 rounded-3xl p-8">
                  <h3 className="text-xl font-bold mb-6 text-amber-400">Register Machinery</h3>
                  <form onSubmit={handleCreateMachine} className="space-y-4">
                    <select required className="w-full bg-black border border-neutral-800 p-3 rounded-xl text-sm text-neutral-300" value={machineForm.type} onChange={e => setMachineForm({...machineForm, type: e.target.value})}>
                      <option value="Harvester">Heavy Harvester</option>
                      <option value="Tractor">Utility Tractor</option><option value="Drone">Pesticide Drone</option>
                    </select>
                    <input required type="number" step="0.1" placeholder="Capacity (Acres / Day)" className="w-full bg-black border border-neutral-800 p-3 rounded-xl text-sm" value={machineForm.capacity_per_day} onChange={e => setMachineForm({...machineForm, capacity_per_day: e.target.value})} />
                    <button type="submit" className="w-full bg-amber-600/20 text-amber-400 hover:bg-amber-500 hover:text-black font-bold py-3 rounded-xl outline-none transition-colors">Register Hardware Asset</button>
                  </form>
                </div>
              )}
              <div className={`space-y-4 ${role === 'admin' ? 'lg:col-span-2' : ''}`}>
                <h3 className="text-xl font-bold text-white mb-6">{role === 'admin' ? 'Global Network Assets' : 'Secured Asset Inventory'}</h3>
                {machines.map(mach => (
                  <div key={mach.id} className="bg-black/50 border border-neutral-800 p-5 rounded-2xl flex justify-between items-center">
                    <div><h4 className="font-bold text-lg text-amber-100">{mach.type}</h4><p className="text-xs text-neutral-500">Rated Capacity: {mach.capacity_per_day} Acres daily</p></div>
                    <span className="px-3 py-1 bg-amber-900/30 border border-amber-700/50 text-xs rounded-full text-amber-400">#ACD-{mach.id}</span>
                  </div>
                ))}
              </div>
            </div>
        )}

        {activeTab === 'labour' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {role === 'labour_team' && (
                <div className="bg-neutral-900 border border-neutral-800 rounded-3xl p-8">
                  <h3 className="text-xl font-bold mb-6 text-rose-400">Register Syndicate Force</h3>
                  <form onSubmit={handleCreateLabour} className="space-y-4">
                    <input required type="number" min="1" placeholder="Total Worker Count" className="w-full bg-black border border-neutral-800 p-3 rounded-xl text-sm" value={labourForm.worker_count} onChange={e => setLabourForm({...labourForm, worker_count: e.target.value})} />
                    <input required placeholder="Primary Skills" className="w-full bg-black border border-neutral-800 p-3 rounded-xl text-sm" value={labourForm.skills} onChange={e => setLabourForm({...labourForm, skills: e.target.value})} />
                    <button type="submit" className="w-full bg-rose-600/20 text-rose-400 hover:bg-rose-500 hover:text-white font-bold py-3 rounded-xl outline-none transition-colors">Mobilize Workforce Roster</button>
                  </form>
                </div>
              )}
              <div className={`space-y-4 ${role === 'admin' ? 'lg:col-span-2' : ''}`}>
                <h3 className="text-xl font-bold text-white mb-6">{role === 'admin' ? 'Global Active Squads' : 'Registered Workforce'}</h3>
                {labourTeams.map(team => (
                  <div key={team.id} className="bg-black/50 border border-neutral-800 p-5 rounded-2xl flex justify-between items-center">
                    <div><h4 className="font-bold text-lg text-rose-100">{team.worker_count} Personnel</h4><p className="text-xs text-neutral-500">Specialization: {team.skills}</p></div>
                    <span className="px-3 py-1 bg-rose-900/30 border border-rose-700/50 text-xs rounded-full text-rose-400">Active</span>
                  </div>
                ))}
              </div>
            </div>
        )}

        {/* Phase 13: Provider Task Execution Loop */}
        {activeTab === 'tasks' && (role === 'machine_owner' || role === 'labour_team') && (
          <div className="space-y-6">
            <h3 className="text-2xl font-bold text-indigo-400 border-b border-neutral-800 pb-4">Active Dispatch Contracts</h3>
            <div className="grid gap-6">
              {assignments.map(task => (
                <div key={task.id} className="p-6 rounded-2xl border border-neutral-800 bg-neutral-900 shadow-lg flex justify-between items-center group">
                  <div>
                    <p className="font-bold text-white mb-1 uppercase tracking-widest text-sm">Request ID #{task.request_id}</p>
                    <p className="text-xs text-neutral-500">Expected Window: <span className="text-indigo-300">{new Date(task.scheduled_date).toLocaleDateString()}</span></p>
                    <div className="mt-4 flex gap-2">
                       <span className={`px-2 py-1 text-[10px] uppercase font-bold rounded-full ${task.status === 'completed' ? 'bg-emerald-900/40 text-emerald-400 border border-emerald-500/30' : 'bg-amber-900/40 text-amber-400 border border-amber-500/30'}`}>{task.status}</span>
                    </div>
                  </div>
                  {task.status !== 'completed' && (
                    <button onClick={() => handleCompleteTask(task.id)} className="bg-emerald-600/20 text-emerald-400 hover:bg-emerald-500 hover:text-black transition-colors px-6 py-3 rounded-xl font-bold text-sm shadow-xl">
                      Mark as Completed
                    </button>
                  )}
                </div>
              ))}
              {assignments.length === 0 && <p className="text-neutral-500">No contracts assigned to you yet.</p>}
            </div>
          </div>
        )}

        {/* Phase 12: Admin System Dispatcher Module */}
        {activeTab === 'dispatcher' && role === 'admin' && (
            <div className="space-y-8">
              <h3 className="text-2xl font-bold text-purple-400 border-b border-neutral-800 pb-4">Global Queue Map</h3>
              
              {/* Core Map */}
              <div className="w-full h-[550px] bg-neutral-900 border border-purple-900/50 rounded-2xl relative shadow-[0_0_20px_rgba(168,85,247,0.15)] overflow-hidden">
                <div className="absolute top-2 left-2 z-[500] bg-black/80 p-2 rounded-lg text-xs font-bold uppercase tracking-widest text-purple-400 border border-purple-900/50">Admin Spatial Overseer</div>
                <LeafletMap requests={requests} farms={farms} machines={machines} labourTeams={labourTeams} role={role} />
              </div>

              {requests.map(req => (
                <div key={req.id} className="bg-neutral-900 border border-purple-900/30 p-6 rounded-3xl flex flex-col md:flex-row gap-6 shadow-xl">
                  
                  {/* Info Block */}
                  <div className="flex-1">
                    <span className="text-2xl font-black text-white">{req.priority_score.toFixed(1)} <span className="text-[10px] text-purple-500 uppercase">Risk Score</span></span>
                    <h4 className="font-bold uppercase text-neutral-300 mt-2">{req.type} Requirement</h4>
                    <p className="text-xs text-neutral-400 mt-1">Farm ID: #{req.farm_id} • Due: {req.required_by_date ? req.required_by_date.split('T')[0] : 'TBD'}</p>
                    <p className="text-[10px] text-purple-400 font-mono mt-3 uppercase tracking-widest bg-purple-900/20 inline-block px-2 py-1 rounded">{req.priority_reason || 'Base Network Priority'}</p>
                  </div>

                  {/* Matching Engine Action Block */}
                  <div className="flex-1 bg-black/60 p-4 rounded-xl border border-neutral-800">
                    <h5 className="text-xs text-neutral-500 font-bold uppercase mb-4">Execute AI Overlay Contract</h5>
                    <div className="space-y-2">
                       {req.type === 'machine' ? machines.map(m => (
                         <button key={m.id} onClick={() => executeAssignment(req.id, m.id, 'machine')} className="w-full text-left px-4 py-3 bg-amber-900/20 hover:bg-amber-600/40 border border-amber-700/30 rounded-lg text-amber-200 text-sm transition-all group">
                           Assign <span className="font-bold">Hardware #{m.id}</span> <span className="float-right text-xs opacity-50 group-hover:opacity-100">{m.type}</span>
                         </button>
                       )) : labourTeams.map(l => (
                         <button key={l.id} onClick={() => executeAssignment(req.id, l.id, 'labour')} className="w-full text-left px-4 py-3 bg-rose-900/20 hover:bg-rose-600/40 border border-rose-700/30 rounded-lg text-rose-200 text-sm transition-all group">
                           Assign <span className="font-bold">Roster #{l.id}</span> <span className="float-right text-xs opacity-50 group-hover:opacity-100">{l.worker_count} workers</span>
                         </button>
                       ))}
                    </div>
                  </div>
                </div>
              ))}
              {requests.length === 0 && <p className="text-neutral-500">No pending requests isolated on the grid.</p>}
            </div>
        )}

      </main>
    </div>
  );
}

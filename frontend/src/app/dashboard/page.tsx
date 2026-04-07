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
  
  // Modals / Form State
  const [activeTab, setActiveTab] = useState<'overview' | 'farms' | 'requests'>('overview');
  const [farmForm, setFarmForm] = useState({ name: '', size_acres: '', crop_type: '', crop_stage: 'Vegetative', location_lat: '28.61', location_lng: '77.20' });
  const [reqForm, setReqForm] = useState({ farm_id: '', type: 'machine', required_by_date: '' });

  useEffect(() => {
    if (!token) {
      router.push('/auth/login');
    } else {
      loadDashboardData();
    }
  }, [token]);

  const loadDashboardData = async () => {
    try {
      const [profileRes, farmsRes, reqRes] = await Promise.all([
        api.get('/auth/me'),
        api.get('/farms/'),
        api.get('/requests/me')
      ]);
      setProfileData(profileRes.data);
      setFarms(farmsRes.data);
      setRequests(reqRes.data);
      if (farmsRes.data.length > 0) setReqForm(prev => ({ ...prev, farm_id: farmsRes.data[0].id.toString() }));
    } catch {
      logout();
      router.push('/auth/login');
    }
  };

  const handleCreateFarm = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/farms/', {
        ...farmForm,
        size_acres: parseFloat(farmForm.size_acres),
        location_lat: parseFloat(farmForm.location_lat),
        location_lng: parseFloat(farmForm.location_lng)
      });
      alert("Farm Registered!");
      setFarmForm({ name: '', size_acres: '', crop_type: '', crop_stage: 'Vegetative', location_lat: '28.61', location_lng: '77.20' });
      loadDashboardData();
    } catch (err) { alert("Failed to register farm."); }
  };

  const handleCreateRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/requests/', {
        ...reqForm,
        farm_id: parseInt(reqForm.farm_id),
        required_by_date: new Date(reqForm.required_by_date).toISOString()
      });
      alert("Request Deployed to Priority Engine!");
      loadDashboardData();
    } catch (err) { alert("Failed to create request."); }
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
                Securely connected to AI Matching Engine
              </p>
            </div>
            {role === 'farmer' && (
              <div className="bg-neutral-900 border border-neutral-800 p-6 rounded-2xl shadow-xl">
                <h3 className="text-neutral-500 font-bold uppercase tracking-widest text-xs mb-4">Total Assets</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="block text-4xl font-extrabold text-cyan-400">{farms.length}</span>
                    <span className="text-xs text-neutral-500 uppercase">Registered Farms</span>
                  </div>
                  <div>
                    <span className="block text-4xl font-extrabold text-indigo-400">{requests.length}</span>
                    <span className="text-xs text-neutral-500 uppercase">Active Requests</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'farms' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div className="bg-neutral-900 border border-neutral-800 rounded-3xl p-8">
              <h3 className="text-xl font-bold mb-6 text-cyan-400">Register New Farm</h3>
              <form onSubmit={handleCreateFarm} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <input required placeholder="Farm Name (e.g. North Field)" className="col-span-2 bg-black border border-neutral-800 p-3 rounded-xl text-sm" value={farmForm.name} onChange={e => setFarmForm({...farmForm, name: e.target.value})} />
                  <input required type="number" step="0.1" placeholder="Size (Acres)" className="bg-black border border-neutral-800 p-3 rounded-xl text-sm" value={farmForm.size_acres} onChange={e => setFarmForm({...farmForm, size_acres: e.target.value})} />
                  <input required placeholder="Crop Type (e.g. Wheat)" className="bg-black border border-neutral-800 p-3 rounded-xl text-sm" value={farmForm.crop_type} onChange={e => setFarmForm({...farmForm, crop_type: e.target.value})} />
                  
                  <select className="col-span-2 bg-black border border-neutral-800 p-3 rounded-xl text-sm text-neutral-300" value={farmForm.crop_stage} onChange={e => setFarmForm({...farmForm, crop_stage: e.target.value})}>
                    <option value="Vegetative">Vegetative (Low Priority)</option>
                    <option value="Flowering">Flowering</option>
                    <option value="Harvest-Ready">Harvest-Ready (Critical Priority)</option>
                  </select>
                </div>
                <button type="submit" className="w-full bg-cyan-600/20 text-cyan-400 hover:bg-cyan-500 hover:text-black font-bold py-3 rounded-xl transition-all outline-none">Register Terrain</button>
              </form>
            </div>

            <div className="space-y-4">
              <h3 className="text-xl font-bold mb-6 text-white">Registered Sector Database</h3>
              {farms.length === 0 ? <p className="text-neutral-500 text-sm">No farms registered yet.</p> : farms.map(farm => (
                <div key={farm.id} className="bg-black/50 border border-neutral-800 p-5 rounded-2xl flex justify-between items-center group">
                  <div>
                    <h4 className="font-bold text-lg text-emerald-100">{farm.name}</h4>
                    <p className="text-xs text-neutral-500">{farm.size_acres} Acres • {farm.crop_type}</p>
                  </div>
                  <span className="px-3 py-1 bg-neutral-900 border border-neutral-700 text-xs rounded-full text-cyan-400">{farm.crop_stage}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'requests' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div className="bg-neutral-900 border border-neutral-800 rounded-3xl p-8">
              <h3 className="text-xl font-bold mb-6 text-indigo-400">Deploy Resource Request</h3>
              <form onSubmit={handleCreateRequest} className="space-y-4">
                <select required className="w-full bg-black border border-neutral-800 p-3 rounded-xl text-sm text-neutral-300" value={reqForm.farm_id} onChange={e => setReqForm({...reqForm, farm_id: e.target.value})}>
                  <option value="" disabled>Select Target Farm...</option>
                  {farms.map(f => <option key={f.id} value={f.id}>{f.name}</option>)}
                </select>
                
                <select required className="w-full bg-black border border-neutral-800 p-3 rounded-xl text-sm text-neutral-300" value={reqForm.type} onChange={e => setReqForm({...reqForm, type: e.target.value})}>
                  <option value="machine">Heavy Machinery</option>
                  <option value="labour">Labour Syndicate</option>
                  <option value="irrigation">Water Routing</option>
                </select>

                <input required type="date" className="w-full bg-black border border-neutral-800 p-3 rounded-xl text-sm text-neutral-400" value={reqForm.required_by_date} onChange={e => setReqForm({...reqForm, required_by_date: e.target.value})} />
                
                <button type="submit" disabled={!reqForm.farm_id} className="w-full bg-indigo-600/20 text-indigo-400 hover:bg-indigo-500 hover:text-white font-bold py-3 rounded-xl transition-all disabled:opacity-50">Signal Priority Engine</button>
              </form>
            </div>

            <div className="space-y-4">
              <h3 className="text-xl font-bold mb-6 text-white">Active Queue</h3>
              {requests.length === 0 ? <p className="text-neutral-500 text-sm">No active requests floating.</p> : requests.map(req => (
                <div key={req.id} className="bg-black/50 border border-neutral-800 p-5 rounded-2xl">
                  <div className="flex justify-between items-start mb-2">
                    <h4 className="font-bold uppercase tracking-wider text-sm text-indigo-300">{req.type} Requirement</h4>
                    <span className={`px-2 py-1 text-[10px] font-bold uppercase rounded-md ${req.status === 'pending' ? 'bg-orange-500/20 text-orange-400' : 'bg-emerald-500/20 text-emerald-400'}`}>{req.status}</span>
                  </div>
                  <div className="flex justify-between items-end">
                    <p className="text-xs text-neutral-500">Needed by: <span className="font-mono text-neutral-300">{req.required_by_date ? req.required_by_date.split('T')[0] : 'TBD'}</span></p>
                    <div className="text-right">
                      <span className="block text-2xl font-black text-white">{req.priority_score.toFixed(1)}</span>
                      <span className="text-[10px] text-neutral-500 uppercase tracking-widest">{req.priority_reason || 'Base Score'}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

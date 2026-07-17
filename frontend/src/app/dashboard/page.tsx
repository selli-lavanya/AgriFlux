"use client";

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import api from '@/lib/api';
import dynamic from 'next/dynamic';
import { fetchAddressFromCoordinates } from '@/lib/geocoder';

const LeafletMap = dynamic(() => import('@/components/MapOverlay'), { ssr: false });
const LocationPickerMap = dynamic(() => import('@/components/LocationPickerMap'), { ssr: false });
import CopilotWidget from '@/components/CopilotWidget';
import NotificationToaster from '@/components/NotificationToaster';
import { useNotificationStore } from '@/store/notificationStore';

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
  const [analytics, setAnalytics] = useState<any>(null);
  
  const [newFarm, setNewFarm] = useState({ 
    name: '', size_acres: '', location_lat: 28.6139, location_lng: 77.2090, 
    location_label: '', full_address: '', crop_type: '', crop_stage: 'Sowing' 
  });
  const [isResolvingAddress, setIsResolvingAddress] = useState(false);
  
  const [activeTab, setActiveTab] = useState<'overview' | 'farms' | 'requests' | 'machines' | 'labour' | 'dispatcher' | 'tasks' | 'calendar'>('overview');
  const [reqForm, setReqForm] = useState({
    farm_id: '', type: 'machine',
    job_date: '',        // YYYY-MM-DD — becomes required_by_date
    start_time: '',      // HH:MM
    end_time: '',        // HH:MM
    duration: '',        // auto-calculated minutes
    max_budget_per_hour: '',
    max_total_budget: '',
    // machine-only
    work_size: '',
    quantity: '1',
    // labour-only
    workers_required: '',
    partial_allowed: false,
  });
  const [machineForm, setMachineForm] = useState({ type: 'Harvester', capacity_per_day: '', location_lat: 28.6139, location_lng: 77.2090, cost_per_hour: '150' });
  const [labourForm, setLabourForm] = useState({ worker_count: '', skills: 'Manual Harvesting', location_lat: 28.6139, location_lng: 77.2090, cost_per_worker_per_hour: '50' });

  const { notifications, addNotification } = useNotificationStore();

  useEffect(() => {
    if (!token) {
      router.push('/auth/login');
    } else {
      loadDashboardData();
    }
  }, [token]);

  // Phase 18: Real-time Dispatcher & Dashboard Sync
  useEffect(() => {
    if (notifications.length > 0) {
      const latest = notifications[0];
      const relevantEvents = ['NEW_REQUEST', 'ASSIGNMENT_CREATED', 'ASSIGNMENT_COMPLETED', 'FARM_CREATED', 'FARM_DELETED'];
      if (relevantEvents.includes(latest.event_type)) {
        loadDashboardData();
      }
    }
  }, [notifications.length]);

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
        const [pendRes, allMachRes, allLabRes, allFarmsRes] = await Promise.all([
          api.get('/requests/pending'),
          api.get('/machines/all'),
          api.get('/labour/all'),
          api.get('/farms/all')
        ]);
        setRequests(pendRes.data);
        setMachines(allMachRes.data);
        setLabourTeams(allLabRes.data);
        setFarms(allFarmsRes.data);
        const analyticsRes = await api.get('/analytics/overview');
        setAnalytics(analyticsRes.data.data);
      }
    } catch {
      logout();
      router.push('/auth/login');
    }
  };

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
      addNotification({
        id: `farm-success-${Date.now()}`,
        event_type: 'FARM_SUCCESS',
        entity_type: 'farm',
        entity_id: 0,
        message: "Farm Registered With Verifiable Location Intelligence!",
        timestamp: new Date().toISOString(),
        read: false
      });
    } catch {
      addNotification({
        id: `farm-err-${Date.now()}`,
        event_type: 'FARM_ERROR',
        entity_type: 'farm',
        entity_id: 0,
        message: "Registration failed. Internal database uplink error.",
        timestamp: new Date().toISOString(),
        read: false
      });
    }
  };

  const executeBrowserGPS = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition((pos) => {
        handleMapCoordinateChange(pos.coords.latitude, pos.coords.longitude);
      }, () => alert("GPS Permission Denied. Drag the pin manually."));
    }
  };

  const executeMachineGPS = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition((pos) => {
        setMachineForm(prev => ({ ...prev, location_lat: pos.coords.latitude, location_lng: pos.coords.longitude }));
      }, () => alert("GPS Permission Denied. Drag the pin manually."));
    }
  };

  const executeLabourGPS = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition((pos) => {
        setLabourForm(prev => ({ ...prev, location_lat: pos.coords.latitude, location_lng: pos.coords.longitude }));
      }, () => alert("GPS Permission Denied. Drag the pin manually."));
    }
  };

  const handleMapCoordinateChange = async (lat: number, lng: number) => {
    setNewFarm(prev => ({ ...prev, location_lat: lat, location_lng: lng }));
  };

  const handleDeleteFarm = async (farmId: number) => {
    try {
      await api.delete(`/farms/${farmId}?confirm=true`);
      addNotification({
        id: `farm-purge-${Date.now()}`,
        event_type: 'FARM_SUCCESS',
        entity_type: 'farm',
        entity_id: 0,
        message: "Territory and associated logistics purged from Matrix.",
        timestamp: new Date().toISOString(),
        read: false
      });
      loadDashboardData();
    } catch (err: any) {
      const msg = err.response?.data?.message || "Purge Restricted: Operational links active.";
      addNotification({
        id: `farm-err-${Date.now()}`,
        event_type: 'FARM_ERROR',
        entity_type: 'farm',
        entity_id: 0,
        message: msg,
        timestamp: new Date().toISOString(),
        read: false
      });
    }
  };

  const resolveSemanticAddress = async () => {
    setIsResolvingAddress(true);
    const data = await fetchAddressFromCoordinates(newFarm.location_lat, newFarm.location_lng);
    setIsResolvingAddress(false);
    if (data) {
       setNewFarm(prev => ({ ...prev, full_address: data.address, location_label: prev.location_label || data.label }));
    } else {
       addNotification({
        id: `geo-err-${Date.now()}`,
        event_type: 'GEO_ERROR',
        entity_type: 'geo',
        entity_id: 0,
        message: "Target resides in an unmapped sector entirely.",
        timestamp: new Date().toISOString(),
        read: false
      });
    }
  };

  const handleCreateRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const d = reqForm.job_date; // YYYY-MM-DD
      const toISO = (t: string) => t ? new Date(`${d}T${t}:00`).toISOString() : undefined;
      const startISO = toISO(reqForm.start_time);
      const endISO   = toISO(reqForm.end_time);

      // Auto-calculate duration from start/end if not manually entered
      // Use Math.floor to avoid 1-minute drift from floating point
      let duration: number | undefined = reqForm.duration ? parseInt(reqForm.duration) : undefined;
      if (!duration && startISO && endISO) {
        duration = Math.max(Math.floor((new Date(endISO).getTime() - new Date(startISO).getTime()) / 60000), 1);
      }

      const payload: any = {
        farm_id:          parseInt(reqForm.farm_id),
        type:             reqForm.type,
        required_by_date: startISO ?? new Date(`${d}T00:00:00`).toISOString(),
        start_time:       startISO,
        end_time:         endISO,
        duration,
        max_budget_per_hour: reqForm.max_budget_per_hour ? parseFloat(reqForm.max_budget_per_hour) : undefined,
        max_total_budget:    reqForm.max_total_budget    ? parseFloat(reqForm.max_total_budget)    : undefined,
      };

      if (reqForm.type === 'machine') {
        payload.work_size = reqForm.work_size ? parseFloat(reqForm.work_size) : undefined;
        payload.quantity  = reqForm.quantity  ? parseInt(reqForm.quantity)    : 1;
      } else {
        payload.workers_required = reqForm.workers_required ? parseInt(reqForm.workers_required) : undefined;
        payload.partial_allowed  = reqForm.partial_allowed;
      }

      await api.post('/requests/', payload);
      addNotification({
        id: `req-success-${Date.now()}`,
        event_type: 'REQUEST_SUCCESS',
        entity_type: 'req',
        entity_id: 0,
        message: "Request deployed to Priority Engine!",
        timestamp: new Date().toISOString(),
        read: false
      });
      // Reset form (keep farm and type)
      setReqForm(prev => ({ ...prev, job_date: '', start_time: '', end_time: '', duration: '',
        max_budget_per_hour: '', max_total_budget: '', work_size: '', quantity: '1',
        workers_required: '', partial_allowed: false }));
      loadDashboardData();
    } catch (err: any) {
      const msg = err.response?.data?.message || err.response?.data?.detail || "Failed to create request.";
      addNotification({
        id: `req-err-${Date.now()}`,
        event_type: 'REQUEST_ERROR',
        entity_type: 'req',
        entity_id: 0,
        message: msg,
        timestamp: new Date().toISOString(),
        read: false
      });
    }
  };

  const handleCreateMachine = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/machines/', {
        type: machineForm.type,
        capacity_per_day: parseFloat(machineForm.capacity_per_day),
        lat: machineForm.location_lat,
        lng: machineForm.location_lng,
        cost_per_hour: machineForm.cost_per_hour ? parseFloat(machineForm.cost_per_hour) : 150.0,
      });
      addNotification({
        id: `mach-success-${Date.now()}`,
        event_type: 'ASSET_SUCCESS',
        entity_type: 'machine',
        entity_id: 0,
        message: "Machinery Asset Registered!",
        timestamp: new Date().toISOString(),
        read: false
      });
      setMachineForm({ type: 'Harvester', capacity_per_day: '', location_lat: 28.6139, location_lng: 77.2090, cost_per_hour: '150' });
      loadDashboardData();
    } catch (err) {
      addNotification({
        id: `mach-err-${Date.now()}`,
        event_type: 'ASSET_ERROR',
        entity_type: 'machine',
        entity_id: 0,
        message: "Failed to register asset.",
        timestamp: new Date().toISOString(),
        read: false
      });
    }
  };

  const handleCreateLabour = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/labour/', {
        worker_count: parseInt(labourForm.worker_count),
        skills: labourForm.skills,
        lat: labourForm.location_lat,
        lng: labourForm.location_lng,
        cost_per_worker_per_hour: labourForm.cost_per_worker_per_hour ? parseFloat(labourForm.cost_per_worker_per_hour) : 50.0,
      });
      addNotification({
        id: `lab-success-${Date.now()}`,
        event_type: 'ROSTER_SUCCESS',
        entity_type: 'labour',
        entity_id: 0,
        message: "Labour Syndicate Placed on Roster!",
        timestamp: new Date().toISOString(),
        read: false
      });
      loadDashboardData();
    } catch (err) {
      addNotification({
        id: `lab-err-${Date.now()}`,
        event_type: 'ROSTER_ERROR',
        entity_type: 'labour',
        entity_id: 0,
        message: "Failed to register roster.",
        timestamp: new Date().toISOString(),
        read: false
      });
    }
  };

  const handleCompleteTask = async (id: number) => {
    try {
      await api.put(`/assignments/${id}/complete`);
      addNotification({
        id: `task-success-${Date.now()}`,
        event_type: 'TASK_COMPLETE',
        entity_type: 'req',
        entity_id: id,
        message: "Task documented as COMPLETE. Supply Chain Notified.",
        timestamp: new Date().toISOString(),
        read: false
      });
      loadDashboardData();
    } catch (err) {
       addNotification({
        id: `task-err-${Date.now()}`,
        event_type: 'TASK_ERROR',
        entity_type: 'req',
        entity_id: id,
        message: "Failed to finalize completion report.",
        timestamp: new Date().toISOString(),
        read: false
      });
    }
  };

  const executeEngineTrigger = async () => {
    try {
      const res = await api.post('/requests/trigger-engine');
      addNotification({
        id: `engine-success-${Date.now()}`,
        event_type: 'ENGINE_SYNC',
        entity_type: 'system',
        entity_id: 0,
        message: `Prioritization Complete: ${res.data.processed_count} requests evaluated!`,
        timestamp: new Date().toISOString(),
        read: false
      });
      loadDashboardData();
    } catch {
       addNotification({
        id: `engine-err-${Date.now()}`,
        event_type: 'ENGINE_ERROR',
        entity_type: 'system',
        entity_id: 0,
        message: "Engine computation failed. Core downlink interrupted.",
        timestamp: new Date().toISOString(),
        read: false
      });
    }
  };

  const executeAssignment = async (request: any, resourceId: number, type: string) => {
    try {
      await api.post('/assignments/', {
        request_id: request.id,
        resource_id: resourceId,
        resource_type: type,
        scheduled_date: request.required_by_date
      });
      
      addNotification({
        id: `success-${Date.now()}`,
        event_type: 'ASSIGNMENT_SUCCESS',
        entity_type: 'req',
        entity_id: request.id,
        message: "Match Successfully Authenticated & Sent!",
        timestamp: new Date().toISOString(),
        read: false
      });
      loadDashboardData();
    } catch (err: any) { 
      const msg = err.response?.data?.message || err.response?.data?.detail || "Failed to secure mapping contract!";
      const details = err.response?.data?.details ? ` (${err.response.data.details})` : "";
      
      // Use premium Toaster instead of browser alert
      addNotification({
        id: `err-${Date.now()}`,
        event_type: 'ASSIGNMENT_ERROR',
        entity_type: 'req',
        entity_id: request.id,
        message: `${msg}${details}`,
        timestamp: new Date().toISOString(),
        read: false
      });
    }
  };

  const handleRequestCreation = async (formData: any) => {
    try {
      await api.post('/requests/', formData);
      addNotification({
        id: `success-${Date.now()}`,
        event_type: 'NEW_REQUEST_CREATED',
        entity_type: 'req',
        entity_id: 0,
        message: "Network demand broadcast successfully. Scanning for available hardware...",
        timestamp: new Date().toISOString(),
        read: false
      });
      loadDashboardData();
    } catch (err: any) {
       addNotification({
        id: `err-${Date.now()}`,
        event_type: 'REQUEST_FAILURE',
        entity_type: 'req',
        entity_id: 0,
        message: "Failed to broadcast demand. Internal uplink error.",
        timestamp: new Date().toISOString(),
        read: false
      });
    }
  };

  if (!profileData) return <div className="min-h-screen bg-neutral-950 flex items-center justify-center text-emerald-500 animate-pulse font-mono">Syncing Cortex...</div>;

  return (
    <div className="min-h-screen bg-neutral-950 text-white flex">
      <aside className="w-72 bg-neutral-900/50 backdrop-blur-xl border-r border-neutral-800/50 flex flex-col p-6 space-y-2">
        <div className="flex items-center gap-3 mb-10 px-2">
          <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/20">
             <span className="text-xl font-black">A</span>
          </div>
          <h2 className="text-2xl font-black tracking-tighter bg-clip-text text-transparent bg-gradient-to-br from-white to-neutral-500">AgriFlux</h2>
        </div>
        
        <button onClick={() => setActiveTab('overview')} className={`text-left px-4 py-3 rounded-xl font-bold transition-all duration-300 flex items-center gap-3 ${activeTab === 'overview' ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20' : 'text-neutral-500 hover:bg-neutral-800/50 hover:text-neutral-300'}`}>
          <span className="text-lg opacity-80">📊</span> Overview
        </button>
        <button onClick={() => setActiveTab('calendar')} className={`text-left px-4 py-3 rounded-xl font-bold transition-all duration-300 flex items-center gap-3 ${activeTab === 'calendar' ? 'bg-fuchsia-600 text-white shadow-lg shadow-fuchsia-600/20' : 'text-neutral-500 hover:bg-neutral-800/50 hover:text-neutral-300'}`}>
          <span className="text-lg opacity-80">🗓️</span> Network Matrix
        </button>
        
        <div className="my-4 border-t border-neutral-800/50 pt-4 pb-2">
           <p className="px-4 text-[10px] font-black uppercase tracking-widest text-neutral-600">Operational Nodes</p>
        </div>

        {role === 'farmer' && (
          <>
            <button onClick={() => setActiveTab('farms')} className={`text-left px-4 py-3 rounded-xl font-bold transition-all duration-300 flex items-center gap-3 ${activeTab === 'farms' ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-600/20' : 'text-neutral-500 hover:bg-neutral-800/50 hover:text-neutral-300'}`}>
              <span className="text-lg opacity-80">🌾</span> My Territories
            </button>
            <button onClick={() => setActiveTab('requests')} className={`text-left px-4 py-3 rounded-xl font-bold transition-all duration-300 flex items-center gap-3 ${activeTab === 'requests' ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20' : 'text-neutral-500 hover:bg-neutral-800/50 hover:text-neutral-300'}`}>
              <span className="text-lg opacity-80">🛰️</span> Logistics
            </button>
          </>
        )}
        {role === 'admin' && (
          <button onClick={() => setActiveTab('dispatcher')} className={`text-left px-4 py-3 rounded-xl font-bold transition-all duration-300 flex items-center gap-3 ${activeTab === 'dispatcher' ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/20' : 'text-neutral-500 hover:bg-neutral-800/50 hover:text-neutral-300'}`}>
            <span className="text-lg opacity-80">⚡</span> Dispatcher
          </button>
        )}
        {(role === 'machine_owner' || role === 'admin') && <button onClick={() => setActiveTab('machines')} className={`text-left px-4 py-3 rounded-xl font-bold transition-all duration-300 flex items-center gap-3 ${activeTab === 'machines' ? 'bg-amber-600 text-white shadow-lg shadow-amber-600/20' : 'text-neutral-500 hover:bg-neutral-800/50 hover:text-neutral-300'}`}>
          <span className="text-lg opacity-80">🚜</span> Hardware
        </button>}
        {(role === 'labour_team' || role === 'admin') && <button onClick={() => setActiveTab('labour')} className={`text-left px-4 py-3 rounded-xl font-bold transition-all duration-300 flex items-center gap-3 ${activeTab === 'labour' ? 'bg-rose-600 text-white shadow-lg shadow-rose-600/20' : 'text-neutral-500 hover:bg-neutral-800/50 hover:text-neutral-300'}`}>
          <span className="text-lg opacity-80">👷</span> Workforce
        </button>}
        {(role === 'machine_owner' || role === 'labour_team') && (
          <button onClick={() => setActiveTab('tasks')} className={`text-left px-4 py-3 rounded-xl font-bold transition-all duration-300 flex items-center gap-3 ${activeTab === 'tasks' ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20' : 'text-neutral-500 hover:bg-neutral-800/50 hover:text-neutral-300'}`}>
            <span className="text-lg opacity-80">📋</span> Assignments
          </button>
        )}
        
        <div className="flex-grow" />
        <div className="px-4 py-2 mb-4 bg-emerald-500/5 rounded-lg border border-emerald-500/10 flex items-center gap-3">
           <span className="relative flex h-2 w-2"><span className="animate-ping absolute h-full w-full rounded-full bg-emerald-400 opacity-75"></span><span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span></span>
           <span className="text-[10px] font-black uppercase tracking-widest text-emerald-500/70">System Live</span>
        </div>
        
        <button onClick={() => { logout(); router.push('/auth/login'); }} className="group text-left px-4 py-3 text-neutral-600 hover:text-rose-500 hover:bg-rose-950/20 rounded-xl font-bold transition-all mt-auto flex items-center gap-3">
          <span className="text-lg opacity-50 group-hover:opacity-100">🔒</span> Terminate Session
        </button>
      </aside>

      <main className="flex-1 p-10 overflow-y-auto">
        <header className="mb-10 pb-6 border-b border-neutral-900">
          <h1 className="text-3xl font-extrabold tracking-tight capitalize">{activeTab} Interface</h1>
          <p className="text-neutral-500 mt-2 text-sm font-mono">Operator ID: {profileData.email} | Clearance: <span className="text-emerald-400 uppercase">{role}</span></p>
        </header>

        {activeTab === 'overview' && (
          <div className="space-y-8">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="bg-neutral-900 border border-neutral-800 p-6 rounded-2xl shadow-xl hover:border-indigo-500/30 transition-all group">
                <h3 className="text-neutral-500 font-bold uppercase tracking-widest text-[10px] mb-4">Command Center Status</h3>
                <p className="text-emerald-400 flex items-center gap-3 text-sm font-bold">
                  <span className="relative flex h-3 w-3"><span className="animate-ping absolute h-full w-full rounded-full bg-emerald-400 opacity-75"></span><span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span></span>
                  Uplink Stabilized
                </p>
                <p className="text-[10px] text-neutral-600 mt-2 font-mono uppercase">Encryption: AES-256 Verified</p>
              </div>
              {analytics && (
                <>
                  <div className="bg-neutral-900 border border-neutral-800 p-6 rounded-2xl shadow-xl">
                    <h3 className="text-neutral-500 font-bold uppercase tracking-widest text-[10px] mb-4">Active Requests</h3>
                    <p className="text-2xl font-black text-white">{analytics.requests.pending + analytics.requests.assigned}</p>
                    <p className="text-[10px] text-neutral-500 mt-1 uppercase font-bold tracking-tighter">{analytics.requests.completed} Fulfilled via Fleet</p>
                  </div>
                  <div className="bg-neutral-900 border border-neutral-800 p-6 rounded-2xl shadow-xl">
                    <h3 className="text-neutral-500 font-bold uppercase tracking-widest text-[10px] mb-4">Machine Load</h3>
                    <p className="text-2xl font-black text-amber-500">{analytics.utilization.machine_pct}%</p>
                    <div className="w-full bg-neutral-800 h-1 mt-2 rounded-full overflow-hidden">
                       <div className="bg-amber-500 h-full" style={{ width: `${analytics.utilization.machine_pct}%` }} />
                    </div>
                  </div>
                  <div className="bg-neutral-900 border border-neutral-800 p-6 rounded-2xl shadow-xl">
                    <h3 className="text-neutral-500 font-bold uppercase tracking-widest text-[10px] mb-4">Labour Load</h3>
                    <p className="text-2xl font-black text-rose-500">{analytics.utilization.labour_pct}%</p>
                    <div className="w-full bg-neutral-800 h-1 mt-2 rounded-full overflow-hidden">
                       <div className="bg-rose-500 h-full" style={{ width: `${analytics.utilization.labour_pct}%` }} />
                    </div>
                  </div>
                </>
              )}
            </div>
            {role === 'admin' && (
              <div className="bg-neutral-900 border border-emerald-900/50 p-8 rounded-3xl shadow-[0_0_30px_rgba(52,211,153,0.05)] flex flex-col md:flex-row justify-between items-center gap-6">
                 <div className="flex-1">
                    <h3 className="text-emerald-500 font-black uppercase tracking-widest text-xs mb-2">Automated Supply Chain Orchestrator</h3>
                    <p className="text-neutral-400 text-sm leading-relaxed max-w-xl">Re-evaluate all pending demand signals and optimize resource distribution based on latest priority scores.</p>
                 </div>
                 <button onClick={executeEngineTrigger} className="bg-emerald-500 text-black px-8 py-4 font-black rounded-2xl hover:bg-emerald-400 transition-all shadow-xl shadow-emerald-500/20 active:scale-95">RE-SYNC PRIORITY ENGINE</button>
              </div>
            )}
          </div>
        )}

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
                      <p className="text-lg font-bold text-amber-400">{day.machines.available} Available / {day.machines.booked} Booked</p>
                      <p className="text-[10px] text-neutral-600 mt-1 uppercase font-bold">Fleet Size: {day.machines.total} Units</p>
                    </div>
                    <div className="bg-black/50 p-3 rounded-xl border border-neutral-800">
                      <p className="text-xs text-neutral-500 font-bold uppercase mb-1">Labour Network Matrix</p>
                      <p className="text-lg font-bold text-rose-400">{day.labour.available} Available / {day.labour.booked} Booked</p>
                      <p className="text-[10px] text-neutral-600 mt-1 uppercase font-bold">Total Roster: {day.labour.total} Teams</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
        {activeTab === 'farms' && (
            <div className="space-y-8">
              <div className="bg-neutral-900 border border-neutral-800 rounded-3xl p-8">
                <h3 className="text-xl font-bold mb-6 text-emerald-400">Register New Farm Operation</h3>
                <form onSubmit={handleCreateFarm} className="space-y-6">
                  {/* ... form content ... */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <input type="text" placeholder="Farm Name" className="w-full bg-black/50 border border-neutral-700/50 p-3 rounded-xl focus:border-emerald-500 focus:outline-none" value={newFarm.name} onChange={e => setNewFarm({...newFarm, name: e.target.value})} required />
                    <input type="number" placeholder="Size (Acres)" className="w-full bg-black/50 border border-neutral-700/50 p-3 rounded-xl focus:border-emerald-500 focus:outline-none" value={newFarm.size_acres} onChange={e => setNewFarm({...newFarm, size_acres: e.target.value})} required />
                    <input type="text" placeholder="Crop Type" className="w-full bg-black/50 border border-neutral-700/50 p-3 rounded-xl focus:border-emerald-500 focus:outline-none" value={newFarm.crop_type} onChange={e => setNewFarm({...newFarm, crop_type: e.target.value})} required />
                    <select className="w-full bg-black/50 border border-neutral-700/50 p-3 rounded-xl focus:border-emerald-500 focus:outline-none text-neutral-300" value={newFarm.crop_stage} onChange={e => setNewFarm({...newFarm, crop_stage: e.target.value})}>
                      <option value="Sowing">Sowing Phase</option>
                      <option value="Vegetative">Vegetative Phase</option>
                      <option value="Harvesting">Harvesting Phase</option>
                    </select>
                  </div>
                  <div className="mt-8 border border-neutral-800 rounded-2xl overflow-hidden bg-black/50">
                    <div className="flex flex-col md:flex-row justify-between items-center p-4 border-b border-neutral-800 bg-neutral-900/50">
                        <h4 className="text-sm font-bold text-gray-300">Geospatial Target</h4>
                        <button type="button" onClick={executeBrowserGPS} className="mt-2 md:mt-0 text-xs font-bold bg-blue-600/20 text-blue-400 hover:bg-blue-600/40 px-3 py-1.5 rounded transition">📡 Ping Mobile GPS</button>
                    </div>
                    <div className="grid grid-cols-1 lg:grid-cols-2">
                        <div className="h-[250px] w-full bg-neutral-800">
                            <LocationPickerMap lat={newFarm.location_lat} lng={newFarm.location_lng} onChange={handleMapCoordinateChange} />
                        </div>
                        <div className="p-6 space-y-4 flex flex-col justify-center">
                            <button type="button" onClick={resolveSemanticAddress} disabled={isResolvingAddress} className="w-full bg-emerald-600/20 text-emerald-400 border border-emerald-900/50 hover:bg-emerald-600/40 font-bold text-sm py-2 rounded-lg transition disabled:opacity-50">
                              {isResolvingAddress ? "Resolving..." : "Extract Semantic Address"}
                            </button>
                            <div><label className="text-[10px] font-bold text-gray-500 uppercase">Sector Label</label><input type="text" className="w-full mt-1 bg-black/80 border border-neutral-800 p-2 rounded focus:border-emerald-500 focus:outline-none text-sm" value={newFarm.location_label} onChange={e => setNewFarm({...newFarm, location_label: e.target.value})} /></div>
                            <div><label className="text-[10px] font-bold text-gray-500 uppercase">Verifiable Address</label><textarea rows={2} className="w-full mt-1 bg-black/80 border border-neutral-800 p-2 rounded focus:border-emerald-500 focus:outline-none text-xs text-gray-400" value={newFarm.full_address} onChange={e => setNewFarm({...newFarm, full_address: e.target.value})} /></div>
                        </div>
                    </div>
                  </div>
                  <button type="submit" className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-3 mt-4 rounded-xl transition-all">Commit Farm to Matrix</button>
                </form>
              </div>

              <div className="space-y-4">
                 <h3 className="text-xl font-bold text-neutral-400 px-2">Managed Territories</h3>
                 {farms.length === 0 ? (
                   <p className="text-neutral-600 italic px-2">No active farm nodes registered.</p>
                 ) : (
                   <div className="grid grid-cols-1 gap-4">
                     {farms.map(f => (
                       <div key={f.id} className="bg-neutral-900 border border-neutral-800 p-6 rounded-2xl flex justify-between items-center group hover:border-emerald-500/30 transition-all">
                          <div>
                            <h4 className="text-white font-bold text-lg">{f.name}</h4>
                            <p className="text-xs text-neutral-500 font-mono mt-1 uppercase tracking-widest">{f.crop_type} • {f.size_acres} Acres</p>
                            <p className="text-[10px] text-emerald-500/50 mt-2 font-bold">{f.full_address || "Address mapping pending"}</p>
                          </div>
                          <button 
                            onClick={() => { if(window.confirm("Delete this Farm? All associated unassigned requests will be deleted.")) handleDeleteFarm(f.id); }}
                            className="p-3 bg-rose-500/10 text-rose-500 rounded-xl hover:bg-rose-500 hover:text-white transition-all opacity-0 group-hover:opacity-100"
                          >
                            🗑️
                          </button>
                       </div>
                     ))}
                   </div>
                 )}
              </div>
            </div>
        )}

        {activeTab === 'requests' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Map */}
              <div className="lg:col-span-2 h-[420px] w-full rounded-2xl overflow-hidden relative border border-indigo-900/30">
                 <LeafletMap requests={requests} farms={farms} machines={machines} labourTeams={labourTeams} role={role || ''} />
              </div>

              {/* Request Form */}
              <div className="bg-neutral-900 border border-neutral-800 rounded-3xl p-8">
                <h3 className="text-xl font-bold mb-1 text-indigo-400">New Request</h3>
                <p className="text-[11px] text-neutral-600 font-mono uppercase tracking-widest mb-6">Fill all fields — engine uses them for matching</p>
                <form onSubmit={handleCreateRequest} className="space-y-5">

                  {/* Farm + Type */}
                  <div className="space-y-3">
                    <p className="text-[10px] font-black uppercase tracking-widest text-neutral-600">Target</p>
                    <select required className="w-full bg-black border border-neutral-800 p-3 rounded-xl text-sm text-neutral-300 focus:border-indigo-500 focus:outline-none" value={reqForm.farm_id} onChange={e => setReqForm({...reqForm, farm_id: e.target.value})}>
                      <option value="" disabled>Select Farm…</option>
                      {farms.map(f => <option key={f.id} value={f.id}>{f.name}</option>)}
                    </select>
                    <div className="grid grid-cols-2 gap-3">
                      <button type="button" onClick={() => setReqForm({...reqForm, type: 'machine'})} className={`py-2.5 rounded-xl text-sm font-bold border transition-all ${ reqForm.type === 'machine' ? 'bg-amber-600 border-amber-500 text-white' : 'bg-black border-neutral-800 text-neutral-500 hover:border-neutral-600' }`}>🚜 Machinery</button>
                      <button type="button" onClick={() => setReqForm({...reqForm, type: 'labour'})}  className={`py-2.5 rounded-xl text-sm font-bold border transition-all ${ reqForm.type === 'labour'  ? 'bg-rose-600  border-rose-500  text-white' : 'bg-black border-neutral-800 text-neutral-500 hover:border-neutral-600' }`}>👷 Labour</button>
                    </div>
                  </div>

                  {/* Scheduling */}
                  <div className="space-y-3 pt-1 border-t border-neutral-800">
                    <p className="text-[10px] font-black uppercase tracking-widest text-neutral-600 pt-2">Job Scheduling</p>
                    <div>
                      <label className="text-[10px] text-neutral-500 font-bold uppercase">Job Date</label>
                      <input required type="date" className="w-full mt-1 bg-black border border-neutral-800 p-3 rounded-xl text-sm text-neutral-300 focus:border-indigo-500 focus:outline-none" value={reqForm.job_date} onChange={e => setReqForm({...reqForm, job_date: e.target.value})} />
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="text-[10px] text-neutral-500 font-bold uppercase">Available From</label>
                        <input required type="time" className="w-full mt-1 bg-black border border-neutral-800 p-3 rounded-xl text-sm text-neutral-300 focus:border-indigo-500 focus:outline-none" value={reqForm.start_time} onChange={e => setReqForm({...reqForm, start_time: e.target.value})} />
                      </div>
                      <div>
                        <label className="text-[10px] text-neutral-500 font-bold uppercase">Available Until</label>
                        <input required type="time" className="w-full mt-1 bg-black border border-neutral-800 p-3 rounded-xl text-sm text-neutral-300 focus:border-indigo-500 focus:outline-none" value={reqForm.end_time} onChange={e => setReqForm({...reqForm, end_time: e.target.value})} />
                      </div>
                    </div>
                    <div>
                      <label className="text-[10px] text-neutral-500 font-bold uppercase">Job Duration (minutes)</label>
                      <input type="number" min="1" placeholder={reqForm.start_time && reqForm.end_time ? `Auto: ${Math.max(Math.round((new Date(`2000-01-01T${reqForm.end_time}`).getTime() - new Date(`2000-01-01T${reqForm.start_time}`).getTime())/60000),1)} min` : 'e.g. 120'} className="w-full mt-1 bg-black border border-neutral-800 p-3 rounded-xl text-sm text-neutral-300 placeholder:text-neutral-600 focus:border-indigo-500 focus:outline-none" value={reqForm.duration} onChange={e => setReqForm({...reqForm, duration: e.target.value})} />
                      <p className="text-[10px] text-neutral-700 mt-1">Leave blank to auto-calculate from time window</p>
                    </div>
                  </div>

                  {/* Budget */}
                  <div className="space-y-3 pt-1 border-t border-neutral-800">
                    <p className="text-[10px] font-black uppercase tracking-widest text-neutral-600 pt-2">Budget Limits</p>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="text-[10px] text-neutral-500 font-bold uppercase">Max ₹/Hour</label>
                        <input type="number" min="0" step="0.01" placeholder="e.g. 500" className="w-full mt-1 bg-black border border-neutral-800 p-3 rounded-xl text-sm text-neutral-300 placeholder:text-neutral-600 focus:border-indigo-500 focus:outline-none" value={reqForm.max_budget_per_hour} onChange={e => setReqForm({...reqForm, max_budget_per_hour: e.target.value})} />
                      </div>
                      <div>
                        <label className="text-[10px] text-neutral-500 font-bold uppercase">Max Total ₹</label>
                        <input type="number" min="0" step="0.01" placeholder="e.g. 5000" className="w-full mt-1 bg-black border border-neutral-800 p-3 rounded-xl text-sm text-neutral-300 placeholder:text-neutral-600 focus:border-indigo-500 focus:outline-none" value={reqForm.max_total_budget} onChange={e => setReqForm({...reqForm, max_total_budget: e.target.value})} />
                      </div>
                    </div>
                  </div>

                  {/* Conditional: Machine fields */}
                  {reqForm.type === 'machine' && (
                    <div className="space-y-3 pt-1 border-t border-neutral-800">
                      <p className="text-[10px] font-black uppercase tracking-widest text-amber-700 pt-2">Machinery Details</p>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="text-[10px] text-neutral-500 font-bold uppercase">Work Size (Acres)</label>
                          <input type="number" min="0" step="0.1" placeholder="e.g. 5.0" className="w-full mt-1 bg-black border border-neutral-800 p-3 rounded-xl text-sm text-neutral-300 placeholder:text-neutral-600 focus:border-amber-500 focus:outline-none" value={reqForm.work_size} onChange={e => setReqForm({...reqForm, work_size: e.target.value})} />
                        </div>
                        <div>
                          <label className="text-[10px] text-neutral-500 font-bold uppercase">No. of Machines</label>
                          <input type="number" min="1" placeholder="1" className="w-full mt-1 bg-black border border-neutral-800 p-3 rounded-xl text-sm text-neutral-300 placeholder:text-neutral-600 focus:border-amber-500 focus:outline-none" value={reqForm.quantity} onChange={e => setReqForm({...reqForm, quantity: e.target.value})} />
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Conditional: Labour fields */}
                  {reqForm.type === 'labour' && (
                    <div className="space-y-3 pt-1 border-t border-neutral-800">
                      <p className="text-[10px] font-black uppercase tracking-widest text-rose-700 pt-2">Labour Details</p>
                      <div>
                        <label className="text-[10px] text-neutral-500 font-bold uppercase">Workers Required</label>
                        <input type="number" min="1" placeholder="e.g. 5" className="w-full mt-1 bg-black border border-neutral-800 p-3 rounded-xl text-sm text-neutral-300 placeholder:text-neutral-600 focus:border-rose-500 focus:outline-none" value={reqForm.workers_required} onChange={e => setReqForm({...reqForm, workers_required: e.target.value})} />
                      </div>
                      <button type="button" onClick={() => setReqForm({...reqForm, partial_allowed: !reqForm.partial_allowed})} className={`w-full py-3 rounded-xl text-sm font-bold border transition-all ${ reqForm.partial_allowed ? 'bg-rose-600/20 border-rose-500 text-rose-300' : 'bg-black border-neutral-800 text-neutral-500' }`}>
                        {reqForm.partial_allowed ? '✅ Allow Partial Teams (Split Across Multiple)' : '⬜ Require Single Team Only'}
                      </button>
                    </div>
                  )}

                  <button type="submit" disabled={!reqForm.farm_id || !reqForm.job_date || !reqForm.start_time || !reqForm.end_time} className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white py-3.5 rounded-xl font-black transition-all shadow-lg shadow-indigo-600/20 active:scale-[.98]">🚀 Submit Request</button>
                </form>
              </div>

              {/* Request List */}
              <div className="space-y-3">
                <h3 className="text-lg font-bold text-neutral-400 mb-4">My Requests ({requests.length})</h3>
                {requests.length === 0 ? (
                  <p className="text-neutral-600 italic text-sm">No requests submitted yet.</p>
                ) : (
                  requests.map(req => {
                    const statusColors: Record<string, string> = {
                      PENDING:     'bg-yellow-900/30 text-yellow-400 border-yellow-700/30',
                      ASSIGNED:    'bg-emerald-900/30 text-emerald-400 border-emerald-700/30',
                      IN_PROGRESS: 'bg-blue-900/30 text-blue-400 border-blue-700/30',
                      COMPLETED:   'bg-neutral-800 text-neutral-400 border-neutral-700',
                      UNSERVICED:  'bg-rose-900/30 text-rose-400 border-rose-700/30',
                    };
                    const sc = statusColors[req.status] ?? 'bg-neutral-800 text-neutral-400 border-neutral-700';
                    return (
                      <div key={req.id} className="bg-black/50 border border-neutral-800 p-5 rounded-2xl hover:border-neutral-700 transition-all">
                        <div className="flex justify-between items-start mb-3">
                          <div>
                            <p className="font-bold text-white capitalize">{req.type === 'machine' ? '🚜' : '👷'} {req.type} Request</p>
                            <p className="text-[10px] text-neutral-600 mt-0.5 font-mono">ID #{req.id} • Score {req.priority_score?.toFixed(1)}</p>
                          </div>
                          <span className={`text-[10px] font-black px-2.5 py-1 rounded-full border uppercase ${sc}`}>{req.status}</span>
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-[11px] text-neutral-500">
                          {req.required_by_date && <p>📅 {new Date(req.required_by_date).toLocaleDateString('en-IN', {day:'numeric', month:'short', year:'numeric'})}</p>}
                          {req.duration         && <p>⏱ {Math.round(req.duration)} min</p>}
                          {req.max_total_budget  && <p>💰 Budget ₹{Number(req.max_total_budget).toLocaleString('en-IN', {minimumFractionDigits: 0, maximumFractionDigits: 2})}</p>}
                          {req.estimated_cost    && <p className="text-emerald-600">✅ Cost ₹{Number(req.estimated_cost).toLocaleString('en-IN', {minimumFractionDigits: 0, maximumFractionDigits: 2})}</p>}
                        </div>
                        {req.priority_reason && <p className="text-[10px] text-indigo-500/70 mt-2 italic border-t border-neutral-900 pt-2">{req.priority_reason}</p>}
                      </div>
                    );
                  })
                )}
              </div>
            </div>
        )}

        {activeTab === 'machines' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {role === 'machine_owner' && (
                <div className="bg-neutral-900 border border-neutral-800 rounded-3xl p-8">
                  <h3 className="text-xl font-bold mb-6 text-amber-400">Register Machinery</h3>
                  <form onSubmit={handleCreateMachine} className="space-y-4">
                    <select required className="w-full bg-black border border-neutral-800 p-3 rounded-xl text-sm text-neutral-300 focus:border-amber-500 focus:outline-none" value={machineForm.type} onChange={e => setMachineForm({...machineForm, type: e.target.value})}>
                      <option value="Harvester">Harvester</option>
                      <option value="Tractor">Tractor</option>
                    </select>
                    <input required type="number" step="0.1" placeholder="Capacity (Acres/Day)" className="w-full bg-black border border-neutral-800 p-3 rounded-xl text-sm focus:border-amber-500 focus:outline-none" value={machineForm.capacity_per_day} onChange={e => setMachineForm({...machineForm, capacity_per_day: e.target.value})} />
                    <div>
                      <label className="text-[10px] text-neutral-500 font-bold uppercase">Cost per Hour (₹)</label>
                      <input type="number" step="0.01" placeholder="150" className="w-full mt-1 bg-black border border-neutral-800 p-3 rounded-xl text-sm focus:border-amber-500 focus:outline-none" value={machineForm.cost_per_hour} onChange={e => setMachineForm({...machineForm, cost_per_hour: e.target.value})} />
                    </div>
                    {/* GPS Map Picker — same as farm form */}
                    <div className="border border-neutral-800 rounded-2xl overflow-hidden bg-black/50">
                      <div className="flex flex-col md:flex-row justify-between items-center p-3 border-b border-neutral-800 bg-neutral-900/50">
                        <h4 className="text-sm font-bold text-amber-300">📍 Machine Location</h4>
                        <button type="button" onClick={executeMachineGPS} className="mt-2 md:mt-0 text-xs font-bold bg-blue-600/20 text-blue-400 hover:bg-blue-600/40 px-3 py-1.5 rounded transition">📡 Use My GPS</button>
                      </div>
                      <div className="h-[220px] w-full bg-neutral-800">
                        <LocationPickerMap lat={machineForm.location_lat} lng={machineForm.location_lng} onChange={(lat, lng) => setMachineForm(prev => ({...prev, location_lat: lat, location_lng: lng}))} />
                      </div>
                      <div className="p-3 flex gap-3">
                        <div className="flex-1">
                          <label className="text-[10px] text-neutral-600 font-bold uppercase">Latitude</label>
                          <input type="number" step="any" className="w-full mt-1 bg-black border border-neutral-800 p-2 rounded-lg text-xs text-neutral-300 focus:border-amber-500 focus:outline-none" value={machineForm.location_lat.toFixed(5)} onChange={e => setMachineForm(prev => ({...prev, location_lat: parseFloat(e.target.value) || prev.location_lat}))} />
                        </div>
                        <div className="flex-1">
                          <label className="text-[10px] text-neutral-600 font-bold uppercase">Longitude</label>
                          <input type="number" step="any" className="w-full mt-1 bg-black border border-neutral-800 p-2 rounded-lg text-xs text-neutral-300 focus:border-amber-500 focus:outline-none" value={machineForm.location_lng.toFixed(5)} onChange={e => setMachineForm(prev => ({...prev, location_lng: parseFloat(e.target.value) || prev.location_lng}))} />
                        </div>
                      </div>
                    </div>
                    <button type="submit" className="w-full bg-amber-600 hover:bg-amber-500 text-white font-bold py-3 rounded-xl transition-all">Register Asset</button>
                  </form>
                </div>
              )}
              <div className={`space-y-4 ${role === 'admin' ? 'lg:col-span-2' : ''}`}>
                {machines.map(mach => (
                  <div key={mach.id} className="bg-black/50 border border-neutral-800 p-5 rounded-2xl flex justify-between items-center">
                    <div><h4 className="font-bold text-amber-100">{mach.type}</h4><p className="text-xs text-neutral-500">Capacity: {mach.capacity_per_day} Acres/day</p></div>
                    <span className="px-3 py-1 bg-amber-900/30 border border-amber-700/50 text-xs rounded-full text-amber-400">#ID-{mach.id}</span>
                  </div>
                ))}
              </div>
            </div>
        )}

        {activeTab === 'labour' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {role === 'labour_team' && (
                <div className="bg-neutral-900 border border-neutral-800 rounded-3xl p-8">
                  <h3 className="text-xl font-bold mb-6 text-rose-400">Register Syndicate</h3>
                  <form onSubmit={handleCreateLabour} className="space-y-4">
                    <input required type="number" placeholder="Worker Count" className="w-full bg-black border border-neutral-800 p-3 rounded-xl text-sm focus:border-rose-500 focus:outline-none" value={labourForm.worker_count} onChange={e => setLabourForm({...labourForm, worker_count: e.target.value})} />
                    <input required placeholder="Primary Skills (e.g. Manual Harvesting)" className="w-full bg-black border border-neutral-800 p-3 rounded-xl text-sm focus:border-rose-500 focus:outline-none" value={labourForm.skills} onChange={e => setLabourForm({...labourForm, skills: e.target.value})} />
                    <div>
                      <label className="text-[10px] text-neutral-500 font-bold uppercase">Cost per Worker per Hour (₹)</label>
                      <input type="number" step="0.01" placeholder="50" className="w-full mt-1 bg-black border border-neutral-800 p-3 rounded-xl text-sm focus:border-rose-500 focus:outline-none" value={labourForm.cost_per_worker_per_hour} onChange={e => setLabourForm({...labourForm, cost_per_worker_per_hour: e.target.value})} />
                    </div>
                    {/* GPS Map Picker — same as farm form */}
                    <div className="border border-neutral-800 rounded-2xl overflow-hidden bg-black/50">
                      <div className="flex flex-col md:flex-row justify-between items-center p-3 border-b border-neutral-800 bg-neutral-900/50">
                        <h4 className="text-sm font-bold text-rose-300">📍 Team Base Location</h4>
                        <button type="button" onClick={executeLabourGPS} className="mt-2 md:mt-0 text-xs font-bold bg-blue-600/20 text-blue-400 hover:bg-blue-600/40 px-3 py-1.5 rounded transition">📡 Use My GPS</button>
                      </div>
                      <div className="h-[220px] w-full bg-neutral-800">
                        <LocationPickerMap lat={labourForm.location_lat} lng={labourForm.location_lng} onChange={(lat, lng) => setLabourForm(prev => ({...prev, location_lat: lat, location_lng: lng}))} />
                      </div>
                      <div className="p-3 flex gap-3">
                        <div className="flex-1">
                          <label className="text-[10px] text-neutral-600 font-bold uppercase">Latitude</label>
                          <input type="number" step="any" className="w-full mt-1 bg-black border border-neutral-800 p-2 rounded-lg text-xs text-neutral-300 focus:border-rose-500 focus:outline-none" value={labourForm.location_lat.toFixed(5)} onChange={e => setLabourForm(prev => ({...prev, location_lat: parseFloat(e.target.value) || prev.location_lat}))} />
                        </div>
                        <div className="flex-1">
                          <label className="text-[10px] text-neutral-600 font-bold uppercase">Longitude</label>
                          <input type="number" step="any" className="w-full mt-1 bg-black border border-neutral-800 p-2 rounded-lg text-xs text-neutral-300 focus:border-rose-500 focus:outline-none" value={labourForm.location_lng.toFixed(5)} onChange={e => setLabourForm(prev => ({...prev, location_lng: parseFloat(e.target.value) || prev.location_lng}))} />
                        </div>
                      </div>
                    </div>
                    <button type="submit" className="w-full bg-rose-600 hover:bg-rose-500 text-white font-bold py-3 rounded-xl transition-all">Mobilize Workforce</button>
                  </form>
                </div>
              )}
              <div className={`space-y-4 ${role === 'admin' ? 'lg:col-span-2' : ''}`}>
                {labourTeams.map(team => (
                  <div key={team.id} className="bg-black/50 border border-neutral-800 p-5 rounded-2xl flex justify-between items-center">
                    <div><h4 className="font-bold text-rose-100">{team.worker_count} Personnel</h4><p className="text-xs text-neutral-500">{team.skills}</p></div>
                    <span className="px-3 py-1 bg-rose-900/30 border border-rose-700/50 text-xs rounded-full text-rose-400">Active</span>
                  </div>
                ))}
              </div>
            </div>
        )}

        {activeTab === 'tasks' && (role === 'machine_owner' || role === 'labour_team') && (
          <div className="space-y-6">
            <h3 className="text-2xl font-bold text-indigo-400 border-b border-neutral-800 pb-4">Active Contracts</h3>
            <div className="grid gap-6">
              {assignments.map(task => (
                <div key={task.id} className="p-6 rounded-2xl border border-neutral-800 bg-neutral-900 flex justify-between items-center">
                  <div>
                    <p className="font-bold text-white mb-1 uppercase tracking-widest text-sm">Request ID #{task.request_id}</p>
                    <p className="text-xs text-neutral-500">Date: <span className="text-indigo-300">{new Date(task.scheduled_date).toLocaleDateString()}</span></p>
                    <span className={`mt-2 inline-block px-2 py-1 text-[10px] uppercase font-bold rounded-full ${
                      task.status === 'COMPLETED' ? 'bg-emerald-900/40 text-emerald-400 border border-emerald-700/50' : 
                      ['FAILED', 'NO_SHOW', 'CANCELLED'].includes(task.status) ? 'bg-rose-900/40 text-rose-400 border border-rose-700/50' :
                      task.status === 'IN_PROGRESS' ? 'bg-blue-900/40 text-blue-400 border border-blue-700/50' :
                      'bg-amber-900/40 text-amber-400 border border-amber-700/50'
                    }`}>{task.status}</span>
                  </div>
                  {['SCHEDULED', 'IN_PROGRESS'].includes(task.status) && (
                    <button onClick={() => handleCompleteTask(task.id)} className="bg-emerald-600 hover:bg-emerald-500 transition-colors text-white px-6 py-3 rounded-xl font-bold text-sm shadow-xl">Complete Task</button>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'dispatcher' && role === 'admin' && (
            <div className="space-y-8">
              <h3 className="text-2xl font-bold text-purple-400 border-b border-neutral-800 pb-4">Global Queue Map</h3>
              <div className="w-full h-[550px] bg-neutral-900 border border-purple-900/50 rounded-2xl relative overflow-hidden">
                <LeafletMap requests={requests} farms={farms} machines={machines} labourTeams={labourTeams} role={role} />
              </div>
              {requests.map(req => (
                <div key={req.id} className="bg-neutral-900 border border-purple-900/30 p-6 rounded-3xl flex flex-col md:flex-row gap-6">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                       <span className="text-2xl font-black text-white">{req.priority_score.toFixed(1)}</span>
                       <span className="text-[10px] text-purple-500 border border-purple-900/50 px-2 py-0.5 rounded-full uppercase font-black tracking-widest">Priority Index</span>
                    </div>
                    <h4 className="font-bold uppercase text-neutral-200 text-sm tracking-tight">{req.type} Logistics Pipeline</h4>
                    <p className="text-[11px] text-neutral-500 mt-1 font-medium italic">Target: Farm Cluster #{req.farm_id} • Critical Window: {req.required_by_date ? req.required_by_date.split('T')[0] : 'TBD'}</p>
                  </div>
                  <div className="flex-1 bg-black/60 p-4 rounded-xl border border-neutral-800">
                    <h5 className="text-xs text-neutral-500 font-bold uppercase mb-4">Assign Resource</h5>
                    <div className="space-y-2">
                       {req.type === 'machine' ? machines.map(m => (
                         <button key={m.id} onClick={() => executeAssignment(req, m.id, 'machine')} className="w-full text-left px-4 py-3 bg-amber-900/20 hover:bg-amber-600/40 border border-amber-700/30 rounded-lg text-amber-200 text-sm transition-all group">
                           Assign <span className="font-bold">Hardware #{m.id}</span>
                         </button>
                       )) : labourTeams.map(l => (
                         <button key={l.id} onClick={() => executeAssignment(req, l.id, 'labour')} className="w-full text-left px-4 py-3 bg-rose-900/20 hover:bg-rose-600/40 border border-rose-700/30 rounded-lg text-rose-200 text-sm transition-all group">
                           Assign <span className="font-bold">Roster #{l.id}</span>
                         </button>
                       ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
        )}
      </main>
      <CopilotWidget />
      <NotificationToaster />
    </div>
  );
}

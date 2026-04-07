"use client";

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import api from '@/lib/api';

export default function DashboardPage() {
  const router = useRouter();
  const { role, token, logout } = useAuthStore();
  const [profileData, setProfileData] = useState<any>(null);

  // Protected Route Check
  useEffect(() => {
    if (!token) {
      router.push('/auth/login');
    } else {
      // Hit the "me" endpoint strictly to prove secure route transmission
      api.get('/auth/me').then(res => setProfileData(res.data)).catch(() => {
        logout();
        router.push('/auth/login');
      });
    }
  }, [token, router, logout]);

  if (!profileData) return <div className="min-h-screen bg-neutral-950 flex items-center justify-center text-emerald-500 animate-pulse font-mono">Syncing Cortex...</div>;

  return (
    <div className="min-h-screen bg-neutral-950 text-white p-8">
      <div className="max-w-6xl mx-auto">
        <header className="flex justify-between items-center mb-12 border-b border-neutral-800 pb-6">
          <div>
            <h1 className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-cyan-500 tracking-tight">Active Command Center</h1>
            <p className="text-neutral-500 mt-2 font-mono text-sm">Clearance Level: <span className="uppercase text-cyan-400">{role}</span></p>
          </div>
          
          <button 
            onClick={() => { logout(); router.push('/auth/login'); }}
            className="px-6 py-2 rounded-lg bg-neutral-900 border border-neutral-700 hover:border-rose-500 hover:text-rose-400 transition-colors text-sm font-bold tracking-wider"
          >
            SEVER LINK
          </button>
        </header>

        <main className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-neutral-900 border border-neutral-800 rounded-2xl p-6">
            <h3 className="text-neutral-400 text-xs font-bold uppercase tracking-wider mb-4 border-b border-neutral-800 pb-2">Identity Matrix</h3>
            <p className="text-lg">{profileData.email}</p>
            <p className="text-sm text-neutral-500 mt-1">ID Tag: #{profileData.id}</p>
          </div>

          <div className="bg-neutral-900 border border-emerald-900/50 rounded-2xl p-6 md:col-span-2 relative overflow-hidden group">
            <div className="absolute -inset-0.5 bg-gradient-to-r from-emerald-500/10 to-cyan-500/10 opacity-0 group-hover:opacity-100 transition-opacity" />
            <h3 className="text-neutral-400 text-xs font-bold uppercase tracking-wider mb-4 border-b border-neutral-800 pb-2">Operational Status</h3>
            <div className="flex items-center gap-4 text-emerald-400">
              <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
              </span>
              Next.js JWT Frontend is perfectly synchronizing with FastAPI Backend Operations.
            </div>
          </div>
        </main>

      </div>
    </div>
  );
}

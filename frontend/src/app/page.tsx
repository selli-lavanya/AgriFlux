"use client";

import { useState, useEffect } from "react";
import api from "../lib/api";
import Link from "next/link";
import { useAuthStore } from "../store/authStore";

export default function Home() {
  const [healthStatus, setHealthStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [mounted, setMounted] = useState(false);
  const { token, role } = useAuthStore();

  useEffect(() => {
    setMounted(true);
  }, []);

  const pingServer = async () => {
    setLoading(true);
    try {
      // Using our dedicated axios interceptor
      // Since NEXT_PUBLIC_API_URL is mapped to /api/v1, /health is technically at root.
      // Wait! Let's cleanly ping the root by backing out of the /api/v1 prefix,
      const response = await api.get("http://127.0.0.1:8000/health");
      setHealthStatus(`SUCCESS! Backend says: ${response.data.message} v${response.data.data.version}`);
    } catch (err: any) {
      setHealthStatus(`FAILED: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-neutral-900 text-white flex flex-col items-center justify-center font-sans tracking-wide">
      <div className="bg-neutral-800 p-12 rounded-3xl shadow-2xl border border-neutral-700 max-w-xl text-center">
        
        {/* Core Header */}
        <h1 className="text-5xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-cyan-500 mb-4 animate-pulse">
          AgriFlux Engine
        </h1>
        <p className="text-neutral-400 mb-10 text-lg">
          The Phase 8 Network Foundation is successfully booting.
        </p>

        {/* Auth State Reflection from Zustand */}
        <div className="bg-neutral-900 rounded-xl p-4 mb-8 border border-neutral-700 text-sm">
          <p className="text-neutral-500 font-bold uppercase tracking-wider mb-2">Zustand Internal State</p>
          <div className="flex justify-between items-center px-4 py-2 bg-black/40 rounded-lg shadow-inner">
            <span className="text-neutral-400">Memory Token:</span>
            <span className={mounted && token ? "text-emerald-400 font-mono" : "text-rose-400 font-mono"}>
              {mounted && token ? "Token Active" : "NULL"}
            </span>
          </div>
          <div className="flex justify-between items-center px-4 py-2 mt-2 bg-black/40 rounded-lg shadow-inner">
            <span className="text-neutral-400">Current Role:</span>
            <span className={mounted && role ? "text-cyan-400 font-mono uppercase" : "text-rose-400 font-mono uppercase"}>
              {mounted && role ? role : "UNAUTHORIZED"}
            </span>
          </div>
        </div>

        {/* Network Button Test */}
        <button 
          onClick={pingServer}
          disabled={loading}
          className="w-full relative py-4 px-8 tracking-wider font-bold rounded-xl overflow-hidden group hover:scale-[1.02] active:scale-95 transition-all outline-none"
        >
          <div className="absolute inset-0 bg-gradient-to-r from-emerald-500 to-cyan-600 opacity-90 group-hover:opacity-100 transition-opacity" />
          <span className="relative text-white flex items-center justify-center gap-2">
            {loading ? (
              <span className="animate-spin h-5 w-5 border-2 border-white/30 border-t-white rounded-full" />
            ) : (
              "PING FASTAPI SERVER"
            )}
          </span>
        </button>

        <div className="grid grid-cols-2 gap-4 mt-8">
          <Link href="/auth/login" className="py-3 px-6 text-center rounded-xl font-bold tracking-wide border border-emerald-500/50 text-emerald-400 hover:bg-emerald-500/10 transition-colors">LOGIN</Link>
          <Link href="/auth/signup" className="py-3 px-6 text-center rounded-xl font-bold tracking-wide border border-cyan-500/50 text-cyan-400 hover:bg-cyan-500/10 transition-colors">SIGNUP</Link>
        </div>

        {/* Dynamic Axios Network Response Text */}
        {healthStatus && (
          <div className={`mt-6 p-4 rounded-lg text-sm font-mono transition-all duration-500 ${healthStatus.startsWith("SUCCESS") ? "bg-emerald-900/40 border border-emerald-500/50 text-emerald-300" : "bg-rose-900/40 border border-rose-500/50 text-rose-300"}`}>
            {healthStatus}
          </div>
        )}

      </div>
    </div>
  );
}

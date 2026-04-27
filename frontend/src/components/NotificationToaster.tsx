"use client";

import { useEffect } from 'react';
import { useNotificationStore } from '@/store/notificationStore';
import { useAuthStore } from '@/store/authStore';

export default function NotificationToaster() {
  const { notifications, addNotification, markAsRead } = useNotificationStore();
  const token = useAuthStore(state => state.token);

  useEffect(() => {
    if (!token) return;

    // Phase 17: SSE Integration
    // Create EventSource connection to the backend stream
    const url = `http://127.0.0.1:8000/api/v1/notifications/stream?token=${token}`;
    const es = new EventSource(url);

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        // Add to global store
        addNotification({
          id: Date.now().toString(),
          ...data,
          read: false
        });
      } catch (err) {
        console.error("Failed to parse SSE event", err);
      }
    };

    es.onerror = (e) => {
      console.error("SSE Connection Error", e);
      // Wait and reconnect is handled natively by EventSource.
    };

    return () => {
      es.close();
    };
  }, [token]);

  const activeNotifications = notifications.filter(n => !n.read).slice(0, 5);

  return (
    <div className="fixed top-6 right-6 z-[9999] flex flex-col gap-3 max-w-sm w-full pointer-events-none">
      {activeNotifications.map((notif) => (
        <div 
          key={notif.id} 
          className="pointer-events-auto bg-neutral-900 border border-neutral-800 p-4 rounded-2xl shadow-2xl shadow-black/50 animate-in slide-in-from-right fade-in duration-500 relative overflow-hidden group"
        >
          {/* Aesthetic Indicator */}
          <div className={`absolute left-0 top-0 bottom-0 w-1 ${
            notif.event_type === 'NEW_REQUEST' ? 'bg-indigo-500' : 
            notif.event_type === 'ASSIGNMENT_COMPLETED' ? 'bg-emerald-500' : 'bg-cyan-500'
          }`} />
          
          <div className="flex justify-between items-start gap-4">
            <div className="flex-1">
              <p className="text-[10px] font-black uppercase tracking-widest text-neutral-500 mb-1">
                {notif.event_type.replace('_', ' ')}
              </p>
              <p className="text-sm text-neutral-200 font-medium leading-relaxed whitespace-pre-wrap">
                {notif.message}
              </p>
            </div>
            <button 
              onClick={() => markAsRead(notif.id)}
              className="text-neutral-600 hover:text-white transition-colors p-1"
            >
              ✕
            </button>
          </div>
          
          <div className="mt-2 flex items-center gap-2">
             <span className="text-[9px] font-mono text-neutral-600">
               {new Date(notif.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
             </span>
          </div>
        </div>
      ))}
    </div>
  );
}

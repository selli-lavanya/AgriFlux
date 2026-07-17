"use client";

import { useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import './leaflet-overrides.css';

// Highly recognizable Div Icons with Emojis for clean visualization
const getIcon = (type: 'farm'|'machine'|'labour', risk: number = 0) => {
  let bgColor = '#10b981'; // Default Green (Secured Farm)
  let iconText = '🌱';
  let size = 32;
  let pulseHtml = '';

  if (type === 'farm') {
    if (risk > 50) { 
      bgColor = '#ef4444'; // Red for High Risk
      iconText = '⚠️'; 
      size = 36; 
      pulseHtml = `<div class="absolute inset-0 bg-red-500 rounded-lg animate-ping opacity-75"></div>`;
    }
  } else if (type === 'machine') {
    bgColor = '#f59e0b'; // Amber
    iconText = '🚜'; 
    size = 28;
  } else if (type === 'labour') {
    bgColor = '#8b5cf6'; // Purple
    iconText = '👷'; 
    size = 28;
  }

  return L.divIcon({
    html: `<div class="relative flex items-center justify-center">
             ${pulseHtml}
             <div style="background-color:${bgColor}; width:${size}px; height:${size}px; border-radius:8px; display:flex; align-items:center; justify-content:center; font-size:${size * 0.55}px; border:2px solid #ffffff; box-shadow:0 4px 10px rgba(0,0,0,0.4); z-index:10; position:relative;">${iconText}</div>
           </div>`,
    className: '',
    iconSize: [size, size],
    iconAnchor: [size/2, size]
  });
};

function BoundFitter({ markers }: { markers: {lat: number, lng: number}[] }) {
  const map = useMap();
  useEffect(() => {
    if (markers && markers.length > 0) {
      const bounds = L.latLngBounds(markers.map(m => [m.lat, m.lng]));
      map.fitBounds(bounds, { padding: [80, 80], maxZoom: 16 });
    }
  }, [markers, map]);
  return null;
}

interface MapProps {
    requests?: any[];
    farms?: any[];
    machines?: any[];
    labourTeams?: any[];
    role: string;
}

export default function MapOverlay({ requests = [], farms = [], machines = [], labourTeams = [], role }: MapProps) {
  
  // Real backend coordinates from DB (Farms)
  const farmMarkers = useMemo(() => {
    return farms.map(farm => {
      const activeReqs = requests.filter(r => r.farm_id === farm.id);
      const highestRisk = activeReqs.length > 0 ? Math.max(...activeReqs.map(r => r.priority_score || 0)) : 0;
      
      return {
        lat: farm.location_lat || 28.61,
        lng: farm.location_lng || 77.20,
        id: farm.id,
        name: farm.name,
        label: farm.location_label,
        address: farm.full_address,
        crop: farm.crop_type,
        risk: highestRisk,
        reqs: activeReqs
      };
    });
  }, [farms, requests]);

  // Determine an operational center based on real farm locations
  const opCenterLat = farmMarkers.length > 0 ? farmMarkers[0].lat : 28.61;
  const opCenterLng = farmMarkers.length > 0 ? farmMarkers[0].lng : 77.20;

  // Use real DB coordinates for machines
  const machineMarkers = useMemo(() => {
    return machines
      .filter(m => m.lat != null && m.lng != null)
      .map(m => ({
        lat: m.lat,
        lng: m.lng,
        id: m.id,
        type: m.type,
        capacity: m.capacity_per_day,
        cost: m.cost_per_hour,
        status: m.status,
      }));
  }, [machines]);

  // Use real DB coordinates for labour teams
  const labourMarkers = useMemo(() => {
    return labourTeams
      .filter(l => l.lat != null && l.lng != null)
      .map(l => ({
        lat: l.lat,
        lng: l.lng,
        id: l.id,
        workers: l.worker_count,
        skills: l.skills,
        cost: l.cost_per_worker_per_hour,
        status: l.status,
      }));
  }, [labourTeams]);

  // Aggregate all items for BoundFitter
  const allPoints = [
    ...farmMarkers,
    ...(role === 'admin' ? machineMarkers : []),
    ...(role === 'admin' ? labourMarkers : [])
  ];

  return (
    <div className="relative w-full h-full font-sans bg-neutral-200">
      <MapContainer 
        key={`map-${opCenterLat}-${opCenterLng}`}
        center={[opCenterLat, opCenterLng]} 
        zoom={11} 
        maxZoom={19} 
        scrollWheelZoom={true} 
        className="w-full h-full z-0 font-sans"
      >
        
        {/* Lighter Testing Basemap (Carto Voyager) - Max Zoom 19 */}
        <TileLayer
            attribution='&copy; CARTO'
            url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
            maxZoom={19}
        />
        
        <BoundFitter markers={allPoints} />
        
        {/* Farm Nodes */}
        {farmMarkers.map(f => (
          <Marker key={`farm-${f.id}`} position={[f.lat, f.lng]} icon={getIcon('farm', f.risk)}>
            <Popup className="clean-popup">
              <div className="p-2 w-[240px]">
                <div className="flex items-center gap-2 mb-2 pb-2 border-b border-gray-200">
                   <span className="text-xl">{f.risk > 50 ? '⚠️' : '🌱'}</span>
                       <div>
                          <h4 className="font-extrabold text-gray-900 capitalize text-base m-0 leading-tight">{f.label ? `${f.name} (${f.label})` : f.name}</h4>
                          <p className="text-[10px] text-gray-500 font-mono mt-1 mb-0 leading-tight">GPS: [{f.lat.toFixed(4)}, {f.lng.toFixed(4)}]</p>
                          {f.address ? (
                            <p className="text-[10px] font-bold text-indigo-600 mt-1 uppercase max-w-[200px] leading-tight truncate">{f.address}</p>
                          ) : (
                            <p className="text-[10px] text-neutral-400 font-black mt-1 uppercase tracking-widest">Address mapping pending</p>
                          )}
                       </div>
                </div>

                {f.reqs.length > 0 ? (
                  <div className="space-y-3 mt-2">
                    {f.reqs.map((r: any) => (
                      <div key={r.id} className="bg-gray-50 p-2 rounded border border-gray-200">
                        <div className="flex justify-between items-center mb-1">
                          <span className="text-[11px] font-bold text-indigo-600 uppercase tracking-widest">{r.type}</span>
                          <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${r.status === 'pending' ? 'bg-amber-100 text-amber-700' : 'bg-green-100 text-green-700'}`}>{r.status}</span>
                        </div>
                        <div className="flex justify-between items-end mt-1">
                           <span className={`text-xl font-black ${r.priority_score > 50 ? 'text-red-500' : 'text-gray-900'}`}>{r.priority_score.toFixed(1)}</span>
                           <span className="text-xs text-gray-400 font-bold">SCORE</span>
                        </div>
                        {r.priority_reason && <p className="text-[10px] text-gray-600 mt-1 leading-tight">{r.priority_reason}</p>}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-green-600 font-bold bg-green-50 p-2 rounded mt-2 border border-green-100">✔ All logistics caught up.</p>
                )}
              </div>
            </Popup>
          </Marker>
        ))}

        {/* Machine Nodes (Admin Only) */}
        {role === 'admin' && machineMarkers.map(m => (
          <Marker key={`mach-${m.id}`} position={[m.lat, m.lng]} icon={getIcon('machine')}>
            <Popup className="clean-popup">
               <div className="p-2 min-w-[190px]">
                 <div className="flex items-center gap-2 mb-2 pb-2 border-b border-amber-200">
                    <span className="text-xl">🚜</span>
                    <div>
                       <p className="text-amber-600 font-bold uppercase tracking-wider text-[10px] m-0">Hardware Provider</p>
                       <p className="text-gray-900 font-extrabold text-base m-0 leading-tight">{m.type} #{m.id}</p>
                    </div>
                 </div>
                 <p className="text-xs text-gray-500 m-0">Capacity: <span className="font-bold text-gray-900">{m.capacity} Acres/day</span></p>
                 {m.cost && <p className="text-xs text-gray-500 m-0 mt-1">Rate: <span className="font-bold text-amber-600">₹{m.cost}/hr</span></p>}
                 {m.status && <p className="text-[10px] font-bold uppercase mt-1 text-emerald-600">{m.status}</p>}
                 <div className="mt-2 pt-2 border-t border-gray-100">
                    <p className="text-[9px] font-mono text-gray-400">GPS (Real Location)</p>
                    <p className="text-[10px] text-gray-500 font-mono">[{m.lat.toFixed(5)}, {m.lng.toFixed(5)}]</p>
                 </div>
               </div>
            </Popup>
          </Marker>
        ))}

        {/* Labour Nodes (Admin Only) */}
        {role === 'admin' && labourMarkers.map(l => (
          <Marker key={`lab-${l.id}`} position={[l.lat, l.lng]} icon={getIcon('labour')}>
            <Popup className="clean-popup">
               <div className="p-2 min-w-[190px]">
                 <div className="flex items-center gap-2 mb-2 pb-2 border-b border-purple-200">
                    <span className="text-xl">👷</span>
                    <div>
                       <p className="text-purple-600 font-bold uppercase tracking-wider text-[10px] m-0">Labour Syndicate</p>
                       <p className="text-gray-900 font-extrabold text-base m-0 leading-tight">Roster #{l.id}</p>
                    </div>
                 </div>
                 <p className="text-xs text-gray-500 m-0">Workers: <span className="font-bold text-gray-900">{l.workers}</span></p>
                 <p className="text-xs text-gray-500 m-0 mt-1">Skills: {l.skills}</p>
                 {l.cost && <p className="text-xs text-gray-500 m-0 mt-1">Rate: <span className="font-bold text-purple-600">₹{l.cost}/worker/hr</span></p>}
                 {l.status && <p className="text-[10px] font-bold uppercase mt-1 text-emerald-600">{l.status}</p>}
                 <div className="mt-2 pt-2 border-t border-gray-100">
                    <p className="text-[9px] font-mono text-gray-400">GPS (Real Location)</p>
                    <p className="text-[10px] text-gray-500 font-mono">[{l.lat.toFixed(5)}, {l.lng.toFixed(5)}]</p>
                 </div>
               </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>

      {/* Clear Legend */}
      <div className="absolute bottom-6 right-6 z-[400] bg-white border border-gray-200 p-4 rounded-xl shadow-lg">
         <h5 className="text-[11px] font-black text-gray-800 uppercase tracking-widest mb-3 border-b border-gray-100 pb-2">Map Legend</h5>
         <div className="space-y-3">
           <div className="flex items-center gap-3 text-xs font-bold text-gray-700">
              <div className="flex items-center justify-center w-6 h-6 bg-red-500 text-white rounded shadow text-[10px]">⚠️</div> High-Risk Farm
           </div>
           <div className="flex items-center gap-3 text-xs font-bold text-gray-700">
              <div className="flex items-center justify-center w-6 h-6 bg-emerald-500 text-white rounded shadow text-[10px]">🌱</div> Normal Farm
           </div>
           {role === 'admin' && (
             <>
               <div className="flex items-center gap-3 text-xs font-bold text-gray-700">
                  <div className="flex items-center justify-center w-6 h-6 bg-amber-500 text-white rounded shadow text-[10px]">🚜</div> Contracted Machine
               </div>
               <div className="flex items-center gap-3 text-xs font-bold text-gray-700">
                  <div className="flex items-center justify-center w-6 h-6 bg-purple-500 text-white rounded shadow text-[10px]">👷</div> Active Roster
               </div>
             </>
           )}
         </div>
      </div>
    </div>
  );
}

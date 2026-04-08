"use client";

import { useEffect, useState, useRef, useMemo } from 'react';
import { MapContainer, TileLayer, Marker, useMapEvents, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

const pickerIcon = L.divIcon({
  html: `<div class="relative flex items-center justify-center">
            <div class="absolute inset-0 bg-emerald-500 rounded-full animate-ping opacity-60"></div>
            <div style="background-color:#10b981; width:24px; height:24px; border-radius:50%; border:3px solid #fff; box-shadow:0 4px 10px rgba(0,0,0,0.5); z-index:10; position:relative;"></div>
            <div style="position:absolute; top:24px; width:4px; height:12px; background-color:#10b981; z-index:9;"></div>
         </div>`,
  className: '',
  iconSize: [24, 36],
  iconAnchor: [12, 36]
});

function MapEventsHandler({ setPosition }: { setPosition: (p: {lat: number, lng: number}) => void }) {
  useMapEvents({
    click(e) {
      setPosition(e.latlng);
    }
  });
  return null;
}

function CenterMap({ position }: { position: {lat: number, lng: number} }) {
  const map = useMap();
  useEffect(() => {
    map.flyTo([position.lat, position.lng], map.getZoom());
  }, [position, map]);
  return null;
}

interface LocationPickerProps {
  lat: number;
  lng: number;
  onChange: (lat: number, lng: number) => void;
}

export default function LocationPickerMap({ lat, lng, onChange }: LocationPickerProps) {
  const [position, setPosition] = useState({ lat, lng });
  
  // Force sync from parent if needed
  useEffect(() => {
    setPosition({ lat, lng });
  }, [lat, lng]);

  const handlePositionChange = (p: {lat: number, lng: number}) => {
    setPosition(p);
    onChange(p.lat, p.lng);
  };

  return (
    <div className="w-full h-full relative font-sans rounded-xl overflow-hidden shadow-inner border border-gray-300">
       <MapContainer center={[lat, lng]} zoom={13} scrollWheelZoom={true} className="w-full h-full z-0 font-sans">
          <TileLayer
             attribution='&copy; CARTO'
             url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
             maxZoom={19}
          />
          <MapEventsHandler setPosition={handlePositionChange} />
          <CenterMap position={position} />
          <Marker position={position} icon={pickerIcon} draggable={true} eventHandlers={{ dragend: (e) => handlePositionChange(e.target.getLatLng()) }} />
       </MapContainer>
       <div className="absolute top-2 right-2 z-[500] pointer-events-none">
          <div className="bg-white/90 backdrop-blur-md text-xs font-mono font-bold text-gray-700 py-1.5 px-3 rounded shadow-lg border border-gray-200">
             [ {position.lat.toFixed(5)}, {position.lng.toFixed(5)} ]
          </div>
       </div>
       <div className="absolute bottom-2 left-2 right-2 z-[400] pointer-events-none">
          <div className="bg-black/80 text-[10px] font-bold uppercase text-emerald-400 py-1 px-3 rounded text-center backdrop-blur-md">
             Drag Pin or Click Terrain to Target
          </div>
       </div>
    </div>
  );
}

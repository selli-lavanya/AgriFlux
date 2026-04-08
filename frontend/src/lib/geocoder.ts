export async function fetchAddressFromCoordinates(lat: number, lng: number): Promise<{ address: string, label: string } | null> {
  try {
    // MVP implementation using OpenStreetMap's Nominatim (Free, no API key required)
    // In the future, this abstraction can easily be swapped to a secure backend endpoint querying Google Maps/Mapbox.
    const response = await fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}`, {
      headers: {
        'Accept-Language': 'en-US,en;q=0.9',
        'User-Agent': 'AgriFlux-MVP-Routing-Engine/1.0' // Mandated by Nominatim terms of service
      }
    });

    if (!response.ok) {
      throw new Error(`Geocoding HTTP Error: ${response.status}`);
    }

    const data = await response.json();
    
    // Safety check if ocean or unmapped area
    if (data.error) {
       return null;
    }

    const addressStr = data.display_name || '';
    
    // Intelligently derive a short 'Sector Label' from the response
    let extractedLabel = '';
    if (data.address) {
       extractedLabel = data.address.farm || data.address.neighbourhood || data.address.suburb || data.address.village || data.address.city || data.address.county || 'Unmapped Sector';
    }

    return {
      address: addressStr,
      label: extractedLabel
    };
  } catch (error) {
    console.error("Geocoding Core Failure:", error);
    return null;
  }
}

import httpx
from app.core.config import settings

class WeatherService:
    async def get_forecast(self, lat: float, lng: float) -> dict:
        if not settings.OPENWEATHER_API_KEY:
             return {"risk_level": "HIGH", "condition": "Missing Key Mock", "description": "No key attached."}
             
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lng}&appid={settings.OPENWEATHER_API_KEY}"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    # Scan atmospheric data across the upcoming 15 hours
                    for item in data.get("list", [])[:5]:
                        condition = item["weather"][0]["main"].upper()
                        if condition in ["RAIN", "THUNDERSTORM", "EXTREME", "SNOW"]:
                            return {
                                "risk_level": "HIGH",
                                "condition": condition,
                                "description": f"Live environmental threat detected: {item['weather'][0]['description']}"
                            }
                    return {"risk_level": "LOW", "condition": "CLEAR", "description": "Satellite radar is clear."}
        except Exception:
            pass

        return {
            "risk_level": "HIGH", 
            "condition": "Failsafe Mock", 
            "description": "API severed. Triggering failsafe urgency."
        }

weather_service = WeatherService()

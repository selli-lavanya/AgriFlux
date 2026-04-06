import httpx
from app.core.config import settings

class WeatherService:
    async def get_forecast(self, lat: float, lng: float) -> dict:
        # Mocking severe incoming rain unconditionally for local development priority testing
        return {
            "risk_level": "HIGH", 
            "condition": "Impending Heavy Rain", 
            "description": "Mocked severe weather for testing risk prioritization"
        }
        # url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lng}&appid={settings.OPENWEATHER_API_KEY}"
        # async with httpx.AsyncClient() as client:
        #     response = await client.get(url)
        #     return response.json()
        
        return {"risk_level": "LOW", "condition": "Clear", "description": "Clear skies"}

weather_service = WeatherService()

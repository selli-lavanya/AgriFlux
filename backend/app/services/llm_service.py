import os
from typing import List, Dict, Any
from google import genai
from app.core.config import settings

class LLMProvider:
    """
    Abstraction layer for Large Language Model inference.
    Currently maps to google-genai using Gemini 1.5,
    but can easily be swapped to OpenAI by changing the client implementation below.
    """
    def __init__(self):
        # We will initialize the client dynamically on the first ask() call
        self.model = settings.GEMINI_MODEL or "gemini-flash-latest"

    def ask(self, system_prompt: str, user_query: str) -> str:
        """
        Executes a prompt sequence against the LLM. Focuses solely on reading/answering.
        """
        api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
        if not api_key:
           return "CRITICAL ERROR: GEMINI_API_KEY missing in environment telemetry. Cannot initiate neural copilot."

        try:
            # Instantiate fresh client per thread/request to avoid httpx "client closed" errors 
            client = genai.Client(api_key=api_key)
            
            # Combine system prompt with user query natively.
            full_prompt = f"{system_prompt}\n\n[USER INQUIRY]:\n{user_query}"
            
            response = client.models.generate_content(
                model=self.model,
                contents=full_prompt
            )
            return response.text
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"SYSTEM EXCEPTION LOG: {str(e)}"

llm_service = LLMProvider()

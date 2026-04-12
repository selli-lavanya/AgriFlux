from google import genai
import os

def test():
    api_key = os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    
    models_to_test = [
        'gemini-2.5-flash',
        'gemini-1.5-flash-8b',
        'gemini-1.5-pro',
        'gemini-2.5-pro',
        'gemini-2.0-flash-lite',
        'gemini-flash-latest',
        'gemma-3-1b-it',
    ]
    
    for model in models_to_test:
        print(f"Testing model: {model}...")
        try:
            response = client.models.generate_content(
                model=model,
                contents='Say OK'
            )
            print(f"SUCCESS limit exists! Model: {model}")
        except Exception as e:
            print(f"FAILED: {str(e)}")

if __name__ == "__main__":
    test()

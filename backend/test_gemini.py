from google import genai
import os
import sys

def test():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.environ.get("GEMINI_API_KEY")
    print(f"Key loaded: {'YES' if api_key else 'NO'}")
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents='Respond with a single word: OK'
        )
        print("Success:", response.text)
    except Exception as e:
        print("Exception:", str(e))
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test()

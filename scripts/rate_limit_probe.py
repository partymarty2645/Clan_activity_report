import logging
import time
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Probe")

client = genai.Client(api_key=API_KEY)

MODELS_TO_TEST = [
    "gemini-3-flash-preview",
     # Fallbacks to compare against
    "gemini-2.0-flash-exp",
    "gemini-2.5-flash"
]

def test_config(model_name, disable_afc=True, bulk=False):
    print(f"\n--- Testing {model_name} [AFC_OFF={disable_afc}] [BULK={bulk}] ---")
    
    # Text
    if bulk:
        text = "Generate 10 different haikus about coding."
    else:
        text = "Hello, how are you?"
        
    config_args = {
        "temperature": 0.7,
        "max_output_tokens": 1024,
    }
    
    if disable_afc:
        config_args["tool_config"] = types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(mode="NONE")
        )
        
    config = types.GenerateContentConfig(**config_args)
    
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=text,
            config=config
        )
        print(f"SUCCESS: {len(response.text)} chars generated.")
        return True
    except Exception as e:
        print(f"FAILED: {e}")
        return False

if __name__ == "__main__":
    print("Starting Quota Probe...")
    
    # 1. Test the user's "Best Result" candidate: Gemini 3 Flash Preview
    # We test it with the known fix (Disable AFC) first.
    test_config("gemini-3-flash-preview", disable_afc=True)
    
    # 2. Test without the fix to see if it breaks immediately
    # time.sleep(2)
    # test_config("gemini-3-flash-preview", disable_afc=False)
    
    # 3. Test Bulk load on 3 Flash Preview
    # time.sleep(2)
    # test_config("gemini-3-flash-preview", disable_afc=True, bulk=True)

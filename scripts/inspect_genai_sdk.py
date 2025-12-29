
from google import genai
from google.genai import types
import inspect

print("--- types.GenerateContentConfig fields ---")
# Try to instantiate to see valid init args or check annotations
try:
    conf = types.GenerateContentConfig()
    print(dir(conf))
except Exception as e:
    print(f"Init failed: {e}")
    # inspect class
    print(dir(types.GenerateContentConfig))


print("\n--- FunctionCallingConfig? ---")
if hasattr(types, 'FunctionCallingConfig'):
    print("Found types.FunctionCallingConfig")
else:
    print("types.FunctionCallingConfig NOT found")

print("\n--- ToolConfig? ---")
if hasattr(types, 'ToolConfig'):
    print("Found types.ToolConfig")
else:
    print("types.ToolConfig NOT found")

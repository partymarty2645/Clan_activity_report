import os
import time
import random
import logging
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Setup Logging
logger = logging.getLogger("GeminiService")
logging.basicConfig(level=logging.INFO)

# Load env
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env")

# Initialize Client (New SDK)
client = genai.Client(api_key=API_KEY)

# CONFIG
# Allow overriding the default Gemini model (stable precedence) via GEMINI_MODEL.
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
FALLBACK_MODELS = ["gemini-3-flash", "gemini-2.5-flash"]

ALLOWED_MODELS = []
for model in [DEFAULT_MODEL] + FALLBACK_MODELS:
    if model not in ALLOWED_MODELS:
        ALLOWED_MODELS.append(model)

# Selected model (lazy initialization)
_selected_model = None

def select_model():
    """Select the first available model from allowed list without test calls."""
    global _selected_model
    if _selected_model is None:
        # Just return the first preference - let retry logic handle failures
        _selected_model = ALLOWED_MODELS[0]
        logger.info(f"Selected model: {_selected_model}")
    return _selected_model

MODEL_NAME = select_model() 

GENERATION_CONFIG = types.GenerateContentConfig(
    temperature=1,
    top_p=0.95,
    top_k=40,
    max_output_tokens=8192,
    response_mime_type="text/plain"
)

def retry_with_backoff(retries=5, backoff_in_seconds=10, max_backoff=300):
    """Decorator to retry function on rate limits with exponential backoff and jitter."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            attempt = 0
            while attempt <= retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    err_str = str(e).lower()
                    if any(keyword in err_str for keyword in ["429", "exhausted", "quota", "rate limit"]):
                        # IMMEDIATE FAILURE on 429 - no retries allowed
                        logger.error(f"Gemini API Rate Limit hit. IMMEDIATE FAILURE - no retries allowed.")
                        raise e
                    else:
                        # For other errors, don't retry
                        logger.error(f"Gemini API Error: {e}")
                        raise e
                attempt += 1
        return wrapper
    return decorator

def get_lore():
    try:
        with open("assets/lore.md", "r") as f:
            return f.read()
    except FileNotFoundError:
        return "You are a helpful assistant."

@retry_with_backoff(retries=5, backoff_in_seconds=10)
def generate_character_card(username, context_json):
    """
    Generates a 'Round X' card using the new google-genai SDK.
    """
    lore = get_lore()
    
    prompt = f"""
    {lore}
    
    ---
    **USER REQUEST**:
    Generate a character card for:
    Name: {username}
    Context: {context_json}
    """
    
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=GENERATION_CONFIG
    )
    
    return response.text

@retry_with_backoff(retries=5, backoff_in_seconds=10)
def generate_bulk_cards(profiles):
    """
    Generates cards for multiple users in a SINGLE request.
    profiles: List of dicts { 'username': str, 'category': str, 'context': dict }
    """
    lore = get_lore()
    
    # Construct a massive context block
    profiles_text = ""
    for p in profiles:
        profiles_text += f"""
        ---
        CANDIDATE: {p['username']} ({p['category']})
        DATA: {p['context']}
        ---
        """

    prompt = f"""
    {lore}
    
    **BATCH INSTRUCTION**:
    Below is data for {len(profiles)} different clan members. 
    You must generate a full "Round X" character card for EACH ONE.
    
    Output Format:
    Separate each card with "## SCORED_CARD_SEPARATOR" so I can parse them.
    Maintain the specific Rules/Tone for every single card.
    
    **PROFILES TO ANALYZE**:
    {profiles_text}
    """
    
    # Increase token limit for bulk output
    bulk_config = types.GenerateContentConfig(
        temperature=1,
        max_output_tokens=30000,
        response_mime_type="text/plain"
    )

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=bulk_config
    )
    
    return response.text

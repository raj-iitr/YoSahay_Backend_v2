import os
from dotenv import load_dotenv

# Load environment variables from a .env file for local development
load_dotenv()

# --- Core Application Settings ---
class Settings:
    # WhatsApp / Meta API
    WHATSAPP_ACCESS_TOKEN: str = os.getenv("WHATSAPP_ACCESS_TOKEN")
    WHATSAPP_VERIFY_TOKEN: str = os.getenv("WHATSAPP_VERIFY_TOKEN")
    WHATSAPP_PHONE_NUMBER_ID: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    
    # OpenAI API
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    EMBED_MODEL: str = "text-embedding-3-small"
    GENERATION_MODEL: str = "gpt-4o-mini"
    CLASSIFICATION_MODEL: str = "gpt-4o-mini"
    
    # Vector DB
    CHROMA_COLLECTION_NAME: str = "yosahay_schemes_v1"
    
    # RAG Pipeline Parameters
    DISTANCE_THRESHOLD: float = 1.6
    TOP_K_RESULTS: int = 3
    
    # Caching (Redis)
    REDIS_URL: str = os.getenv("REDIS_URL") # Provided by Render.com
    CACHE_EXPIRATION_SECONDS: int = 3600 # 1 hour
    
    # Analytics (Google Sheets)
    GCP_SA_KEY_B64: str = os.getenv("GCP_SA_KEY_B64") # Base64 encoded service account key

    # Bot Behavior
    AVAILABLE_SCHEMES: list[str] = ["pm_jay", "pm_kisan", "pmayg", "pmfby", "pmuy"]
    SMALL_TALK_WORDS: set[str] = {
        "hi", "hello", "thanks", "thank you", "ok", "okay", "bye", 
        "goodbye", "namaste", "shukriya", "dhanyavaad"
    }

# Instantiate settings to be imported by other modules
settings = Settings()

# --- Basic validation ---
if not all([
    settings.WHATSAPP_ACCESS_TOKEN, 
    settings.WHATSAPP_VERIFY_TOKEN, 
    settings.WHATSAPP_PHONE_NUMBER_ID, 
    settings.OPENAI_API_KEY,
    settings.REDIS_URL,
    settings.GCP_SA_KEY_B64
]):
    raise ValueError("FATAL: One or more critical environment variables are missing.")
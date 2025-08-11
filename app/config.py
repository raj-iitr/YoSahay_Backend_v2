# app/config.py
import os
from dotenv import load_dotenv
import logging

# --- Intelligent .env file loading ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
dotenv_path = os.path.join(project_root, '.env')

if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    logging.info(f"Successfully loaded environment variables from: {dotenv_path}")
else:
    logging.warning(".env file not found. Relying on system environment variables.")


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
    
    # --- [REMOVED] Redis settings are no longer here ---
    
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
# [REMOVED] settings.REDIS_URL is no longer checked here
if not all([
    settings.WHATSAPP_ACCESS_TOKEN, 
    settings.WHATSAPP_VERIFY_TOKEN, 
    settings.WHATSAPP_PHONE_NUMBER_ID, 
    settings.OPENAI_API_KEY,
    settings.GCP_SA_KEY_B64
]):
    missing_vars = [var for var in ["WHATSAPP_ACCESS_TOKEN", "WHATSAPP_VERIFY_TOKEN", "WHATSAPP_PHONE_NUMBER_ID", "OPENAI_API_KEY", "GCP_SA_KEY_B64"] if not os.getenv(var)]
    raise ValueError(f"FATAL: Critical environment variables are missing. Please check your .env file or system variables. Missing: {', '.join(missing_vars)}")
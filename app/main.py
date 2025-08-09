# app/main.py

import os
import logging
import httpx
import chromadb
import time
import re
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response, HTTPException, BackgroundTasks
from openai import OpenAI

# --- Your Bot's Core Logic Imports ---
from app.detector import detect_lang
from app.embedder import embed_text
from app.db import search_chunks, load_data_into_chroma
from app.responder import generate_response
from app.analytics_logger import log_analytics_event

DISTANCE_THRESHOLD = 1.6 # Adjust this based on your final relevance tests

# --- Setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
load_dotenv()

# --- Environment Variables ---
ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not all([ACCESS_TOKEN, VERIFY_TOKEN, PHONE_NUMBER_ID, OPENAI_API_KEY]):
    logger.critical("FATAL: Environment variables not configured correctly.")

SMALL_TALK_WORDS = {"hi", "hello", "thanks", "thank you", "ok", "okay", "bye", "goodbye", "namaste", "shukriya", "dhanyavaad"}

# --- Centralized Database, Cache, and App Initialization ---
client = chromadb.Client()
collection = client.get_or_create_collection(name="schemes")
query_cache = {}
app = FastAPI()

# --- AI Intent Classifier Setup ---
AVAILABLE_SCHEMES = [
    "pm_jay", "pm_kisan", "pmayg", "pmfby", "pmuy" # Maintain this list
]
openai_client = OpenAI(api_key=OPENAI_API_KEY)

def classify_scheme_intent(query: str) -> str | None:
    system_prompt = f"""You are an expert intent classifier. Your task is to identify which of the following government schemes a user is asking about. The available schemes are: {', '.join(AVAILABLE_SCHEMES)}. Analyze the user's query. Respond with ONLY the single, most relevant scheme name from the list. If the query is ambiguous or not about any of the schemes, respond with ONLY the word 'none'. Do not add any explanation."""
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini", messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": query}],
            temperature=0, max_tokens=10
        )
        result = response.choices[0].message.content.strip().lower()
        return result if result in AVAILABLE_SCHEMES else None
    except Exception as e:
        logger.error(f"Error during intent classification: {e}")
        return None

# --- Startup Event ---
@app.on_event("startup")
def on_startup():
    load_data_into_chroma(collection)

# --- Background Task for Processing and Logging ---
async def process_and_log_reply(user_phone: str, user_text: str, background_tasks: BackgroundTasks):
    analytics_data = {"UserID": user_phone, "QueryText": user_text}

    try:
        normalized_query = user_text.lower().strip()

        if normalized_query in SMALL_TALK_WORDS:
            analytics_data["ResponseType"] = "SMALL_TALK"
            reply = "Namaste! Sarkari yojanaon ke baare mein jaankari ke liye apna prashn likhein."
            if normalized_query in {"thanks", "thank you", "shukriya", "dhanyavaad"}: reply = "Aapka swagat hai!"
            await send_whatsapp_message(user_phone, reply)
            return

        if normalized_query in query_cache:
            cached_reply, timestamp = query_cache[normalized_query]
            if time.time() - timestamp < 300: return
            analytics_data.update({"CacheStatus": "HIT", "ResponseType": "CACHED"})
            await send_whatsapp_message(user_phone, cached_reply)
            return

        analytics_data["CacheStatus"] = "MISS"
        
        detected_scheme = classify_scheme_intent(normalized_query)
        logger.info(f"AI classified scheme intent: {detected_scheme}")

        lang = detect_lang(user_text)
        analytics_data["Language"] = lang
        query_vector = embed_text(user_text)
        results = search_chunks(collection, query_vector, scheme_filter=detected_scheme, top_k=3)
        best_distance = results['distances'][0][0] if results.get('distances') and results['distances'][0] else 2.0
        analytics_data["RelevanceDistance"] = best_distance
        
        if best_distance > DISTANCE_THRESHOLD:
            analytics_data.update({"ContextStatus": "NOT_FOUND_THRESHOLD", "ResponseType": "FALLBACK"})
            reply = generate_response(user_text, [], lang) 
            query_cache[normalized_query] = (reply, time.time())
            await send_whatsapp_message(user_phone, reply)
            return

        chunks = results['documents'][0] if results.get('documents') and results['documents'] else []
        top_scheme_source = results['metadatas'][0][0].get('scheme', 'unknown')
        analytics_data.update({"ContextStatus": "FOUND", "ContextSource": top_scheme_source, "ResponseType": "AI_GENERATED"})
        reply = generate_response(user_text, chunks, lang)
        query_cache[normalized_query] = (reply, time.time())
        await send_whatsapp_message(user_phone, reply)

    except Exception as e:
        analytics_data["ResponseType"] = "ERROR"
        logger.error(f"[BACKGROUND_TASK_ERROR] User={user_phone}, Details='{e}'", exc_info=True)
    finally:
        background_tasks.add_task(log_analytics_event, analytics_data=analytics_data)

# --- Function to Send WhatsApp Message ---
async def send_whatsapp_message(to: str, message: str):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    json_data = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": message}}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=json_data)
            response.raise_for_status()
            logger.info(f"Successfully sent message to {to}.")
    except httpx.HTTPStatusError as e: logger.error(f"Error sending message: {e.response.text}")
    except Exception as e: logger.error(f"An unexpected error occurred while sending message: {e}")

# --- Webhook Endpoints ---
@app.get("/")
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info("Webhook verified successfully!")
        return Response(content=challenge, status_code=200)
    else:
        logger.error("Webhook verification failed.")
        raise HTTPException(status_code=403, detail="Verification token mismatch.")

@app.post("/")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        payload = await request.json()
        if (payload.get("object") and payload.get("entry") and payload["entry"][0].get("changes") and 
                payload["entry"][0]["changes"][0].get("value")):
            value_payload = payload["entry"][0]["changes"][0]["value"]
            if "messages" in value_payload:
                message_data = value_payload["messages"][0]
                user_phone = message_data["from"]
                message_type = message_data.get("type")
                if message_type == "text":
                    user_text = message_data.get("text", {}).get("body", "").strip()
                    if not user_text or not any(char.isalpha() for char in user_text):
                        return Response(status_code=200)
                    background_tasks.add_task(process_and_log_reply, user_phone, user_text, background_tasks)
                else:
                    logger.warning(f"[METRIC] Type=IGNORED_MESSAGE, UserID={user_phone}, Reason='Non-text message', MessageType='{message_type}'")
            else:
                logger.info("Received a non-message notification (e.g., status update). Ignoring.")
    except Exception as e:
        logger.error(f"Error in handle_webhook (before background task): {e}", exc_info=True)
    return Response(status_code=200)

@app.get("/health")
def health_check():
    try:
        item_count = collection.count()
        cache_size = len(query_cache)
        return {
            "status": "ok", "message": "Server is running.", "chromadb_collection_name": collection.name,
            "items_in_collection": item_count, "items_in_cache": cache_size
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
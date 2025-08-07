# app/main.py

import os
import logging
import httpx
import chromadb
import time
import re # We still need the basic 're' for your previous structure, let's keep it.
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response, HTTPException, BackgroundTasks

# --- Your Bot's Core Logic Imports ---
from app.detector import detect_lang
from app.embedder import embed_text
from app.db import search_chunks, load_data_into_chroma
from app.responder import generate_response

DISTANCE_THRESHOLD = 1.2 # Adjust this based on your final relevance tests

# --- Setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
load_dotenv()

# --- Environment Variables ---
ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

if not all([ACCESS_TOKEN, VERIFY_TOKEN, PHONE_NUMBER_ID]):
    logger.critical("FATAL: Environment variables not configured correctly.")

SMALL_TALK_WORDS = {"hi", "hello", "thanks", "thank you", "ok", "okay", "bye", "goodbye", "namaste", "shukriya", "dhanyavaad"}

# --- Centralized Database, Cache, and App Initialization ---
client = chromadb.Client()
collection = client.get_or_create_collection(name="schemes")
query_cache = {}
app = FastAPI()

# --- Startup Event ---
@app.on_event("startup")
def on_startup():
    load_data_into_chroma(collection)

# --- Background Task for Processing ---
async def process_and_reply(user_phone: str, user_text: str):
    try:
        normalized_query = user_text.lower().strip()

        if normalized_query in SMALL_TALK_WORDS:
            logger.info(f"Detected small talk: '{normalized_query}'. Sending polite reply.")
            reply = "Namaste! Sarkari yojanaon ke baare mein jaankari ke liye apna prashn likhein."
            if normalized_query in {"thanks", "thank you", "shukriya", "dhanyavaad"}:
                reply = "Aapka swagat hai!"
            await send_whatsapp_message(user_phone, reply)
            return

        if normalized_query in query_cache:
            cached_reply, timestamp = query_cache[normalized_query]
            if time.time() - timestamp < 300:
                logger.warning(f"[DUPLICATE_IGNORED] Ignoring duplicate request for query: '{normalized_query}'")
                return
            
            logger.info(f"[METRIC] Type=CACHE_HIT, UserID={user_phone}, Query='{normalized_query}'")
            await send_whatsapp_message(user_phone, cached_reply)
            return

        logger.info(f"[METRIC] Type=CACHE_MISS, UserID={user_phone}, Query='{normalized_query}'")

        lang = detect_lang(user_text)
        query_vector = embed_text(user_text)
        results = search_chunks(collection, query_vector, lang=lang, top_k=3)
        
        best_distance = results['distances'][0][0] if results.get('distances') and results['distances'][0] else 2.0
        
        if best_distance > DISTANCE_THRESHOLD:
            logger.warning(f"[METRIC] Type=NO_CONTEXT_FOUND, UserID={user_phone}, Reason='Relevance threshold failed', Distance={best_distance:.2f}, Query='{user_text}'")
            reply = generate_response(user_text, [], lang) 
            query_cache[normalized_query] = (reply, time.time())
            await send_whatsapp_message(user_phone, reply)
            return

        chunks = results['documents'][0] if results.get('documents') and results['documents'] else []
        top_scheme_source = results['metadatas'][0][0].get('scheme', 'unknown')
        logger.info(f"[METRIC] Type=CONTEXT_FOUND, UserID={user_phone}, TopScheme='{top_scheme_source}', Distance={best_distance:.2f}, Query='{user_text}'")
        
        reply = generate_response(user_text, chunks, lang)
        query_cache[normalized_query] = (reply, time.time())
        await send_whatsapp_message(user_phone, reply)

    except Exception as e:
        logger.error(f"[BACKGROUND_TASK_ERROR] User={user_phone}, Details='{e}'", exc_info=True)

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
    except httpx.HTTPStatusError as e:
        logger.error(f"Error sending message: {e.response.text}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while sending message: {e}")

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
                    
                    # --- THIS IS THE GUARANTEED WORKING FILTER ---
                    # It checks if ANY character in the string is a letter.
                    # This is fully Unicode-aware and reliable for all languages.
                    if not user_text or not any(char.isalpha() for char in user_text):
                        logger.warning(f"[METRIC] Type=IGNORED_MESSAGE, UserID={user_phone}, Reason='Empty or non-letter message', Content='{user_text}'")
                        return Response(status_code=200)
                    # --- END OF FINAL FILTER ---

                    logger.info(f"[METRIC] Type=MESSAGE_RECEIVED, UserID={user_phone}")
                    background_tasks.add_task(process_and_reply, user_phone, user_text)
                    
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
            "status": "ok",
            "message": "Server is running.",
            "chromadb_collection_name": collection.name,
            "items_in_collection": item_count,
            "items_in_cache": cache_size
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
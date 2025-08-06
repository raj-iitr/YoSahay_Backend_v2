

# app/main.py

# import os
# import logging
# import httpx
# import chromadb
# from dotenv import load_dotenv
# from fastapi import FastAPI, Request, Response, HTTPException

# # --- Your Bot's Core Logic Imports ---
# from app.detector import detect_lang
# from app.embedder import embed_text
# from app.db import search_chunks, load_data_into_chroma
# from app.responder import generate_response

# # --- Setup ---
# logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
# logger = logging.getLogger(__name__)
# load_dotenv()

# # --- Environment Variables ---
# ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
# VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")
# PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

# if not all([ACCESS_TOKEN, VERIFY_TOKEN, PHONE_NUMBER_ID]):
#     logger.critical("FATAL: Environment variables not configured correctly.")

# # --- Centralized Database, Cache, and App Initialization ---
# client = chromadb.Client()  # Correct in-memory client for deployment
# collection = client.get_or_create_collection(name="schemes")
# query_cache = {}  # In-memory cache
# app = FastAPI()

# # --- Startup Event ---
# @app.on_event("startup")
# def on_startup():
#     load_data_into_chroma(collection)

# # --- Function to Send WhatsApp Message ---
# async def send_whatsapp_message(to: str, message: str):
#     url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
#     headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
#     json_data = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": message}}
    
#     try:
#         async with httpx.AsyncClient() as client:
#             response = await client.post(url, headers=headers, json=json_data)
#             response.raise_for_status()
#             logger.info(f"Successfully sent message to {to}.")
#     except httpx.HTTPStatusError as e:
#         logger.error(f"Error sending message: {e.response.text}")
#     except Exception as e:
#         logger.error(f"An unexpected error occurred while sending message: {e}")

# # --- Webhook Endpoints ---
# @app.get("/")
# async def verify_webhook(request: Request):
#     mode = request.query_params.get("hub.mode")
#     token = request.query_params.get("hub.verify_token")
#     challenge = request.query_params.get("hub.challenge")

#     if mode == "subscribe" and token == VERIFY_TOKEN:
#         logger.info("Webhook verified successfully!")
#         return Response(content=challenge, status_code=200)
#     else:
#         logger.error("Webhook verification failed.")
#         raise HTTPException(status_code=403, detail="Verification token mismatch.")

# @app.post("/")
# async def handle_webhook(request: Request):
#     try:
#         payload = await request.json()
        
#         if (payload.get("object") and payload.get("entry") and payload["entry"][0].get("changes") and 
#                 payload["entry"][0]["changes"][0].get("value") and payload["entry"][0]["changes"][0]["value"].get("messages")):
            
#             message_data = payload["entry"][0]["changes"][0]["value"]["messages"][0]
            
#             if message_data.get("type") == "text":
#                 user_phone = message_data["from"]
#                 user_text = message_data["text"]["body"].strip()
#                 normalized_query = user_text.lower()

#                 logger.info(f"Processing message from {user_phone}: '{user_text}'")
    
#       # <<<--- METRIC 1: Track every message received from a unique user ---
#                 logger.info(f"[METRIC] Type=MESSAGE_RECEIVED, UserID={user_phone}")

#                 # --- CACHE LOGIC START ---
#                 if normalized_query in query_cache:
#                     cached_reply = query_cache[normalized_query]
#                     logger.info(f"[ANALYTICS] Type=CACHE_HIT, Query='{normalized_query}'")
#                     await send_whatsapp_message(user_phone, cached_reply)
#                     return Response(status_code=200)
#                 # --- CACHE LOGIC END ---

#                 # If we are here, it's a CACHE MISS. We need to call the AI.
#                 logger.info(f"[ANALYTICS] Type=CACHE_MISS, Query='{normalized_query}'")

#                 # === YOUR CORE LOGIC EXECUTES HERE ===
#                 lang = detect_lang(user_text)
#                 logger.info(f"Detected language: {lang}")

#                 # Simple logic to adjust context size
#                 if len(user_text.split()) < 5:
#                     num_chunks = 2
#                 else:
#                     num_chunks = 3

#                 query_vector = embed_text(user_text)
#                 results = search_chunks(collection, query_vector, lang=lang, top_k=num_chunks)
#                 chunks = results['documents'][0] if results.get('documents') and results['documents'] else []
                
#                 if chunks:
#                     top_scheme_source = results['metadatas'][0][0].get('source', 'unknown')
#                     logger.info(f"[METRIC] Type=CONTEXT_FOUND, UserID={user_phone}, TopScheme='{top_scheme_source}', Query='{user_text}'")
#                 else:
#                     # We found NO relevant context. This is a "failure" of our knowledge base.
#                     logger.warning(f"[METRIC] Type=NO_CONTEXT_FOUND, UserID={user_phone}, Query='{user_text}'")
                
                
#                 reply = generate_response(user_text, chunks, lang)
                
#                 # --- SAVE TO CACHE ---
#                 query_cache[normalized_query] = reply
#                 # ---------------------

#                 await send_whatsapp_message(user_phone, reply)

#     except Exception as e:
#         logger.error(f"Error processing webhook: {e}", exc_info=True)
    
#     return Response(status_code=200)

# @app.get("/health")
# def health_check():
#     try:
#         item_count = collection.count()
#         return {
#             "status": "ok",
#             "message": "Server is running.",
#             "chromadb_collection_name": collection.name,
#             "items_in_collection": item_count,
#         }
#     except Exception as e:
#         logger.error(f"Health check failed: {e}", exc_info=True)
#         return {"status": "error", "message": str(e)}


# app/main.py

import os
import logging
import httpx
import chromadb
import time  # <-- ADDED: Import the time module for timestamps
import re 
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response, HTTPException, BackgroundTasks # <-- ADDED: Import BackgroundTasks

# --- Your Bot's Core Logic Imports ---
from app.detector import detect_lang
from app.embedder import embed_text
from app.db import search_chunks, load_data_into_chroma
from app.responder import generate_response

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

# --- ADDED: A set of common "small talk" words to filter ---
SMALL_TALK_WORDS = {"hi", "hello", "thanks", "thank you", "ok", "okay", "bye", "goodbye", "namaste", "shukriya", "dhanyavaad"}

# --- Centralized Database, Cache, and App Initialization ---
client = chromadb.Client()
collection = client.get_or_create_collection(name="schemes")
# --- MODIFIED: The cache will now store a tuple: (reply_text, timestamp) ---
query_cache = {}
app = FastAPI()

# --- Startup Event ---
@app.on_event("startup")
def on_startup():
    load_data_into_chroma(collection)

# --- ADDED: New function to handle all slow AI logic in the background ---
async def process_and_reply(user_phone: str, user_text: str):
    """
    This function contains all the slow AI logic and runs in the background
    to prevent Meta timeouts and handle duplicate messages.
    """
    try:
        normalized_query = user_text.lower().strip()

        # --- ADDED: Small talk filter to handle greetings efficiently ---
        if normalized_query in SMALL_TALK_WORDS:
            logger.info(f"Detected small talk: '{normalized_query}'. Sending polite reply.")
            reply = "Namaste! Sarkari yojanaon ke baare mein jaankari ke liye apna prashn likhein."
            if normalized_query in {"thanks", "thank you", "shukriya", "dhanyavaad"}:
                reply = "Aapka swagat hai!"
            await send_whatsapp_message(user_phone, reply)
            return  # Exit the task, no AI call needed.

        # --- MODIFIED: Cache logic with timestamp check to prevent duplicates ---
        if normalized_query in query_cache:
            cached_reply, timestamp = query_cache[normalized_query]
            # If the reply was sent less than 5 minutes ago, ignore this duplicate request.
            if time.time() - timestamp < 300: # 300 seconds = 5 minutes
                logger.warning(f"[DUPLICATE_IGNORED] Ignoring duplicate request for query: '{normalized_query}'")
                return # Silently end the task without replying.
            
            logger.info(f"[METRIC] Type=CACHE_HIT, UserID={user_phone}, Query='{normalized_query}'")
            await send_whatsapp_message(user_phone, cached_reply)
            return

        logger.info(f"[METRIC] Type=CACHE_MISS, UserID={user_phone}, Query='{normalized_query}'")

        # === YOUR CORE LOGIC REMAINS THE SAME, BUT IS NOW INSIDE THIS FUNCTION ===
        lang = detect_lang(user_text)
        logger.info(f"Detected language: {lang}")
        
        if len(user_text.split()) < 5:
            num_chunks = 2
        else:
            num_chunks = 3

        query_vector = embed_text(user_text)
        results = search_chunks(collection, query_vector, lang=lang, top_k=num_chunks)
        chunks = results['documents'][0] if results.get('documents') and results['documents'] else []
        
        if chunks:
            top_scheme_source = results['metadatas'][0][0].get('source', 'unknown')
            logger.info(f"[METRIC] Type=CONTEXT_FOUND, UserID={user_phone}, TopScheme='{top_scheme_source}', Query='{user_text}'")
        else:
            logger.warning(f"[METRIC] Type=NO_CONTEXT_FOUND, UserID={user_phone}, Query='{user_text}'")
        
        reply = generate_response(user_text, chunks, lang)
        
        # --- MODIFIED: Save the reply AND the current time to the cache ---
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

# --- MODIFIED: The handle_webhook function is now short and fast ---
@app.post("/")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks): # ADDED: background_tasks parameter
    """
    This function now responds to Meta instantly and hands off the real work to a background task.
    """
    try:
        payload = await request.json()
        
        if (payload.get("object") and payload.get("entry") and payload["entry"][0].get("changes") and  payload["entry"][0]["changes"][0].get("value")):
            
            value_payload = payload["entry"][0]["changes"][0]["value"]
            
            # 2. Check if it's a message. If not, it could be a 'status' update, which we ignore.
            if "messages" in value_payload:
                message_data = value_payload["messages"][0]
                user_phone = message_data["from"]
                message_type = message_data.get("type")
            
                # 3. Handle TEXT messages
                if message_type == "text":
                    user_text = message_data.get("text", {}).get("body", "").strip()
                    
                    if not user_text or not re.search(r'[a-zA-Z0-9]', user_text):
                        logger.warning(f"[METRIC] Type=IGNORED_MESSAGE, UserID={user_phone}, Reason='Empty or symbol-only message'")
                        return Response(status_code=200)

                # ADDED: Log the message received right away
                    logger.info(f"[METRIC] Type=MESSAGE_RECEIVED, UserID={user_phone}")

                # ADDED: Add the slow work to the background task queue
                    background_tasks.add_task(process_and_reply, user_phone, user_text)
                    
                else:
                    logger.warning(f"[METRIC] Type=IGNORED_MESSAGE, UserID={user_phone}, Reason='Non-text message', MessageType='{message_type}'")

            else:
                logger.info("Received a non-message notification (e.g., status update). Ignoring.")

            
    except Exception as e:
        logger.error(f"Error in handle_webhook (before background task): {e}", exc_info=True)
    
    # IMPORTANT: This now returns 200 OK immediately, preventing Meta timeouts.
    return Response(status_code=200)

@app.get("/health")
def health_check():
    try:
        item_count = collection.count()
        return {
            "status": "ok",
            "message": "Server is running.",
            "chromadb_collection_name": collection.name,
            "items_in_collection": item_count,
            "items_in_cache": len(query_cache) # ADDED: Show cache size
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
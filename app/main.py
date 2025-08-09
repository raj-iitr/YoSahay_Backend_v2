# # app/main.py

# import os
# import logging
# import httpx
# import chromadb
# import time
# import json


# import re # We still need the basic 're' for your previous structure, let's keep it.
# from dotenv import load_dotenv
# from fastapi import FastAPI, Request, Response, HTTPException, BackgroundTasks
# from app.analytics_logger import log_user_question

# # --- Your Bot's Core Logic Imports ---
# from app.detector import detect_lang
# from app.embedder import embed_text
# from app.db import search_chunks, load_data_into_chroma
# from app.responder import generate_response
# from openai import OpenAI # Make sure OpenAI is imported if not already
# from app.analytics_logger import log_analytics_event 


# DISTANCE_THRESHOLD = 1.6 # Adjust this based on your final relevance tests

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

# SMALL_TALK_WORDS = {"hi", "hello", "thanks", "thank you", "ok", "okay", "bye", "goodbye", "namaste", "shukriya", "dhanyavaad"}

# # --- Centralized Database, Cache, and App Initialization ---
# client = chromadb.Client()
# collection = client.get_or_create_collection(name="schemes")
# query_cache = {}
# app = FastAPI()

# # --- Startup Event ---
# @app.on_event("startup")
# def on_startup():
#     load_data_into_chroma(collection)

# # In app/main.py, near the top after the setup section

# # --- NEW: Keyword-based Intent Detection ---
# # This dictionary maps scheme names (your folder names) to keywords.

# # This is the list of your folder names. This is now the ONLY thing you need to maintain.
# AVAILABLE_SCHEMES = [
#     "pm_jay",
#     "pm_kisan",
#     "pmayg",
#     "pmfby",
#     "pmuy"
# ]

# # Initialize the OpenAI client for the classifier
# openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# def classify_scheme_intent(query: str) -> str | None:
#     """
#     Uses a cheap LLM call to classify the user's query into one of the available schemes.
#     """
#     # Create a system prompt that forces the AI to act as a classifier
#     system_prompt = f"""You are an expert intent classifier. Your task is to identify which of the following government schemes a user is asking about.
#     The available schemes are: {', '.join(AVAILABLE_SCHEMES)}.
    
#     Analyze the user's query. Respond with ONLY the single, most relevant scheme name from the list.
#     If the query is ambiguous or not about any of the schemes, respond with ONLY the word "none".
#     Do not add any explanation or punctuation.
#     """

#     try:
#         response = openai_client.chat.completions.create(
#             model="gpt-4o-mini", # Fast and cheap for classification
#             messages=[
#                 {"role": "system", "content": system_prompt},
#                 {"role": "user", "content": query}
#             ],
#             temperature=0, # We want deterministic classification
#             max_tokens=10 # The response will be very short (e.g., "pm_kisan")
#         )
        
#         result = response.choices[0].message.content.strip().lower()

#         if result in AVAILABLE_SCHEMES:
#             return result
#         else:
#             return None # If the AI says "none" or anything else, return None
#     except Exception as e:
#         logger.error(f"Error during intent classification: {e}")
#         return None # In case of an API error, default to a general search

# # --- Background Task for Processing ---
# # in app/main.py
# # In app/main.py

# async def process_and_reply(user_phone: str, user_text: str, background_tasks: BackgroundTasks):
#     """
#     This is the final, complete version of the background task.
#     It gathers all analytics data and logs it to Google Sheets at the end.
#     """
#     # 1. Initialize the analytics data bucket
#     analytics_data = {
#         "UserID": user_phone,
#         "QueryText": user_text,
#     }

#     try:
#         normalized_query = user_text.lower().strip()

#         # --- Stage 1: Small Talk Filter ---
#         if normalized_query in SMALL_TALK_WORDS:
#             analytics_data["ResponseType"] = "SMALL_TALK"
#             reply = "Namaste! Sarkari yojanaon ke baare mein jaankari ke liye apna prashn likhein."
#             if normalized_query in {"thanks", "thank you", "shukriya", "dhanyavaad"}:
#                 reply = "Aapka swagat hai!"
#             await send_whatsapp_message(user_phone, reply)
#             return  # Exit early

#         # --- Stage 2: Cache Check ---
#         if normalized_query in query_cache:
#             cached_reply, timestamp = query_cache[normalized_query]
#             if time.time() - timestamp < 300:
#                 return # Silently ignore duplicates
            
#             analytics_data.update({"CacheStatus": "HIT", "ResponseType": "CACHED"})
#             await send_whatsapp_message(user_phone, cached_reply)
#             return

#         analytics_data["CacheStatus"] = "MISS"

#         # --- Stage 3: Core RAG Pipeline ---
#         lang = detect_lang(user_text)
#         analytics_data["Language"] = lang
        
#         query_vector = embed_text(user_text)
#         results = search_chunks(collection, query_vector, lang=lang, top_k=3)
        
#         best_distance = results['distances'][0][0] if results.get('distances') and results['distances'][0] else 2.0
#         analytics_data["RelevanceDistance"] = best_distance
        
#         if best_distance > DISTANCE_THRESHOLD:
#             analytics_data.update({"ContextStatus": "NOT_FOUND_THRESHOLD", "ResponseType": "FALLBACK"})
#             reply = generate_response(user_text, [], lang) 
#             query_cache[normalized_query] = (reply, time.time())
#             await send_whatsapp_message(user_phone, reply)
#             return

#         chunks = results['documents'][0] if results.get('documents') and results['documents'] else []
#         top_scheme_source = results['metadatas'][0][0].get('scheme', 'unknown')
        
#         analytics_data.update({"ContextStatus": "FOUND", "ContextSource": top_scheme_source, "ResponseType": "AI_GENERATED"})
        
#         reply = generate_response(user_text, chunks, lang)
#         query_cache[normalized_query] = (reply, time.time())
#         await send_whatsapp_message(user_phone, reply)

#     except Exception as e:
#         analytics_data["ResponseType"] = "ERROR"
#         logger.error(f"[BACKGROUND_TASK_ERROR] User={user_phone}, Details='{e}'", exc_info=True)
    
#     finally:
#         # --- FINAL STEP: Log everything to Google Sheets in the background ---
#         background_tasks.add_task(log_analytics_event, analytics_data=analytics_data)



    
#     """
#     This is the complete, final version of the background processing task.
#     It includes the AI intent classifier and the high-performance RAG pipeline.
#     """
#     try:
#         normalized_query = user_text.lower().strip()

#         # --- Stage 1: Handle Small Talk & Simple Cases ---
#         if normalized_query in SMALL_TALK_WORDS:
#             logger.info(f"Detected small talk: '{normalized_query}'. Sending polite reply.")
#             reply = "Namaste! Sarkari yojanaon ke baare mein jaankari ke liye apna prashn likhein."
#             if normalized_query in {"thanks", "thank you", "shukriya", "dhanyavaad"}:
#                 reply = "Aapka swagat hai!"
#             await send_whatsapp_message(user_phone, reply)
#             return

#         # --- Stage 2: Check the Cache ---
#         if normalized_query in query_cache:
#             cached_reply, timestamp = query_cache[normalized_query]
#             if time.time() - timestamp < 300: # 5-minute anti-duplicate window
#                 logger.warning(f"[DUPLICATE_IGNORED] Ignoring duplicate request for query: '{normalized_query}'")
#                 return
            
#             logger.info(f"[METRIC] Type=CACHE_HIT, UserID={user_phone}, Query='{normalized_query}'")
#             await send_whatsapp_message(user_phone, cached_reply)
#             return

#         logger.info(f"[METRIC] Type=CACHE_MISS, UserID={user_phone}, Query='{normalized_query}'")

#         # --- Stage 3: High-Performance RAG Pipeline ---
#         # 1. Classify Intent with AI
#         detected_scheme = classify_scheme_intent(normalized_query)
#         logger.info(f"AI classified scheme intent: {detected_scheme}")

#         # 2. Embed the User's Query
#         lang = detect_lang(user_text)
#         logger.info(f"Detected language: {lang}")
#         query_vector = embed_text(user_text)
        
#         # 3. Perform a Filtered Search in ChromaDB
#         results = search_chunks(collection, query_vector, scheme_filter=detected_scheme, top_k=3)
        
#         # 4. Check for Relevance using the Distance Threshold
#         best_distance = results['distances'][0][0] if results.get('distances') and results['distances'][0] else 2.0
        
#         if best_distance > DISTANCE_THRESHOLD:
#             logger.warning(f"[METRIC] Type=NO_CONTEXT_FOUND, UserID={user_phone}, Reason='Relevance threshold failed', Distance={best_distance:.2f}, Query='{user_text}'")
#             reply = generate_response(user_text, [], lang) # Call with empty chunks to get fallback message
#             query_cache[normalized_query] = (reply, time.time())
#             await send_whatsapp_message(user_phone, reply)
#             return

#         # 5. Generate and Send the Final Response
#         chunks = results['documents'][0] if results.get('documents') and results['documents'] else []
#         top_scheme_source = results['metadatas'][0][0].get('scheme', 'unknown')
#         logger.info(f"[METRIC] Type=CONTEXT_FOUND, UserID={user_phone}, TopScheme='{top_scheme_source}', Distance={best_distance:.2f}, Query='{user_text}'")
        
#         reply = generate_response(user_text, chunks, lang)
        
#         # Save the successful reply to the cache
#         query_cache[normalized_query] = (reply, time.time())
#         await send_whatsapp_message(user_phone, reply)

#     except Exception as e:
#         logger.error(f"[BACKGROUND_TASK_ERROR] User={user_phone}, Details='{e}'", exc_info=True)
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
# async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
#     try:
#         payload = await request.json()
        
#         if (payload.get("object") and payload.get("entry") and payload["entry"][0].get("changes") and 
#                 payload["entry"][0]["changes"][0].get("value")):
            
#             value_payload = payload["entry"][0]["changes"][0]["value"]
            
#             if "messages" in value_payload:
#                 message_data = value_payload["messages"][0]
#                 user_phone = message_data["from"]
#                 message_type = message_data.get("type")
            
#                 if message_type == "text":
#                     user_text = message_data.get("text", {}).get("body", "").strip()
                    
#                     # --- THIS IS THE GUARANTEED WORKING FILTER ---
#                     # It checks if ANY character in the string is a letter.
#                     # This is fully Unicode-aware and reliable for all languages.
#                     if not user_text or not any(char.isalpha() for char in user_text):
#                         logger.warning(f"[METRIC] Type=IGNORED_MESSAGE, UserID={user_phone}, Reason='Empty or non-letter message', Content='{user_text}'")
#                         return Response(status_code=200)
#                     # --- END OF FINAL FILTER ---
                    
                    
#                     # <<<--- THIS IS THE NEW ANALYTICS CALL ---
#                     # Log the user's question to Google Sheets in the background.
#                     background_tasks.add_task(log_user_question, user_id=user_phone, question_text=user_text)
#                     # --- END OF NEW CALL ---

#                     logger.info(f"[METRIC] Type=MESSAGE_RECEIVED, UserID={user_phone}")
#                     background_tasks.add_task(process_and_reply, user_phone, user_text)
                    
#                 else:
#                     logger.warning(f"[METRIC] Type=IGNORED_MESSAGE, UserID={user_phone}, Reason='Non-text message', MessageType='{message_type}'")
#             else:
#                 logger.info("Received a non-message notification (e.g., status update). Ignoring.")
            
#     except Exception as e:
#         logger.error(f"Error in handle_webhook (before background task): {e}", exc_info=True)
    
#     return Response(status_code=200)

# @app.get("/health")
# def health_check():
#     try:
#         item_count = collection.count()
#         cache_size = len(query_cache)
#         return {
#             "status": "ok",
#             "message": "Server is running.",
#             "chromadb_collection_name": collection.name,
#             "items_in_collection": item_count,
#             "items_in_cache": cache_size
#         }
#     except Exception as e:
#         logger.error(f"Health check failed: {e}", exc_info=True)
#         return {"status": "error", "message": str(e)}





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
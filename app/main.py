
# # app/main.py

# from fastapi import FastAPI, Request
# from fastapi.responses import JSONResponse
# from app.detector import detect_lang
# from app.embedder import embed_text
# from app.db import search_chunks
# from app.responder import generate_response

# app = FastAPI()

# @app.get("/health")
# async def health_check():
#     return {"status": "ok"}

# @app.post("/whatsapp-webhook")
# async def whatsapp_webhook(request: Request):
#     try:
#         payload = await request.json()
#         message = payload.get("messages", [{}])[0]

#         user_phone = message.get("from", "unknown")
#         user_text = message.get("text", {}).get("body", "").strip()

#         if not user_text:
#             return JSONResponse(content={"error": "No message text found"}, status_code=400)

#         # Step 1: Detect language
#         lang = detect_lang(user_text)

#         # Step 2: Embed query
#         query_vector = embed_text(user_text)

#         # Step 3: Search ChromaDB
#         results = search_chunks(query_vector, lang=lang, top_k=3)
#         chunks = results['documents'][0]

#         # Step 4: Generate response
#         reply = generate_response(user_text, chunks, lang)

#         # Simulate WhatsApp reply format
#         return JSONResponse(content={
#             "to": user_phone,
#             "reply": reply,
#             "lang": lang
#         })

#     except Exception as e:
#         return JSONResponse(content={"error": str(e)}, status_code=500)




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
# from app.db import search_chunks, load_data_into_chroma,collection
# from app.responder import generate_response

# # --- Setup ---
# # Configure logging to see events and errors
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
# )
# logger = logging.getLogger(__name__)

# # Load environment variables from .env file
# load_dotenv()
# ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
# VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")
# PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

# # Verify that environment variables are set
# if not all([ACCESS_TOKEN, VERIFY_TOKEN, PHONE_NUMBER_ID]):
#     logger.critical("FATAL: Environment variables not configured correctly.")
#     # In a real deployment, you might want to exit here.
#     # For now, we'll just log the critical error.

# # Initialize FastAPI app
# app = FastAPI()


# # --- Function to Send WhatsApp Message ---
# async def send_whatsapp_message(to: str, message: str):
#     """
#     Sends a WhatsApp message using the Meta Graph API.
#     """
#     url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
#     headers = {
#         "Authorization": f"Bearer {ACCESS_TOKEN}",
#         "Content-Type": "application/json",
#     }
#     json_data = {
#         "messaging_product": "whatsapp",
#         "to": to,
#         "type": "text",
#         "text": {"body": message},
#     }
    
#     try:
#         async with httpx.AsyncClient() as client:
#             response = await client.post(url, headers=headers, json=json_data)
#             response.raise_for_status()  # Raises an exception for 4xx or 5xx status codes
#             logger.info(f"Successfully sent message to {to}. Response: {response.json()}")
#     except httpx.HTTPStatusError as e:
#         logger.error(f"Error sending message: {e.response.text}")
#     except Exception as e:
#         logger.error(f"An unexpected error occurred while sending message: {e}")

# # ATTACH THE STARTUP EVENT TO YOUR APP
# @app.on_event("startup")
# def on_startup():
#     load_data_into_chroma()



# # --- Webhook Endpoints ---
# # Meta requires both GET and POST on the same endpoint.
# # We'll use '/webhook' as is standard.
# @app.get("/webhook")
# async def verify_webhook(request: Request):
#     """
#     Handles the webhook verification challenge from Meta.
#     """
#     mode = request.query_params.get("hub.mode")
#     token = request.query_params.get("hub.verify_token")
#     challenge = request.query_params.get("hub.challenge")

#     if mode == "subscribe" and token == VERIFY_TOKEN:
#         logger.info("Webhook verified successfully!")
#         return Response(content=challenge, status_code=200)
#     else:
#         logger.error("Webhook verification failed.")
#         raise HTTPException(status_code=403, detail="Verification token mismatch.")

# @app.post("/webhook")
# async def handle_webhook(request: Request):
#     """
#     Handles incoming messages from WhatsApp.
#     """
#     try:
#         payload = await request.json()
#         logger.info(f"Received payload: {payload}")

#         # IMPORTANT: Check the payload structure carefully.
#         # It's nested under 'entry', 'changes', 'value', 'messages'.
#         if (payload.get("object") == "whatsapp_business_account" and
#                 payload.get("entry") and
#                 payload["entry"][0].get("changes") and
#                 payload["entry"][0]["changes"][0].get("value") and
#                 payload["entry"][0]["changes"][0]["value"].get("messages")):
            
#             message_data = payload["entry"][0]["changes"][0]["value"]["messages"][0]
            
#             # We only process text messages for now
#             if message_data.get("type") == "text":
#                 user_phone = message_data["from"]
#                 user_text = message_data["text"]["body"].strip()
                
#                 logger.info(f"Processing message from {user_phone}: '{user_text}'")

#                 # === YOUR CORE LOGIC EXECUTES HERE ===
#                 lang = detect_lang(user_text)
#                 query_vector = embed_text(user_text)
#                 results = search_chunks(query_vector, lang=lang, top_k=3)
#                 chunks = results['documents'][0]
#                 reply = generate_response(user_text, chunks, lang)
#                 # ====================================

#                 # Send the reply back to the user
#                 await send_whatsapp_message(user_phone, reply)

#     except Exception as e:
#         # Log the full error for debugging
#         logger.error(f"Error processing webhook: {e}", exc_info=True)
#         # Always return 200 OK to Meta. Otherwise, they will keep resending the event.
    
#     return Response(status_code=200)

# # A more robust health_check function for debugging

# @app.get("/health")
# def health_check():
#     status_report = {
#         "status": "ok",
#         "message": "Server is running.",
#         "chromadb_collection_name": None,
#         "collection_item_count": None,
#         "peek_status": None,
#         "error_details": None
#     }

#     try:
#         # Check 1: Can we access the collection?
#         if collection:
#             status_report["chromadb_collection_name"] = collection.name
#         else:
#             raise ValueError("ChromaDB collection object is not available.")

#         # Check 2: Can we get the count?
#         try:
#             item_count = collection.count()
#             status_report["collection_item_count"] = item_count
#         except Exception as e:
#             status_report["collection_item_count"] = "Error getting count."
#             raise e # Re-raise the exception to be caught by the outer block

#         # Check 3: Can we peek at the data?
#         try:
#             # Only peek if there are items to avoid errors on empty collections
#             if item_count > 0:
#                 items_preview = collection.peek(limit=1)
#                 status_report["peek_status"] = "Success"
#                 # Note: We won't return the full preview to keep the health check light
#             else:
#                 status_report["peek_status"] = "Collection is empty, did not peek."
#         except Exception as e:
#             status_report["peek_status"] = "Error during peek."
#             raise e # Re-raise the exception

#     except Exception as e:
#         # If any of the above checks fail, update the status report
#         status_report["status"] = "error"
#         status_report["message"] = "An error occurred during health check."
#         status_report["error_details"] = f"{type(e).__name__}: {str(e)}"
#         # Optional: Print the full traceback to the terminal for more detail
#         import traceback
#         traceback.print_exc()

#     return 


# app/main.py

import os
import logging
import httpx
import chromadb
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response, HTTPException

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

# --- Centralized Database, Cache, and App Initialization ---
client = chromadb.Client()  # Correct in-memory client for deployment
collection = client.get_or_create_collection(name="schemes")
query_cache = {}  # In-memory cache
app = FastAPI()

# --- Startup Event ---
@app.on_event("startup")
def on_startup():
    load_data_into_chroma(collection)

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
async def handle_webhook(request: Request):
    try:
        payload = await request.json()
        
        if (payload.get("object") and payload.get("entry") and payload["entry"][0].get("changes") and 
                payload["entry"][0]["changes"][0].get("value") and payload["entry"][0]["changes"][0]["value"].get("messages")):
            
            message_data = payload["entry"][0]["changes"][0]["value"]["messages"][0]
            
            if message_data.get("type") == "text":
                user_phone = message_data["from"]
                user_text = message_data["text"]["body"].strip()
                normalized_query = user_text.lower()

                logger.info(f"Processing message from {user_phone}: '{user_text}'")

                # --- CACHE LOGIC START ---
                if normalized_query in query_cache:
                    cached_reply = query_cache[normalized_query]
                    logger.info(f"[ANALYTICS] Type=CACHE_HIT, Query='{normalized_query}'")
                    await send_whatsapp_message(user_phone, cached_reply)
                    return Response(status_code=200)
                # --- CACHE LOGIC END ---

                # If we are here, it's a CACHE MISS. We need to call the AI.
                logger.info(f"[ANALYTICS] Type=CACHE_MISS, Query='{normalized_query}'")

                # === YOUR CORE LOGIC EXECUTES HERE ===
                lang = detect_lang(user_text)
                logger.info(f"Detected language: {lang}")

                # Simple logic to adjust context size
                if len(user_text.split()) < 5:
                    num_chunks = 2
                else:
                    num_chunks = 3

                query_vector = embed_text(user_text)
                results = search_chunks(collection, query_vector, lang=lang, top_k=num_chunks)
                chunks = results['documents'][0] if results.get('documents') and results['documents'] else []
                
                reply = generate_response(user_text, chunks, lang)
                
                # --- SAVE TO CACHE ---
                query_cache[normalized_query] = reply
                # ---------------------

                await send_whatsapp_message(user_phone, reply)

    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
    
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
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
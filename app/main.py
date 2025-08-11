# app/main.py
import logging
import httpx
import chromadb
# import redis.asyncio as redis <-- REMOVED
from fastapi import FastAPI, Request, Response, HTTPException, BackgroundTasks
from openai import OpenAI

# --- Core Application Imports ---
from app.config import settings
from app.db import load_data_into_chroma, search_chunks
from app.embedder import embed_text
from app.responder import generate_response
from app.detector import detect_lang
from app.analytics_logger import log_analytics_event

# --- Setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --- Centralized Clients and App Initialization ---
chroma_client = chromadb.Client()
collection = chroma_client.get_or_create_collection(name=settings.CHROMA_COLLECTION_NAME)
# redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True) <-- REMOVED
openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
app = FastAPI()

# --- AI Helper Functions ---
def classify_scheme_intent(query: str) -> str | None:
    # (This function remains unchanged)
    system_prompt = f"""You are an expert intent classifier. Your task is to identify which of the following government schemes a user is asking about. The available schemes are: {', '.join(settings.AVAILABLE_SCHEMES)}. Analyze the user's query. Respond with ONLY the single, most relevant scheme name from the list. If the query is ambiguous or not about any of the schemes, respond with ONLY the word 'none'. Do not add any explanation."""
    try:
        response = openai_client.chat.completions.create(
            model=settings.CLASSIFICATION_MODEL,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": query}],
            temperature=0, max_tokens=10
        )
        result = response.choices[0].message.content.strip().lower()
        return result if result in settings.AVAILABLE_SCHEMES else None
    except Exception as e:
        logger.error(f"Error during intent classification: {e}")
        return None

def expand_query(query: str) -> str:
    # (This function remains unchanged)
    system_prompt = "You are a helpful assistant who rephrases a user's query to be more effective for a vector database search. Generate a single, more detailed question or a set of keywords that captures the core intent of the original query. Do not answer the question. Only provide the rephrased query."
    try:
        response = openai_client.chat.completions.create(
            model=settings.CLASSIFICATION_MODEL,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": f"Original query: {query}"}],
            temperature=0.3, max_tokens=80
        )
        expanded_query = response.choices[0].message.content.strip()
        logger.info(f"Expanded query for search: '{expanded_query}'")
        return expanded_query
    except Exception as e:
        logger.error(f"Error during query expansion: {e}")
        return query

# --- Startup Event ---
@app.on_event("startup")
async def on_startup():
    load_data_into_chroma(collection)
    # --- [REMOVED] The Redis connection check is gone ---
    logger.info("YoSahay application startup complete.")

# --- Background Task for Processing and Logging ---
async def process_and_reply(user_phone: str, user_text: str, background_tasks: BackgroundTasks):
    analytics_data = {"UserID": user_phone, "QueryText": user_text}
    
    try:
        normalized_query = user_text.lower().strip()

        # --- Small Talk Filter ---
        if normalized_query in settings.SMALL_TALK_WORDS:
            analytics_data["ResponseType"] = "SMALL_TALK"
            reply = "Namaste! Sarkari yojanaon ke baare mein jaankari ke liye apna prashn likhein."
            if normalized_query in {"thanks", "thank you", "shukriya", "dhanyavaad"}:
                reply = "Aapka swagat hai!"
            await send_whatsapp_message(user_phone, reply)
            return

        # --- [REMOVED] The entire Redis cache check block is gone ---
        analytics_data["CacheStatus"] = "DISABLED"

        # --- Start of RAG Pipeline ---
        lang = detect_lang(user_text)
        analytics_data["Language"] = lang
        
        detected_scheme = classify_scheme_intent(normalized_query)
        analytics_data["IntentScheme"] = detected_scheme
        logger.info(f"AI classified scheme intent: {detected_scheme}")

        expanded_query = expand_query(user_text)
        query_vector = embed_text(expanded_query)
        
        results = search_chunks(collection, query_vector, scheme_filter=detected_scheme, top_k=settings.TOP_K_RESULTS)
        
        best_distance = results['distances'][0][0] if results.get('distances') and results['distances'][0] else 2.0
        analytics_data["RelevanceDistance"] = best_distance
        
        if best_distance > settings.DISTANCE_THRESHOLD:
            analytics_data.update({"ContextStatus": "NOT_FOUND_THRESHOLD", "ResponseType": "FALLBACK"})
            final_reply = generate_response(user_text, [], lang) 
        else:
            chunks = results['documents'][0] if results.get('documents') else []
            top_scheme_source = results['metadatas'][0][0].get('scheme', 'unknown') if results.get('metadatas') else 'unknown'
            analytics_data.update({"ContextStatus": "FOUND", "ContextSource": top_scheme_source, "ResponseType": "AI_GENERATED"})
            final_reply = generate_response(user_text, chunks, lang)
        
        # --- [REMOVED] The call to cache the new result is gone ---
        await send_whatsapp_message(user_phone, final_reply)

    except Exception as e:
        analytics_data["ResponseType"] = "ERROR"
        logger.error(f"[BACKGROUND_TASK_ERROR] User={user_phone}, Details='{e}'", exc_info=True)
    finally:
        background_tasks.add_task(log_analytics_event, analytics_data=analytics_data)

# --- Function to Send WhatsApp Message ---
async def send_whatsapp_message(to: str, message: str):
    # (This function remains unchanged)
    url = f"https://graph.facebook.com/v18.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}", "Content-Type": "application/json"}
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
    # (This function remains unchanged)
    if (request.query_params.get("hub.mode") == "subscribe" and 
        request.query_params.get("hub.verify_token") == settings.WHATSAPP_VERIFY_TOKEN):
        logger.info("Webhook verified successfully!")
        return Response(content=request.query_params.get("hub.challenge"), status_code=200)
    logger.error("Webhook verification failed.")
    raise HTTPException(status_code=403, detail="Verification token mismatch.")

@app.post("/")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
    # (This function remains unchanged)
    try:
        payload = await request.json()
        if (payload.get("object") and payload.get("entry") and 
            payload["entry"][0].get("changes") and 
            payload["entry"][0]["changes"][0].get("value", {}).get("messages")):
            
            message_data = payload["entry"][0]["changes"][0]["value"]["messages"][0]
            user_phone = message_data["from"]
            
            if message_data.get("type") == "text":
                user_text = message_data.get("text", {}).get("body", "").strip()
                if not user_text or not any(char.isalpha() for char in user_text):
                    return Response(status_code=200)
                
                background_tasks.add_task(process_and_reply, user_phone, user_text, background_tasks)
            else:
                logger.warning(f"Ignored non-text message from {user_phone}")
    except Exception as e:
        logger.error(f"Error in handle_webhook: {e}", exc_info=True)
    
    return Response(status_code=200)

@app.get("/health")
async def health_check():
    try:
        item_count = collection.count()
        # redis_ping = await redis_client.ping() <-- REMOVED
        return {
            "status": "ok",
            "message": "Server is running.",
            "chromadb_collection_name": collection.name,
            "items_in_collection": item_count,
            # "redis_connected": redis_ping <-- REMOVED
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail={"status": "error", "message": str(e)})
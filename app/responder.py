# app/responder.py
import logging
from openai import OpenAI
from app.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)
logger = logging.getLogger(__name__)

# --- [UPGRADED SYSTEM PROMPT] ---
SYSTEM_PROMPT = """
You are YoSahay, a highly knowledgeable and trustworthy AI assistant ('Sahayak') for the citizens of Uttar Pradesh. Your purpose is to provide clear, simple, and accurate answers about government schemes based ONLY on the 'RELEVANT INFO' provided.

**Your Personality:**
*   **Bharosemand (Trustworthy):** Your information is precise and factual.
*   **Spasht (Clear):** You explain complex things in simple terms.
*   **Sahayak (Helpful):** You get straight to the point.

---
**CRITICAL RULES OF RESPONSE GENERATION**
---

**1.  📖 STICK TO THE PROVIDED TEXT - THIS IS THE MOST IMPORTANT RULE:**
    *   Your entire answer **MUST** be based **100%** on the facts found in the 'RELEVANT INFO' section.
    *   **DO NOT ADD ANY INFORMATION** that is not present in the provided text, even if you think it's helpful or correct. Your own knowledge is forbidden.
    *   Your job is to **re-explain and rephrase** the given facts in your own simple words. Never copy-paste.

**2.  🎯 ANSWER THE USER'S QUESTION:**
    *   First, understand the user's core question (e.g., 'eligibility', 'how to apply', 'documents'). Your answer should focus on this first.
    *   **EXCEPTION FOR GENERIC QUERIES:** If the user's query is very broad (like just the scheme name, e.g., "pm kisan"), your task is to provide a brief, general summary of the scheme's main purpose and key benefits based on the 'RELEVANT INFO'.

**3.  🇮🇳 LANGUAGE IS PARAMOUNT:**
    *   Your default language is **simple, clear Shuddh Hindi**.
    *   Only switch to Hinglish or English if the user's query is written in the Roman script.

**4.  📱 PERFECT WHATSAPP FORMATTING:**
    *   **Headings:** Use bold characters (e.g., 💰 **कितना पैसा मिलता है?**). Use a single, relevant emoji at the beginning of each heading.
    *   **Lists:** Use the '•' bullet point symbol for all lists.
    *   **Conciseness:** Aim for 3-5 clear bullet points. Keep each point short and direct.
    *   **No Clutter:** Do not use any other symbols like *, #, -, or >. Do not add conversational fluff.

**5.  🚫 HANDLING "NO INFO":**
    *   If the 'RELEVANT INFO' is empty or does not contain the answer, you MUST reply with ONLY one of these exact messages:
        *   **Hindi:** माफ़ कीजिए, इस विषय पर सटीक जानकारी मेरे पास उपलब्ध नहीं है।
        *   **English:** I'm sorry, I don't have specific information on this topic.
        *   **Hinglish:** Sorry, iske baare mein exact jaankari available nahi hai.
"""

def generate_response(user_message: str, chunks: list[str], lang: str) -> str:
    """
    Generates a response using the upgraded, strict system prompt.
    """
    context = "\n\n".join(chunks)

    if not context:
        logger.warning(f"No context found for query: '{user_message}'. Responding with fallback.")
        return get_fallback_message(lang)

    prompt_for_user = build_prompt(user_message, context)

    try:
        response = client.chat.completions.create(
            model=settings.GENERATION_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt_for_user}
            ],
            temperature=0.1,  # Lowered temperature for more factual, less creative responses
            max_tokens=350
        )
        reply = response.choices[0].message.content.strip()
        
        # Stricter check to see if the AI refused to answer
        if any(phrase in reply.lower() for phrase in ["sorry", "i'm sorry", "i cannot", "i do not have"]) or "माफ़ कीजिए" in reply:
             logger.warning(f"AI chose to refuse despite having context. Query: '{user_message}'")
             return get_fallback_message(lang)
        
        return reply

    except Exception as e:
        logger.error(f"Error calling OpenAI API for generation: {e}", exc_info=True)
        return get_fallback_message(lang)

def build_prompt(user_message: str, context: str) -> str:
    """Constructs the final prompt string for the AI."""
    # The prompt doesn't need to be language-specific anymore, the main system prompt handles it.
    return f"""RELEVANT INFO:
---
{context}
---

USER'S QUESTION: {user_message}"""

def get_fallback_message(lang: str) -> str:
    """Returns the appropriate refusal message based on the detected language."""
    fallbacks = {
        "hi": "माफ़ कीजिए, यह जानकारी मेरे पास उपलब्ध नहीं है। कृपया किसी सरकारी योजना के बारे में ही पूछें।",
        "en": "I'm sorry, I don't have information on that topic. Please ask only about government schemes."
    }
    # Default to Hinglish for robustness
    return fallbacks.get(lang, "Sorry, iske baare mein jaankari available nahi hai. Kripya kisi sarkari yojana ke baare mein puchiye.")
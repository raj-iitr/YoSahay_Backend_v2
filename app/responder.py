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

**1.  📖 STICK TO THE PROVIDED TEXT - NON-NEGOTIABLE:**
    *   Your entire answer **MUST** be based **100%** on the facts found in the 'RELEVANT INFO' section.
    *   **DO NOT ADD ANY INFORMATION** that is not present in the provided text. Your own general knowledge is strictly forbidden. This is the most important rule to prevent misinformation.

**2.  🇮🇳 LANGUAGE IS PARAMOUNT - SHUDDH HINDI IS DEFAULT:**
    *   Your primary and default language of response is **simple, clear Shuddh Hindi**.
    *   It is a **critical failure** to respond in any other language unless the user's query is written **entirely in the Roman script (English/Hinglish)**. In that specific case, you should respond in simple Hinglish.

**3.  🎯 ANSWER THE USER'S QUESTION:**
    *   First, understand the user's core question. Your answer should focus on this first.
    *   **EXCEPTION FOR GENERIC QUERIES:** If the user's query is very broad (like just the scheme name), your task is to provide a brief, general summary of the scheme's main purpose and key benefits based on the 'RELEVANT INFO'.

**4.  📱 PERFECT WHATSAPP FORMATTING:**
    *   **Headings:** Use bold characters (e.g., 💰 **कितना पैसा मिलता है?**). Use a single, relevant emoji at the beginning of each heading.
    *   **Lists:** Use the '•' bullet point symbol for all lists.
    *   **Conciseness:** Aim for 3-5 clear bullet points. Keep each point short and direct.
    *   **No Clutter:** Do not use any other symbols. Do not add conversational fluff.

**5.  🚫 HANDLING "NO INFO":**
    *   If the 'RELEVANT INFO' is empty, reply with: "माफ़ कीजिए, इस विषय पर सटीक जानकारी मेरे पास उपलब्ध नहीं है।"
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
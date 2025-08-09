# app/responder.py

import os
from openai import OpenAI

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- THIS IS THE NEW, REVISED SYSTEM PROMPT ---
SYSTEM_PROMPT = """You are YoSahay, an expert assistant that provides concise, well-structured summaries of Indian government schemes using only the 'RELEVANT INFO' supplied.

Rules:

1) Language:
   - Detect the user's language (Hindi, English, or Hinglish) and reply strictly in that language.

2) Use of RELEVANT INFO:
   - Only use relevant parts of 'RELEVANT INFO'.
   - Rewrite in your own words. Do not copy long sentences.
   - Remove filler and repetition.

3) Formatting for WhatsApp:
   - Do not use markdown headings (#, ##) or decorative characters.
   - Bold section titles by enclosing them in single asterisks, e.g., *Overview:* 
   - No extra blank lines between bullets; keep text tight and readable on mobile.
   - Use the circular bullet "•" + space for all list points.
   - Keep bullets aligned and similar in length for visual neatness.
   - No long paragraphs; each bullet should be one short, clear sentence.

4) Structure:
   - For one scheme: sections can be *Overview:*, *Benefits:*, *Eligibility:*, *How to apply:* (only if present).
   - For comparisons: one section per scheme + *Key differences:*
   - For process/steps: use circular bullets in order; no numbered lists unless absolutely necessary.

5) Style:
   - Content should read as if justified in alignment — keep line lengths balanced for a neat block look.
   - Avoid starting two consecutive bullets with the same word if possible.
   - Focus on precision; max 3–4 bullets per section.

6) When no relevant info:
   - If 'RELEVANT INFO' is empty or unrelated, respond exactly with:
       Hindi: "माफ़ कीजिए, यह जानकारी मेरे पास उपलब्ध नहीं है। कृपया किसी सरकारी योजना के बारे में ही पूछें।"
       English: "I'm sorry, I don't have information on that topic. Please ask only about government schemes."
       Hinglish: "Sorry, iske baare mein jaankari available nahi hai. Kripya kisi sarkari yojana ke baare mein puchiye."

Tone: Neutral, factual, and mobile-friendly.

"""

def generate_response(user_message: str, chunks: list[str], lang: str) -> str:
    """
    Generates a response using a strict system prompt to keep the AI on topic.
    """
    # Create the context by joining the document chunks
    context = "\n\n".join(chunks)

    # If ChromaDB found no relevant chunks, refuse immediately without calling the AI.
    if not context:
        logger.warning(f"No context found for query: '{user_message}'. Responding with fallback.")
        return get_fallback_message(lang)

    # Build the final prompt for the user message, tailored by language
    prompt_for_user = build_prompt(user_message, context, lang)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt_for_user}
            ],
            temperature=0.2,
            max_tokens=300
        )
        # Add a check here. If the AI still refuses, use our fallback.
        reply = response.choices[0].message.content.strip()
        if "sorry" in reply.lower() or "माफ़ कीजिए" in reply:
             logger.warning(f"AI chose to refuse despite context. Query: '{user_message}'")
             return get_fallback_message(lang)
        
        return reply

    except Exception as e:
        logger.error(f"Error calling OpenAI API: {e}", exc_info=True)
        return get_fallback_message(lang)

def build_prompt(user_message: str, context: str, lang: str) -> str:
    """
    Constructs the final prompt string for the AI based on the detected language.
    """
    if lang == "hi":
        return f"""RELEVANT INFO:\n---\n{context}\n---\n\nUSER'S QUESTION: {user_message}"""
    elif lang == "en":
        return f"""RELEVANT INFO:\n---\n{context}\n---\n\nUSER'S QUESTION: {user_message}"""
    else:  # Default to Hinglish for "hi-en" or "unknown"
        return f"""RELEVANT INFO:\n---\n{context}\n---\n\nUSER'S QUESTION: {user_message}\n\n(Important: Answer in simple Hinglish using Roman script)"""


def get_fallback_message(lang: str) -> str:
    """
    Returns the appropriate refusal message based on the detected language.
    """
    if lang == "hi":
        return "माफ़ कीजिए, यह जानकारी मेरे पास उपलब्ध नहीं है। कृपया किसी सरकारी योजना के बारे में ही पूछें।"
    elif lang == "en":
        return "I'm sorry, I don't have information on that topic. Please ask only about government schemes."
    else:  # Default to Hinglish for "hi-en" or "unknown"
        return "Sorry, iske baare mein jaankari available nahi hai. Kripya kisi sarkari yojana ke baare mein puchiye."

# --- Logging Setup ---
import logging
logger = logging.getLogger(__name__)

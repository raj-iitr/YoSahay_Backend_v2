# app/responder.py

import os
from openai import OpenAI

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- THIS IS THE NEW, REVISED SYSTEM PROMPT ---
SYSTEM_PROMPT = """You are YoSahay, an expert assistant that provides short, structured summaries of Indian government schemes using only the 'RELEVANT INFO' supplied.

Rules:

1) Language: Detect the user's language accurately (Hindi, English, or Hinglish) and reply strictly in that language. Never switch languages.

2) Use of RELEVANT INFO:
   - Use only the information from 'RELEVANT INFO' that is relevant to the query.
   - Rewrite everything in your own words.
   - Do not copy any sentence or phrase longer than 8 words from the source.
   - Remove all filler, intros, or redundant text.

3) Formatting rules:
   - Plain text only. Do not use any markdown symbols (#, *, **, -, >, `, []).
   - For section headings, write them on their own line, followed by a blank line. Example:  
     आवेदन स्थिति जांचने की प्रक्रिया:
   - Use the circular bullet character "•" followed by a space for all list points.
   - Do not use numbers for lists unless explicitly required in the 'RELEVANT INFO'. If required, still write them without symbols.

4) Style:
   - Keep answers concise.
   - Each section should have no more than 3–4 bullets.
   - Each bullet should be one short, clear sentence.
   - Avoid long paragraphs; use sections and bullets.

5) Structure:
   - For one scheme: Sections can be Overview, Benefits, Eligibility, How to apply (only if present).
   - For comparisons: One section per scheme + Key differences section.
   - For process or steps: Use circular bullets instead of numbers unless numbering is essential.

6) When no relevant info:
   - If 'RELEVANT INFO' is empty or unrelated, respond exactly with:
       Hindi: "माफ़ कीजिए, यह जानकारी मेरे पास उपलब्ध नहीं है। कृपया किसी सरकारी योजना के बारे में ही पूछें।"
       English: "I'm sorry, I don't have information on that topic. Please ask only about government schemes."
       Hinglish: "Sorry, iske baare mein jaankari available nahi hai. Kripya kisi sarkari yojana ke baare mein puchiye."

Tone: Neutral, factual, precise.

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

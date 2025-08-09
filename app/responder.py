# app/responder.py

import os
from openai import OpenAI

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- THIS IS THE NEW, REVISED SYSTEM PROMPT ---
SYSTEM_PROMPT = """You are YoSahay, an expert assistant that provides concise, structured summaries of Indian government schemes using only the 'RELEVANT INFO' supplied.

Rules:

1) Language: Detect the user's language accurately (Hindi, English, or Hinglish) and reply strictly in that language. Never switch languages.

2) Source usage:
   - Use only the 'RELEVANT INFO' provided.
   - Extract only the key facts relevant to the query.
   - Rewrite in your own words; never copy long phrases verbatim.
   - Remove all filler, introductions, and repetitive sentences.

3) Style and precision:
   - Be as short as possible while preserving accuracy.
   - Each section should have at most 3 concise bullet points.
   - Avoid explanations longer than one short sentence per bullet.
   - Use plain section headings followed by a line break.
   - Use the circular bullet "•" followed by a space for lists.

4) Formatting:
   - Do not use markdown characters (#, *, **, `, >) or emojis.
   - Structure output with:
       Section heading
       • Bullet point
       • Bullet point
   - Keep only sections that have relevant info from 'RELEVANT INFO'.

5) Structure:
   - For single-scheme queries: use sections like Overview, Benefits, Eligibility, How to apply (only if present in 'RELEVANT INFO').
   - For comparison queries: use one section per scheme, then a "Key differences" section.

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

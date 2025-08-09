# app/responder.py

import os
from openai import OpenAI

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- THIS IS THE NEW, REVISED SYSTEM PROMPT ---
SYSTEM_PROMPT = """
You are YoSahay, an assistant that produces concise WhatsApp-ready summaries of Indian government schemes using only the 'RELEVANT INFO' supplied.

Rules:

1) Language:
   - Detect the user's language (Hindi, English, or Hinglish) from the query and reply strictly in that language, including headings.

2) Source Use:
   - Use only the 'RELEVANT INFO' provided in the context.
   - Paraphrase all content; do not copy sentences longer than 8 words verbatim.
   - Exclude filler, disclaimers, or irrelevant info.

3) WhatsApp Formatting:
   - Headings must use Unicode bold characters so they appear bold on WhatsApp without asterisks (*).
     Example:
       Hindi: 𝗔𝗮𝘃𝗲𝗱𝗮𝗻 𝗦𝘁𝗵𝗶𝘁𝗶 𝗝𝗮𝗮𝗻𝗰𝗵:
       English: 𝗔𝗽𝗽𝗹𝗶𝗰𝗮𝘁𝗶𝗼𝗻 𝗦𝘁𝗮𝘁𝘂𝘀 𝗖𝗵𝗲𝗰𝗸:
   - No markdown symbols (#, >, `, etc.) or emojis.
   - No unnecessary blank lines between consecutive lines; keep it compact for mobile.
   - Use the circular bullet symbol "•" followed by a space for lists.
   - Each bullet point should be short (30–45 characters ideally) and of similar length for visual balance.

4) Structure:
   - Use headings only if relevant and present in the 'RELEVANT INFO'.
   - Headings must always be in the same language as the user’s query.
   - Keep headings short, clear, and appropriate to government schemes.
   - For comparisons, present each scheme separately, then add a final section with a heading meaning "Key Differences" in the user’s language.

5) Precision:
   - Maximum 3 bullet points per section unless more are absolutely needed.
   - Do not insert extra explanations before or after bullet lists.

6) When no relevant info:
   - Hindi: "माफ़ कीजिए, यह जानकारी मेरे पास उपलब्ध नहीं है। कृपया किसी सरकारी योजना के बारे में ही पूछें।"
   - English: "I'm sorry, I don't have information on that topic. Please ask only about government schemes."
   - Hinglish: "Sorry, iske baare mein jaankari available nahi hai. Kripya kisi sarkari yojana ke baare mein puchiye."

Tone:
   - Neutral, factual, and optimised for WhatsApp mobile readability.



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

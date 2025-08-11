# app/responder.py

import os
from openai import OpenAI

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- THIS IS THE NEW, REVISED SYSTEM PROMPT ---
SYSTEM_PROMPT = """
You are YoSahay, a helpful AI assistant. Your purpose is to provide clear, concise, and trustworthy WhatsApp-ready summaries of Indian government schemes for the citizens of Uttar Pradesh. You will be given 'RELEVANT INFO' for each query.

Your personality is:
• Sahayak (Helpful)
• Spasht (Clear)
• Bharosemand (Trustworthy)

---
**Core Rules**
---

1) **Language First:**
   • Detect the user's query language (Hindi, English, or Hinglish).
   • Your entire response, including headings, MUST be in that same language.

2) **Simplify and Summarize:**
   • Use ONLY the 'RELEVANT INFO' provided. Never add outside information.
   • Your primary task is to **simplify**. Rewrite complex government terms into simple, everyday words that a common person can easily understand.
   - Example: Instead of "beneficiary," use "laabharthi" or "jinko fayda milega."
   • Paraphrase everything. Do not copy-paste sentences. Keep the meaning but change the words.

3) **WhatsApp Formatting is CRITICAL:**
   • **Headings:** MUST use Unicode bold characters to appear bold on WhatsApp without asterisks. (e.g., English: 𝗙𝗮𝘆𝗱𝗲, Hindi: 𝗙𝗮𝘆𝗱𝗲).
   • **Lists:** Use the circular bullet symbol "•" followed by a single space.
   • **Compactness:** Do not use unnecessary blank lines. Keep the text compact for easy reading on a small mobile screen.
   • **Visuals:** You may use a single, relevant emoji at the start of the entire message to make it visually engaging (e.g., 🏡 for Awas Yojana, 🌾 for Fasal Bima). Do not use any other emojis or markdown symbols (#, *, >, `).

4) **Structure and Precision:**
   • **Headings:** Use short, simple headings only if they are relevant to the provided info. (e.g., "Kaise Apply Karein," "Documents," "Benefits").
   • **Bullet Points:**
     - Aim for 2-3 bullet points per section. Use more only if absolutely necessary.
     - Keep bullet points short and direct (ideally 30-50 characters).
     - Do not add any extra explanations or conversational text before or after the bulleted list. Get straight to the point.

5) **Handling "No Information":**
   • If the 'RELEVANT INFO' is empty or does not answer the user's question, reply with ONLY one of the following standard messages based on the query language:
   - **Hindi:** माफ़ कीजिए, यह जानकारी मेरे पास उपलब्ध नहीं है। कृपया किसी सरकारी योजना के बारे में ही पूछें।
   - **English:** I'm sorry, I don't have information on that topic. Please ask only about government schemes.
   - **Hinglish:** Sorry, iske baare mein jaankari available nahi hai. Kripya kisi sarkari yojana ke baare mein puchiye.

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

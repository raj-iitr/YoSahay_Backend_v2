# # app/responder.py

# import os
# from openai import OpenAI

# client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# def generate_response(user_message: str, chunks: list[str], lang: str) -> str:
#     if not chunks:
#         return fallback_message(lang)

#     prompt = build_prompt(user_message, chunks, lang)

#     response = client.chat.completions.create(
#         model="gpt-4o",
#         messages=[
#             {"role": "system", "content": "Answer only based on context below. Do not guess or hallucinate."},
#             {"role": "user", "content": prompt}
#         ],
#         temperature=0.4,
#         max_tokens=300
#     )

#     return response.choices[0].message.content

# def fallback_message(lang: str) -> str:
#     if lang == "hi":
#         return "माफ़ कीजिए, यह जानकारी मेरी डेटाबेस में उपलब्ध नहीं है। कृपया किसी सरकारी योजना से संबंधित प्रश्न पूछें।"
#     elif lang == "en":
#         return "Sorry, I couldn't find any matching information in my database. Please ask about a known government scheme."
#     else:
#         return "Sorry, I didn’t find anything related. Please ask about a Sarkari Yojana."

# def build_prompt(user_message: str, chunks: list[str], lang: str) -> str:
#     context = "\n\n".join(chunks)

#     if lang == "hi":
#         return f"""प्रासंगिक जानकारी:\n{context}\n\nप्रश्न: {user_message}\nउत्तर:"""
#     elif lang == "en":
#         return f"""Relevant Info:\n{context}\n\nQuestion: {user_message}\nAnswer:"""
#     else:  # Hinglish
#         return f"""Context:\n{context}\n\nUser asked: {user_message}\nReply in Hinglish:"""


# app/responder.py
# app/responder.py

import os
from openai import OpenAI

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- THIS IS THE NEW, REVISED SYSTEM PROMPT ---
SYSTEM_PROMPT = """You are 'Sarkari Yojana Sahayak,' an expert AI assistant. Your primary job is to extract and summarize information about Indian government schemes from the context provided.

Your rules are:
1.  Analyze the user's question and the 'RELEVANT INFO' provided below.
2.  If the 'RELEVANT INFO' contains information relevant to the user's question, answer the question by summarizing the information from the context.
3.  **Crucially, your entire response MUST be in the same language as the USER'S QUESTION (Hindi, English, or Hinglish).**
4.  If the 'RELEVANT INFO' is completely empty or clearly unrelated to the user's question, then and ONLY then should you refuse to answer.
5.  When you refuse, use one of these exact sentences:
    - Hindi: "माफ़ कीजिए, यह जानकारी मेरे पास उपलब्ध नहीं है। कृपया किसी सरकारी योजना के बारे में ही पूछें।"
    - English: "I'm sorry, I don't have information on that topic. Please ask only about government schemes."
    - Hinglish: "Sorry, iske baare mein jaankari available nahi hai. Kripya kisi sarkari yojana ke baare mein puchiye."
6.  Do not add any information that is not present in the 'RELEVANT INFO'.
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

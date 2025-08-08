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
SYSTEM_PROMPT = """You are 'YoSahay', an expert AI assistant specialized in providing accurate, clear, and well-presented summaries of Indian government schemes.

Your rules are:

1. **Language Matching**
   - First, detect the language of the user's question with high accuracy (Hindi, English, or Hinglish).
   - Your answer MUST be strictly in the same language as the user's question.
   - Under no circumstances should you switch to another language.

2. **Use of RELEVANT INFO**
   - Use only the 'RELEVANT INFO' provided below to answer the question.
   - If 'RELEVANT INFO' contains information relevant to the user's question, summarize it accurately.
   - Do NOT add any extra information not present in 'RELEVANT INFO'.

3. **Formatting & Presentation**
   - Your response must be professional, visually appealing, and easy to read.
   - Use:
       - Paragraphs for explanations.
       - Bullet points or numbered lists for key features, benefits, eligibility criteria, or steps.
       - Headings or subheadings when breaking down sections.
   - Maintain proper grammar, spelling, and sentence structure.
   - Do NOT use unnecessary symbols, decorative characters, or markdown-like syntax such as `**` unless explicitly provided in the 'RELEVANT INFO'.

4. **When No Relevant Info is Found**
   - If 'RELEVANT INFO' is empty or unrelated to the user's question, refuse to answer using exactly one of the following sentences:
       - Hindi: "माफ़ कीजिए, यह जानकारी मेरे पास उपलब्ध नहीं है। कृपया किसी सरकारी योजना के बारे में ही पूछें।"
       - English: "I'm sorry, I don't have information on that topic. Please ask only about government schemes."
       - Hinglish: "Sorry, iske baare mein jaankari available nahi hai. Kripya kisi sarkari yojana ke baare mein puchiye."

5. **Tone**
   - Be concise yet comprehensive.
   - Maintain an informative, neutral, and professional tone.

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
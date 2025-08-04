# app/responder.py

import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_response(user_message: str, chunks: list[str], lang: str) -> str:
    if not chunks:
        return fallback_message(lang)

    prompt = build_prompt(user_message, chunks, lang)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Answer only based on context below. Do not guess or hallucinate."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.4,
        max_tokens=300
    )

    return response.choices[0].message.content

def fallback_message(lang: str) -> str:
    if lang == "hi":
        return "माफ़ कीजिए, यह जानकारी मेरी डेटाबेस में उपलब्ध नहीं है। कृपया किसी सरकारी योजना से संबंधित प्रश्न पूछें।"
    elif lang == "en":
        return "Sorry, I couldn't find any matching information in my database. Please ask about a known government scheme."
    else:
        return "Sorry, I didn’t find anything related. Please ask about a Sarkari Yojana."

def build_prompt(user_message: str, chunks: list[str], lang: str) -> str:
    context = "\n\n".join(chunks)

    if lang == "hi":
        return f"""प्रासंगिक जानकारी:\n{context}\n\nप्रश्न: {user_message}\nउत्तर:"""
    elif lang == "en":
        return f"""Relevant Info:\n{context}\n\nQuestion: {user_message}\nAnswer:"""
    else:  # Hinglish
        return f"""Context:\n{context}\n\nUser asked: {user_message}\nReply in Hinglish:"""

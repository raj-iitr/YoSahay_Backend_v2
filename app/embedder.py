import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
EMBED_MODEL = "text-embedding-3-small"

def embed_text(text):
    response = client.embeddings.create(input=[text], model=EMBED_MODEL)
    return response.data[0].embedding

print("Embedder loaded successfully.")
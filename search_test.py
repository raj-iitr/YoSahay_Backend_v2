from app.embedder import embed_text
from app.db import search_chunks, collection
from app.detector import detect_lang
from app.responder import generate_response

def run_search(user_input: str):
    # Step 1: Detect language
    lang = detect_lang(user_input)

    # Step 2: Embed the query
    query_vector = embed_text(user_input)

    # Step 3: Retrieve top-k chunks from ChromaDB
    results = search_chunks(query_vector, lang=lang, top_k=3)
    chunks = results['documents'][0]

    # Step 4: Generate response with GPT-4o
    response = generate_response(user_input, chunks, lang)

    # Display
    print(f"\n🔍 Query: {user_input} [{lang}]")
    for i, (text, meta) in enumerate(zip(results['documents'][0], results['metadatas'][0])):
        print(f"\n📚 Chunk {i+1} ({meta['scheme_id']}):\n{text}")
    
    print("\n🤖 GPT-4o Response:\n")
    print(response)

if __name__ == "__main__":
    run_search("ग्रामीण युवा शहर क्यों जाते हैं?")
    # run_search("Raj bhai kaun hai?")

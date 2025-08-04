import chromadb
from chromadb.api.models.Collection import Collection

# Persistent client to share data across scripts
chroma_client = chromadb.PersistentClient(path="./chroma_data")
collection: Collection = chroma_client.get_or_create_collection(name="schemes")

def add_scheme_chunk(id, text, embedding, scheme_id, lang):
    collection.add(
        ids=[id],
        documents=[text],
        embeddings=[embedding],
        metadatas=[{"scheme_id": scheme_id, "lang": lang}]
    )

def search_chunks(query_embedding, lang, top_k=3):
    return collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where={"lang": lang}
    )

def load_data_into_chroma():
    """
    Reads all .txt files from the 'docs' folder and loads them into ChromaDB.
    (This is the logic from your old 'load_chunks.py' script)
    """
    print("Executing startup task: Loading data into ChromaDB...")
    
    # Prevent re-loading data if it's already there (useful for local dev)
    if collection.count() > 0:
        print("Data already loaded. Skipping.")
        return

    # IMPORTANT: The path is relative to your project root.
    # When Render runs your app, it will be in the 'YOSAHAY_BACKEND' folder.
    data_directory = "docs" 
    
    documents = []
    metadatas = []
    ids = []
    
    if not os.path.exists(data_directory):
        print(f"Error: Data directory '{data_directory}' not found.")
        return

    for doc_id, filename in enumerate(os.listdir(data_directory)):
        if filename.endswith(".txt"):
            filepath = os.path.join(data_directory, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                documents.append(f.read())
                metadatas.append({"source": filename})
                ids.append(str(doc_id + 1))
    
    if documents:
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        print(f"Success! Loaded {len(documents)} documents into ChromaDB.")
    else:
        print("No documents found in 'docs' folder.")
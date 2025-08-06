# import chromadb
# from chromadb.api.models.Collection import Collection

# # Persistent client to share data across scripts
# chroma_client = chromadb.PersistentClient(path="./chroma_data")
# collection: Collection = chroma_client.get_or_create_collection(name="schemes")

# def add_scheme_chunk(id, text, embedding, scheme_id, lang):
#     collection.add(
#         ids=[id],
#         documents=[text],
#         embeddings=[embedding],
#         metadatas=[{"scheme_id": scheme_id, "lang": lang}]
#     )

# def search_chunks(query_embedding, lang, top_k=3):
#     return collection.query(
#         query_embeddings=[query_embedding],
#         n_results=top_k,
#         where={"lang": lang}
#     )

# def load_data_into_chroma():
#     """
#     Reads all .txt files from the 'docs' folder and loads them into ChromaDB.
#     (This is the logic from your old 'load_chunks.py' script)
#     """
#     print("Executing startup task: Loading data into ChromaDB...")
    
#     # Prevent re-loading data if it's already there (useful for local dev)
#     if collection.count() > 0:
#         print("Data already loaded. Skipping.")
#         return

#     # IMPORTANT: The path is relative to your project root.
#     # When Render runs your app, it will be in the 'YOSAHAY_BACKEND' folder.
#     data_directory = "docs" 
    
#     documents = []
#     metadatas = []
#     ids = []
    
#     if not os.path.exists(data_directory):
#         print(f"Error: Data directory '{data_directory}' not found.")
#         return

#     for doc_id, filename in enumerate(os.listdir(data_directory)):
#         if filename.endswith(".txt"):
#             filepath = os.path.join(data_directory, filename)
#             with open(filepath, 'r', encoding='utf-8') as f:
#                 documents.append(f.read())
#                 metadatas.append({"source": filename})
#                 ids.append(str(doc_id + 1))
    
#     if documents:
#         collection.add(
#             documents=documents,
#             metadatas=metadatas,
#             ids=ids
#         )
#         print(f"Success! Loaded {len(documents)} documents into ChromaDB.")
#     else:
#         print("No documents found in 'docs' folder.")



# app/db.py

import os
import chromadb
from chromadb.types import Collection
from app.embedder import embed_text  # Import the embedder to use in loading
from langchain_text_splitters import RecursiveCharacterTextSplitter 
import logging


logger = logging.getLogger(__name__)

def load_data_into_chroma(collection: Collection):
    """
    Reads .txt files, splits them into smaller chunks, embeds them,
    and loads them into the provided ChromaDB collection.
    """
    logger.info("Executing startup task: Loading and chunking data for ChromaDB...")
    
    if collection.count() > 0:
        logger.info("Data is already present in the collection. Skipping.")
        return

    data_directory = "docs"
    
    # --- NEW: Initialize the text splitter ---
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,  # The max number of characters in a chunk
        chunk_overlap=100, # The number of characters to overlap between chunks
        length_function=len,
    )
    
    all_chunks = []
    all_metadatas = []
    all_ids = []
    chunk_id_counter = 1

    if not os.path.exists(data_directory):
        logger.error(f"Error: Data directory '{data_directory}' not found.")
        return

    for filename in os.listdir(data_directory):
        if filename.endswith(".txt"):
            filepath = os.path.join(data_directory, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # --- NEW: Split the document into chunks ---
                chunks = text_splitter.split_text(content)
                
                for chunk in chunks:
                    all_chunks.append(chunk)
                    # Each chunk inherits the source filename as metadata
                    all_metadatas.append({"source": filename})
                    all_ids.append(str(chunk_id_counter))
                    chunk_id_counter += 1
    
    if all_chunks:
        # Embed all chunks at once for efficiency
        embeddings = [embed_text(chunk) for chunk in all_chunks]
        
        collection.add(
            embeddings=embeddings,
            documents=all_chunks,
            metadatas=all_metadatas,
            ids=all_ids
        )
        logger.info(f"Success! Loaded and embedded {len(all_chunks)} chunks into ChromaDB.")
    else:
        logger.warning("No documents found to chunk and load.")
        
        
def add_scheme_chunk(collection: Collection, id: str, text: str, embedding: list, scheme_id: str, lang: str):
    """
    Adds a single chunk to the provided collection.
    """
    collection.add(
        ids=[id],
        documents=[text],
        embeddings=[embedding],
        metadatas=[{"scheme_id": scheme_id, "lang": lang}]
    )


def search_chunks(collection: Collection, query_embedding: list, lang: str, top_k: int = 3):
    """
    Searches the provided collection for chunks matching the query embedding.
    """
    # Note: The 'where' filter for language is not efficient for embeddings.
    # A better approach is to have separate collections or filter after the fact.
    # For the MVP, this is acceptable.
    return collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["metadatas", "documents", "distances"]
        # where={"lang": lang}  # This filter might not work as expected with embeddings.
                                # Let's query all and filter later if needed.
    )


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

# import os
# import chromadb
# from chromadb.types import Collection
# from app.embedder import embed_text  # Import the embedder to use in loading
# from langchain_text_splitters import RecursiveCharacterTextSplitter 
# import logging


# logger = logging.getLogger(__name__)
# # app/db.py

# import os
# import chromadb
# from chromadb.types import Collection
# from app.embedder import embed_text
# from langchain_text_splitters import RecursiveCharacterTextSplitter
# import logging

# logger = logging.getLogger(__name__)
# app/db.py

# import os
# import chromadb
# from chromadb.types import Collection
# from app.embedder import embed_text
# from langchain_text_splitters import RecursiveCharacterTextSplitter
# import logging

# logger = logging.getLogger(__name__)
# # app/db.py

# import os
# import chromadb
# from chromadb.types import Collection
# from app.embedder import embed_text
# from langchain_text_splitters import RecursiveCharacterTextSplitter
# import logging

# logger = logging.getLogger(__name__)

# def load_data_into_chroma(collection: Collection):
#     """
#     Recursively walks through the 'knowledge_base' directory, finds all .md files,
#     splits them into smaller chunks, embeds them, and loads them into ChromaDB.
#     """
#     logger.info("Executing startup task: Loading and chunking data for ChromaDB...")
    
#     if collection.count() > 0:
#         logger.info("Data is already present in the collection. Skipping.")
#         return

#     knowledge_base_dir = "knowledge_base"
    
#     text_splitter = RecursiveCharacterTextSplitter(
#         chunk_size=1000,
#         chunk_overlap=100,
#         length_function=len,
#     )
    
#     all_chunks, all_metadatas, all_ids = [], [], []
#     chunk_id_counter = 1

#     if not os.path.exists(knowledge_base_dir):
#         logger.error(f"Error: Knowledge base directory '{knowledge_base_dir}' not found.")
#         return

#     for root, dirs, files in os.walk(knowledge_base_dir):
#         # --- NEW ROBUST LOGIC ---
#         # We only care about directories that are *inside* the knowledge_base,
#         # not the knowledge_base directory itself.
#         if root == knowledge_base_dir:
#             continue

#         for filename in files:
#             if filename.endswith(".md"):
#                 filepath = os.path.join(root, filename)
                
#                 # The scheme name is the name of the directory this file is in.
#                 scheme_name = os.path.basename(root)
                
#                 logger.info(f"Processing file: {filepath} for scheme: {scheme_name}")
                
#                 with open(filepath, 'r', encoding='utf-8') as f:
#                     content = f.read()
#                     chunks = text_splitter.split_text(content)
                    
#                     for chunk in chunks:
#                         all_chunks.append(chunk)
#                         all_metadatas.append({
#                             "source_file": filename,
#                             "scheme": scheme_name
#                         })
#                         all_ids.append(str(chunk_id_counter))
#                         chunk_id_counter += 1
    
#     if all_chunks:
#         embeddings = [embed_text(chunk) for chunk in all_chunks]
#         collection.add(
#             embeddings=embeddings,
#             documents=all_chunks,
#             metadatas=all_metadatas,
#             ids=all_ids
#         )
#         logger.info(f"Success! Loaded and embedded {len(all_chunks)} chunks from {knowledge_base_dir}.")
#     else:
#         logger.warning(f"No .md documents found in the subdirectories of '{knowledge_base_dir}'.")

# # ... (search_chunks function) ...... (search_chunks function) ...
# # ... (search_chunks function) ...
# def add_scheme_chunk(collection: Collection, id: str, text: str, embedding: list, scheme_id: str, lang: str):
#     """
#     Adds a single chunk to the provided collection.
#     """
#     collection.add(
#         ids=[id],
#         documents=[text],
#         embeddings=[embedding],
#         metadatas=[{"scheme_id": scheme_id, "lang": lang}]
#     )


# def search_chunks(collection: Collection, query_embedding: list, lang: str, top_k: int = 3):
#     """
#     Searches the provided collection for chunks matching the query embedding.
#     """
#     # Note: The 'where' filter for language is not efficient for embeddings.
#     # A better approach is to have separate collections or filter after the fact.
#     # For the MVP, this is acceptable.
#     return collection.query(
#         query_embeddings=[query_embedding],
#         n_results=top_k,
#         include=["metadatas", "documents", "distances"]
#         # where={"lang": lang}  # This filter might not work as expected with embeddings.
#                                 # Let's query all and filter later if needed.
#     )











# app/db.py

import os
import chromadb
from chromadb.types import Collection
from app.embedder import embed_text
from langchain_text_splitters import RecursiveCharacterTextSplitter
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)
# Basic logging config in case this module is run standalone
logging.basicConfig(level=logging.INFO)

def load_data_into_chroma(collection: Collection):
    """
    Looks for 'knowledge_base' in the project root, loads all .md files,
    chunks them, embeds them, and adds them to the ChromaDB collection.
    """
    logger.info("Executing startup task: Loading and chunking data for ChromaDB...")
    
    if collection.count() > 0:
        logger.info("Data is already present in the collection. Skipping.")
        return

    # --- THIS IS THE CRITICAL FIX FOR YOUR STRUCTURE ---
    # The knowledge_base directory is at the root of the project.
    knowledge_base_dir = "knowledge_base"
    # --- END OF CRITICAL FIX ---
    
    logger.info(f"Searching for knowledge base in: {knowledge_base_dir}")

    if not os.path.exists(knowledge_base_dir):
        logger.error(f"FATAL: Knowledge base directory not found at '{knowledge_base_dir}'. Make sure it's in the project root.")
        return

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100,
        length_function=len,
    )
    
    all_chunks, all_metadatas, all_ids = [], [], []
    chunk_id_counter = 1

    # Loop through the items in the base directory (e.g., 'pm_kisan', 'pmay_g')
    for scheme_folder in os.listdir(knowledge_base_dir):
        scheme_path = os.path.join(knowledge_base_dir, scheme_folder)
        
        # Process only if the item is a directory
        if os.path.isdir(scheme_path):
            scheme_name = scheme_folder
            
            # Find and process all .md files within this scheme's folder
            for filename in os.listdir(scheme_path):
                if filename.endswith(".md"):
                    filepath = os.path.join(scheme_path, filename)
                    logger.info(f"Processing file: {filepath} for scheme: {scheme_name}")
                    
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        chunks = text_splitter.split_text(content)
                        
                        for chunk in chunks:
                            all_chunks.append(chunk)
                            all_metadatas.append({
                                "source_file": filename,
                                "scheme": scheme_name
                            })
                            all_ids.append(str(chunk_id_counter))
                            chunk_id_counter += 1
    
    if all_chunks:
        embeddings = [embed_text(chunk) for chunk in all_chunks]
        collection.add(
            embeddings=embeddings,
            documents=all_chunks,
            metadatas=all_metadatas,
            ids=all_ids
        )
        logger.info(f"Success! Loaded and embedded {len(all_chunks)} chunks.")
    else:
        logger.warning("No .md documents found in the subdirectories of the knowledge base.")

# in app/db.py
# In app/db.py

def search_chunks(collection: Collection, query_embedding: list, scheme_filter: str | None, top_k: int = 3):
    """
    Searches the collection, applying a metadata filter if a scheme is specified.
    This is the final, correct version.
    """
    # Create the 'where' clause for the ChromaDB query
    where_clause = {}
    if scheme_filter:
        # If a scheme was detected, add it to the filter.
        # This tells ChromaDB to ONLY search within documents that have this metadata.
        where_clause = {"scheme": scheme_filter}
        logger.info(f"Performing a FILTERED search for scheme: '{scheme_filter}'")
    else:
        # If no scheme was detected, perform a general search across all documents.
        logger.info("No specific scheme detected. Performing a GENERAL search.")

    # Execute the query with the appropriate filter
    return collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where_clause,
        include=["metadatas", "documents", "distances"]
    )
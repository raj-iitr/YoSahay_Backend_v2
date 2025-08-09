# app/db.py

import os
import chromadb
from chromadb.types import Collection
from app.embedder import embed_text
from langchain_text_splitters import RecursiveCharacterTextSplitter
import logging
import time

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def load_data_into_chroma(collection: Collection):
    """
    Loads data in batches from the 'knowledge_base' directory in the project root.
    """
    logger.info("Executing startup task: Loading and chunking data for ChromaDB...")
    
    if collection.count() > 0:
        logger.info("Data is already present in the collection. Skipping.")
        return

    knowledge_base_dir = "knowledge_base"
    all_chunks, all_metadatas, all_ids = [], [], []
    chunk_id_counter = 1

    if not os.path.exists(knowledge_base_dir):
        logger.error(f"FATAL: Knowledge base directory not found at '{knowledge_base_dir}'.")
        return

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    
    for scheme_folder in os.listdir(knowledge_base_dir):
        scheme_path = os.path.join(knowledge_base_dir, scheme_folder)
        if os.path.isdir(scheme_path):
            for filename in os.listdir(scheme_path):
                if filename.endswith(".md"):
                    filepath = os.path.join(scheme_path, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        chunks = text_splitter.split_text(content)
                        for chunk in chunks:
                            all_chunks.append(chunk)
                            all_metadatas.append({"source_file": filename, "scheme": scheme_folder})
                            all_ids.append(str(chunk_id_counter))
                            chunk_id_counter += 1

    if not all_chunks:
        logger.warning("No .md documents found to load.")
        return
        
    logger.info(f"Found a total of {len(all_chunks)} chunks to process.")

    batch_size = 50
    for i in range(0, len(all_chunks), batch_size):
        batch_chunks = all_chunks[i:i+batch_size]
        batch_metadatas = all_metadatas[i:i+batch_size]
        batch_ids = all_ids[i:i+batch_size]
        
        logger.info(f"Processing batch {i//batch_size + 1}...")
        
        try:
            batch_embeddings = [embed_text(chunk) for chunk in batch_chunks]
            collection.add(
                embeddings=batch_embeddings,
                documents=batch_chunks,
                metadatas=batch_metadatas,
                ids=batch_ids
            )
            time.sleep(1) 
        except Exception as e:
            logger.error(f"Failed to process batch starting at index {i}. Error: {e}")
            continue 

    logger.info(f"Finished loading all {len(all_chunks)} chunks into ChromaDB.")


def search_chunks(collection: Collection, query_embedding: list, scheme_filter: str | None, top_k: int = 3):
    """
    This is the guaranteed working search function for recent ChromaDB versions.
    It conditionally builds the query arguments to avoid the empty 'where' clause error.
    """
    # 1. Start with the arguments that are always present.
    query_args = {
        "query_embeddings": [query_embedding],
        "n_results": top_k,
        "include": ["metadatas", "documents", "distances"]
    }

    # 2. Conditionally add the 'where' clause ONLY if a filter is provided.
    if scheme_filter:
        query_args["where"] = {"scheme": scheme_filter}
        logger.info(f"Performing a FILTERED search for scheme: '{scheme_filter}'")
    else:
        logger.info("No specific scheme detected. Performing a GENERAL search.")

    # 3. Execute the query using dictionary unpacking.
    # This robustly handles both filtered and unfiltered cases.
    return collection.query(**query_args)
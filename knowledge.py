# knowledge_base_test.py

import chromadb
from app.db import load_data_into_chroma
from app.embedder import embed_text # Needed by the loader

# --- Setup an in-memory test database ---
print("Setting up a temporary in-memory ChromaDB client for testing...")
client = chromadb.Client()
test_collection = client.get_or_create_collection(name="test_schemes")

# --- Run the data loading function ---
# This is the function we want to test
load_data_into_chroma(test_collection)

print("\n" + "="*50)
print("--- TEST RESULTS ---")

# --- Verification Step 1: Check the total number of chunks ---
total_chunks = test_collection.count()
print(f"\n[VERIFICATION 1] Total Chunks Loaded: {total_chunks}")
if total_chunks > 0:
    print("  -> PASSED: The loader found and chunked the documents.")
else:
    print("  -> FAILED: No chunks were loaded. Check the 'knowledge_base' directory and file paths.")

# --- Verification Step 2: Inspect the metadata of the first few chunks ---
if total_chunks > 0:
    print("\n[VERIFICATION 2] Inspecting Metadata of the first 3 chunks...")
    retrieved_items = test_collection.get(limit=3, include=["metadatas"])
    
    for i, metadata in enumerate(retrieved_items['metadatas']):
        print(f"  -> Chunk {i+1} Metadata: {metadata}")
        if 'scheme' in metadata and 'source_file' in metadata:
            print("    -> PASSED: Metadata contains 'scheme' and 'source_file' keys.")
        else:
            print("    -> FAILED: Metadata is missing required keys.")

print("\n" + "="*50)
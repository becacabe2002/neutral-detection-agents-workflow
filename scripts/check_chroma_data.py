import chromadb
import sys
import os

# Ensure we can import from src if needed, though HttpClient is enough
sys.path.append(os.getcwd())

def check_chroma():
    try:
        # Connect to the running container from the host
        # Based on .env.example/config.py, it should be localhost:8000
        client = chromadb.HttpClient(host='chromadb', port=8000)
        
        print("Connected to ChromaDB.")
        
        collections = client.list_collections()
        print(f"Collections found: {[c.name for c in collections]}")
        
        if not collections:
            print("No collections exist.")
            return

        for col_name in [c.name for c in collections]:
            collection = client.get_collection(name=col_name)
            count = collection.count()
            print(f"Collection '{col_name}' count: {count}")
            
            if count > 0:
                results = collection.peek(limit=5)
                print(f"Sample data from '{col_name}':")
                for i in range(len(results['ids'])):
                    print(f"  ID: {results['ids'][i]}")
                    print(f"  Metadata: {results['metadatas'][i]}")
                    print(f"  Document excerpt: {results['documents'][i][:100]}...")
                    print("-" * 20)

    except Exception as e:
        print(f"Error connecting to ChromaDB: {e}")

if __name__ == "__main__":
    check_chroma()

import json
from qdrant_client import QdrantClient
from .utils import ( get_text_chunks, get_embedding, 
                    create_qdrant_collection, add_points_qdrant)
import hashlib


client = QdrantClient("http://localhost:6333") 
def collection_is_empty():
    try:
        collections = client.get_collections().collections
        return len(collections) == 0
    except Exception as e:
        print("Cannot check collection:", e)
        return True 
    
def url_to_collection_name(url):
    # hash URL để tạo tên collection an toàn
    h = hashlib.md5(url.encode("utf-8")).hexdigest()
    return f"collection_{h}"

def build_data_once():
    if collection_is_empty():
        print("Qdrant is empty. Building data from output.json...")

        with open("data/output.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data:
            try:
                collection_name = url_to_collection_name(item['url'])
                create_qdrant_collection(collection_name)
                content_chunks = get_text_chunks(item['text'])
                embeddings_points = get_embedding(content_chunks, item)
                add_points_qdrant(collection_name, embeddings_points)
            except Exception as e:
                print(f'Lỗi: {e}')
                raise Exception(f"Error when saving into qdrant: {e}")

        print("Build data successfully!.")
    else:
        print("Qdrant already has data; skipping rebuild.")

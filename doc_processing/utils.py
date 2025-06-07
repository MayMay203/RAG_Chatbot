from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from qdrant_client import QdrantClient,models
from qdrant_client.http.models import PointStruct
from sentence_transformers import SentenceTransformer
import uuid
import os
import google.generativeai as genai
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
import google.generativeai as genaiModel


model = SentenceTransformer('all-MiniLM-L6-v2')
genaiModel.configure(api_key=os.getenv("GEMINI_API_KEY"))
gemini_model = genaiModel.GenerativeModel("gemini-2.0-flash")
connection = QdrantClient("localhost", port=6333)    

def get_text_chunks(text):
  text_splitter = CharacterTextSplitter(
    separator="\n", # Separate the text at the line down
    chunk_size=1000, # max length
    chunk_overlap=200, # overlap
    length_function=len) # calc length
  chunks = text_splitter.split_text(text)
  return chunks


# Create embedding with vector 384
def get_embedding(text_chunks, material):
    points = []
    embeddings = model.encode(text_chunks)  # Nhận list các vector embedding
    typeMap = {
        1: 'file',
        2: 'content',
        3: 'url',
    }

    material_type_id = material.get('materialType', {}).get('id') or 3
    material_name = material.get('url') if material_type_id == 3 else material.get('name')

    #  Mỗi chunk ứng với enbedding tương ứng
    for chunk, emb in zip(text_chunks, embeddings):
        points.append(PointStruct(
            id=str(uuid.uuid4()),
            vector=emb.tolist(),  # Chuyển về list nếu cần lưu
            payload={
              "text": chunk,
              "materialName": material_name,
              "materialType": typeMap[material_type_id] or 'url',  # basic data
              "accessType": material.get('accessType') or 'public',
              "active": True
            }
        ))

    return points


def create_qdrant_collection(collection_name):
    connection.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE),
    )
    info = connection.get_collection(collection_name=collection_name)
    return info


def add_points_qdrant(collection_name, points):
    connection.upsert(collection_name=collection_name, points=points)
    return True

# Crawl content url
async def fetch_url_content(url: str) -> str:
    browser_config = BrowserConfig()
    run_config = CrawlerRunConfig()
    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url=url, config=run_config)
        if result.success and result.markdown:
            return result.markdown.raw_markdown
        else:
            raise Exception(f"Không thể crawl URL: {result.status_code} - {result.error_message}")

# Send prompt to gemini to get result
def gemini_generate_content(prompt: str) -> str:
    response = gemini_model.generate_content(prompt)
    return response.text
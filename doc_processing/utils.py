from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from qdrant_client import QdrantClient,models
from qdrant_client.http.models import PointStruct
from sentence_transformers import SentenceTransformer
import uuid
import os
import google.generativeai as genai
import asyncio
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
import time

# def unique_collection_name(name):
#     timestamp = int(time.time() * 1000)  
#     safe_name = name.replace(" ", "_") 
#     return f"{safe_name}_{timestamp}"

def get_text_chunks(text):
  text_splitter = CharacterTextSplitter(
    separator="\n", # tách văn bản tại dấu xuống dòng
    chunk_size=1000, # độ dài tối đa
    chunk_overlap=200, # độ chồng lắp
    length_function=len) #hàm tính độ dài
  chunks = text_splitter.split_text(text)
  return chunks


# Custom
# Load model local -> chuyển text thành vector 384 chiều
model = SentenceTransformer('all-MiniLM-L6-v2')
gemini_api_key = os.getenv("GEMINI_API_KEY")
def get_embedding(text_chunks, material):
    points = []
    embeddings = model.encode(text_chunks)  # Nhận list các vector embedding
    typeMap = {
        1: 'file',
        2: 'content',
        3: 'url',
    }

    material_type_id = material.get('materialType', {}).get('id')
    material_name = material.get('url') if material_type_id == 3 else material.get('name')

    #  Mỗi chunk ứng với enbedding tương ứng
    for chunk, emb in zip(text_chunks, embeddings):
        points.append(PointStruct(
            id=str(uuid.uuid4()),
            vector=emb.tolist(),  # Chuyển về list nếu cần lưu
            payload={
              "text": chunk,
              "materialName": material_name,
              "materialType": typeMap[material.get('materialType').get('id')],
              "accessType": material.get('accessType') or 'public',
              "active": True
            }
        ))

    return points


def create_qdrant_collection(collection_name):
    connection = QdrantClient("localhost", port=6333)    
    connection.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE),
    )
    info = connection.get_collection(collection_name=collection_name)
    
    return info


def add_points_qdrant(collection_name, points):
    
    connection = QdrantClient("localhost", port=6333)
    connection.upsert(collection_name=collection_name, points=points)
    
    return True

# Hàm: Crawl nội dung từ URL
async def fetch_url_content(url: str) -> str:
    browser_config = BrowserConfig()
    run_config = CrawlerRunConfig()
    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url=url, config=run_config)
        if result.success and result.markdown:
            return result.markdown.raw_markdown
        else:
            raise Exception(f"Không thể crawl URL: {result.status_code} - {result.error_message}")

# Hàm: Gửi prompt tới Gemini và nhận kết quả
def gemini_generate_content(prompt: str) -> str:
    genai.configure(api_key=gemini_api_key) 
    model = genai.GenerativeModel(model_name="gemini-2.0-flash")
    response = model.generate_content(prompt)
    return response.text
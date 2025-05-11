from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from qdrant_client import QdrantClient,models
from qdrant_client.http.models import PointStruct
from sentence_transformers import SentenceTransformer
import uuid

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
def get_embedding(text_chunks, material):
    points = []
    embeddings = model.encode(text_chunks)  # Nhận list các vector embedding

    #  Mỗi chunk ứng với enbedding tương ứng
    for chunk, emb in zip(text_chunks, embeddings):
        points.append(PointStruct(
            id=str(uuid.uuid4()),
            vector=emb.tolist(),  # Chuyển về list nếu cần lưu
            payload={
              "text": chunk,
              "materialId": material['id'],
              "materialType": material['materialType'],
              "accessType": material['accessType'],
              "knowledgeStore": material['knowledgeStore']
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


# def get_embedding(text_chunks, model_id="text-embedding-ada-002"):
#     points = []
#     for idx, chunk in enumerate(text_chunks):
#         response = open_ai.Embedding.create(
#             input=chunk,
#             model=model_id
#         )
#         embeddings = response['data'][0]['embedding']
#         points.append(PointStruct(id=str(uuid.uuid4()), vector=embeddings,
#                                    payload={"text": chunk}))

#     return points
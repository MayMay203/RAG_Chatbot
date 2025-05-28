import io
import os
import requests
from rest_framework.response import Response
from rest_framework.views import APIView
from PyPDF2 import PdfReader
from rest_framework.permissions import AllowAny
import pandas as pd
from docx import Document
import docx2txt 
from PIL import Image
import re
import cv2
import numpy as np
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'D:\Tesseract-OCR\tesseract.exe'
from .utils import ( get_text_chunks, get_embedding, 
                    create_qdrant_collection, add_points_qdrant, fetch_url_content, gemini_generate_content)
from rest_framework.exceptions import APIException, ValidationError
from qdrant_client import QdrantClient
import asyncio

qdrant_client = QdrantClient("localhost", port=6333)

class DocumentDeleteActionView(APIView):
    permission_classes = [AllowAny]
    def delete(self, request):
        collection_name = request.data.get('collection_name')

        if not collection_name:
            raise APIException(f"Collection_name is required!")

        client = QdrantClient(host="localhost", port=6333)

        try:
            client.delete_collection(collection_name=collection_name)
            return Response({'message': f'Collection "{collection_name}" deleted successfully'}, status=200)
        except Exception as e:
            raise APIException(f"Delete collection not successfully")
        
class DocumentProcessingView(APIView):
    permission_classes=[AllowAny]
    def post(self, request):
        materials = request.data.get("materials", [])
        for material in materials:
            material_type_id = material.get("materialType").get("id")
            name = material.get("name")
            collectionName = name + "_" + str(material['id'])
            existing_collections = [c.name for c in qdrant_client.get_collections().collections]

            if collectionName in existing_collections:
                print(f"Skip this collection: '{collectionName}' existed.")
                continue

            content = ''

            if material_type_id == 1: #type file
                data = material.get('url')
                file_id = data.split("d/")[-1].split("/")[0]
                download_url = f"https://drive.google.com/uc?id={file_id}&export=download"
                response = requests.get(download_url)
                
                if response.status_code == 200:
                    content_type = response.headers.get("Content-Type", "")
                    ext = os.path.splitext(name or "")[1].lower()

                    try:
                        if "pdf" in content_type or ext == ".pdf":
                            file_data = io.BytesIO(response.content)
                            reader = PdfReader(file_data)
                            text_list = [page.extract_text() for page in reader.pages if page.extract_text()]
                            text = "\n".join(text_list)
                            if text:
                                content = text
                            else:
                                raise APIException("Can not extract content from PDF.")
                        
                        elif "msword" in content_type or ext == ".doc":
                            with open("temp.doc", "wb") as f:
                                f.write(response.content)
                            content = docx2txt.process("temp.doc")

                        elif "officedocument.wordprocessingml.document" in content_type or ext == ".docx":
                            file_data = io.BytesIO(response.content)
                            doc = Document(file_data)
                            content = "\n".join(para.text for para in doc.paragraphs)
                        elif "text/plain" in content_type or ext == ".txt":
                            content = response.content.decode("utf-8", errors="ignore")
                        elif "excel" in content_type or ext in [".xls", ".xlsx", ".xlsm", ".csv"]:
                            file_data = io.BytesIO(response.content)
                            if ext in [".xlsx", ".xlsm"]:
                                df = pd.read_excel(file_data, engine='openpyxl', dtype=str)
                            elif ext == ".xls":
                                df = pd.read_excel(file_data, engine='xlrd', dtype=str)
                            elif ext == ".csv":
                                df = pd.read_csv(file_data, dtype=str)
                            content = df.to_string(index=False)

                        elif "image" in content_type or ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"]:
                            # Mở ảnh và tiền xử lý
                            image = Image.open(io.BytesIO(response.content))
                            custom_config = r'--psm 6 -c preserve_interword_spaces=1'

                            # Chuyển ảnh sang dạng xám
                            gray_image = cv2.cvtColor(np.array(image), cv2.COLOR_BGR2GRAY)

                            # Áp dụng ngưỡng (thresholding)
                            _, thresholded_image = cv2.threshold(gray_image, 150, 255, cv2.THRESH_BINARY)

                            # Tạo ảnh sau khi ngưỡng hóa
                            processed_image = Image.fromarray(thresholded_image)

                            # Nhận diện văn bản từ ảnh đã qua xử lý
                            text = pytesseract.image_to_string(processed_image, config=custom_config)

                            # Làm sạch văn bản: chỉ giữ lại các ký tự chữ, số và dấu cách
                            cleaned_text = re.sub(r'[^a-zA-Z0-9\s]', '', text)

                            # Gán lại nội dung
                            content = cleaned_text

                        else:
                            raise ValidationError("File format is not determined or not supported.")

                    except Exception as e:
                        raise APIException(f"Error when handling file '{name}': {str(e)}")

                else:
                    raise APIException(f"Cannot download file from this: {data} (Status: {response.status_code})")

            elif material_type_id == 3:   # type url
                try:
                    data = material.get('url')
                    raw_content = asyncio.run(fetch_url_content(data))
                    prompt = f'Bạn hãy đọc đoạn văn bản dưới đây và tóm tắt lại nội dung chính, chỉ lấy phần văn bản chính, bỏ qua tất cả các link, địa chỉ URL, hình ảnh, biểu tượng, quảng cáo, các phần điều hướng hoặc nội dung không liên quan khác. Chỉ trả về phần nội dung văn bản thuần túy. Nội dung phải đầy đủ các đoạn văn bản. Đoạn văn bản: "{raw_content}"'

                    content = gemini_generate_content(prompt)
                except Exception as e:
                    print(e)
                    raise APIException(f"Error when fetch URL {data}: {e}")

            elif material_type_id == 2: # type content
                content = material.get('text')

            else:
                raise APIException(f"The type of document is not supported")
            
            # Xử lí content nhận được của các loại tài liệu
            try:
                create_qdrant_collection(collectionName)
                content_chunks = get_text_chunks(content)
                embeddings_points = get_embedding(content_chunks, material)
                add_points_qdrant(collectionName, embeddings_points)
            except Exception as e:
                print(f'Lỗi: {e}')
                raise APIException(f"Error when saved to QDRant: {e}")

        return Response({"message": "Processed materials"}, status=200)
    
class DocumentActivationView(APIView):
    permission_classes = [AllowAny]

    # toggle active material
    def post(self, request):
        materials = request.data.get("materials") 
        
        if not materials or not isinstance(materials, list):
            raise APIException("Missing or invalid 'materials' list")

        results = []

        for mat in materials:
            material_id = mat.get("material_id")
            material_name = mat.get("material_name")
            new_status = mat.get("new_status")

            if material_id is None or material_name is None or new_status is None:
                results.append({
                    "material_id": material_id,
                    "material_name": material_name,
                    "error": "Missing material_id, material_name, or new_status"
                })
                continue

            collection_name = f"{material_name}_{material_id}"
            try:
                scroll_result = qdrant_client.scroll(
                    collection_name=collection_name,
                    with_payload=True,
                    limit=10000,
                )
                point_ids = [point.id for point in scroll_result[0]]
                if not point_ids:
                    results.append({
                        "material_id": material_id,
                        "material_name": material_name,
                        "error": "No vectors found in collection"
                    })
                    continue

                qdrant_client.set_payload(
                    collection_name=collection_name,
                    payload={"active": new_status},
                    points=point_ids
                )

                results.append({
                    "material_id": material_id,
                    "material_name": material_name,
                    "updated_vectors": len(point_ids),
                    "new_status": new_status
                })

            except Exception as e:
                raise APIException(f"Failed to toggle status for material: {e}")

        return Response({"results": results}, status=200)

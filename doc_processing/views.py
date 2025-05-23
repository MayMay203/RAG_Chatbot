import io
import os
import requests
from rest_framework.response import Response
from rest_framework.views import APIView
from PyPDF2 import PdfReader
from rest_framework.permissions import AllowAny
import mimetypes
import pandas as pd
from docx import Document
import zipfile
import docx2txt 
from PIL import Image
import re
import string
import cv2
import numpy as np
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'D:\Tesseract-OCR\tesseract.exe'
from .utils import ( get_text_chunks, get_embedding, 
                    create_qdrant_collection, add_points_qdrant, unique_collection_name)
from rest_framework.exceptions import APIException, ValidationError

class DocumentProcessingView(APIView):
    permission_classes=[AllowAny]
    def post(self, request):
        materials = request.data.get("materials", [])
        for material in materials:
            material_type = material.get("materialType")
            data = material.get("data")
            name = material.get("name")
            content = ''

            if material_type == "file":
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
                                raise APIException("Không thể trích xuất nội dung từ PDF.")
                        
                        elif "msword" in content_type or ext == ".doc":
                            with open("temp.doc", "wb") as f:
                                f.write(response.content)
                            content = docx2txt.process("temp.doc")

                        elif "officedocument.wordprocessingml.document" in content_type or ext == ".docx":
                            file_data = io.BytesIO(response.content)
                            doc = Document(file_data)
                            content = "\n".join(para.text for para in doc.paragraphs)

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
                            raise ValidationError("Không xác định được định dạng file hoặc chưa hỗ trợ đọc.")

                    except Exception as e:
                        raise APIException(f"Lỗi khi xử lý file '{name}': {str(e)}")

                else:
                    raise APIException(f"Không thể tải file từ URL: {data} (Status: {response.status_code})")

            elif material_type == "url":
                try:
                    response = requests.get(data)
                    content = response.text
                except Exception as e:
                    raise APIException(f"Lỗi khi fetch URL {data}: {e}")

            elif material_type == "content":
                content = data

            else:
                raise ValidationError(f"Loại tài liệu không được hỗ trợ: {material_type}")
            
            # Xử lí content nhận được của tất cả loại tài liệu
            try:
                collectionName = unique_collection_name(name)
                create_qdrant_collection(collectionName)
                content_chunks = get_text_chunks(content)
                embeddings_points = get_embedding(content_chunks, material)
                add_points_qdrant(collectionName, embeddings_points)
            except Exception as e:
                print(f'Lỗi: {e}')
                raise APIException(f"Lỗi khi lưu vào qdrant: {e}")

        return Response({"message": "Processed materials"}, status=200)
    


# from .utils import (read_data_from_pdf, get_text_chunks, get_embedding,
#                     create_qdrant_collection, add_points_qdrant)
# from rest_framework import status
# import io
# import os
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework.permissions import AllowAny
# import requests
# import mimetypes

# class ProcessDocumentView(APIView):
#     permission_classes = [AllowAny]
#     # def post(self, request):
#     #     materials = request.data.get("materials", [])
#     #     print('materials', materials)

#     #     # all_pdf = [
#     #     #         'documents/Hatang-TiengViet.pdf',
#     #     #         'documents/Viet-Education2024.pdf',
#     #     #         'documents/Viet-HitechPark2024.pdf',
#     #     #         'documents/Viet-Logistics2024.pdf',
#     #     #         'documents/Viet-Trade2024.pdf'
#     #     #         ]
        
#     #     # for pdf_path in all_pdf:
#     #     #     pdf_name = pdf_path.split('/')[-1].split('.')[0]

#     #     #     try:
#     #     #         print("Creating Collection for: ", pdf_name)
#     #     #         create_qdrant_collection(pdf_name)
#     #     #     except Exception as e:
#     #     #         return Response({"message": str(e)},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
#     #     #     pdf_content = read_data_from_pdf(pdf_path)
#     #     #     content_chunks = get_text_chunks(pdf_content)
            
#     #     #     print("Creating Embeddins for: ", pdf_name)
#     #     #     embaddings_points = get_embedding(content_chunks)
            
#     #     #     print("Adding Embeddins for: ", pdf_name)
#     #     #     add_points_qdrant(pdf_name, embaddings_points)
                            
#     #     return Response({"message": "Process documents successfully!"},
#     #                      status=status.HTTP_200_OK)

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
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'D:\Tesseract-OCR\tesseract.exe'

class DocumentProcessingView(APIView):
    permission_classes=[AllowAny]
    def post(self, request):
        materials = request.data.get("materials", [])
        for material in materials:
            material_type = material.get("materialType")
            data = material.get("data")
            name = material.get("name")

            if material_type == "file":
                file_id = data.split("d/")[-1].split("/")[0]
                download_url = f"https://drive.google.com/uc?id={file_id}&export=download"
                print(download_url)
                response = requests.get(download_url)
                
                if response.status_code == 200:
                    # File nhị phân hoặc không xác định: Content-Type: application/octet-stream
                    content_type = response.headers.get("Content-Type", "")

                    # Tách đường dẫn thành 2 phần, lấy phần mở rộng
                    ext = os.path.splitext(name or "")[1].lower()  

                    print(f"[INFO] Content-Type: {content_type}")
                    print(f"[INFO] File Extension from name: {ext}")

                    # Kiểm tra loại tệp và cố gắng đọc nội dung phù hợp
                    # PDF
                    if "pdf" in content_type or ext == ".pdf":
                        try:
                            file_data = io.BytesIO(response.content)
                            reader = PdfReader(file_data)

                            text_list = []
                            for page in reader.pages:
                                page_text = page.extract_text()
                                if page_text:  # nếu trang có văn bản
                                    text_list.append(page_text)
                            text = "\n".join(text_list)
                            
                            if text:
                                print(f"[PDF Content] {text[:200]}...") 
                            else:
                                print("[ERROR] Không thể trích xuất nội dung từ PDF.")
                        except Exception as e:
                            print(f"[ERROR] Lỗi khi xử lý PDF: {e}")
                    # DOC
                    elif "msword" in content_type or ext == ".doc":
                        with open("temp.doc", "wb") as f:
                            f.write(response.content)
                        text = docx2txt.process("temp.doc")
                        print(f"[DOC Content] {text[:200]}...")  # In 200 ký tự đầu
                    # DOCX
                    elif "officedocument.wordprocessingml.document" in content_type or ext == ".docx":
                        try:
                            file_data = io.BytesIO(response.content)
                            
                            # Sử dụng python-docx để đọc tệp DOCX
                            doc = Document(file_data)
                            text = []
                            
                            # Trích xuất văn bản từ các đoạn văn trong DOCX
                            for para in doc.paragraphs:
                                text.append(para.text)
                            
                            text = "\n".join(text)
                            print(f"[DOCX Content] {text[:200]}...")  # In 200 ký tự đầu

                        except Exception as e:
                            print(f"[ERROR] Lỗi khi xử lý tệp DOCX: {e}")

                    elif "excel" in content_type or ext in [".xls", ".xlsx", ".xlsm", ".csv"]:
                        # Tạo file giả trong RAM
                        file_data = io.BytesIO(response.content)
                        
                        # Kiểm tra loại file và sử dụng engine phù hợp
                        if ext in [".xlsx", ".xlsm"]: 
                            df = pd.read_excel(file_data, engine='openpyxl')
                        elif ext == ".xls": 
                            df = pd.read_excel(file_data, engine='xlrd')
                        elif ext == ".csv":
                            df = pd.read_csv(file_data) 

                        # In 5 dòng đầu của DataFrame
                        print(f"[Excel/CSV Content] {df.head()}")

                    elif "image" in content_type or ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"]:
                        # Mở hình ảnh từ dữ liệu nhị phân
                        image = Image.open(io.BytesIO(response.content))

                        # Hiển thị hình ảnh (nếu bạn muốn xem ảnh)
                        # image.show()

                        # Sử dụng pytesseract để trích xuất văn bản từ hình ảnh
                        text = pytesseract.image_to_string(image)

                        # In ra văn bản đã trích xuất
                        print(f"Văn bản trong ảnh: {text}")

                    else:
                        print("[WARN] Không xác định được định dạng file hoặc chưa hỗ trợ đọc.")

                else:
                    print(f"[ERROR] Không thể tải file từ URL: {data} (Status: {response.status_code})")

            elif material_type == "url":
                try:
                    response = requests.get(data)
                    print(f"[URL] {name} => {response.text[:200]}")  # In 200 ký tự đầu
                except Exception as e:
                    print(f"[ERROR] Lỗi khi fetch URL {data}: {e}")

            elif material_type == "content":
                print(f"[CONTENT] {name} => {data}")

        return Response({"message": "Processed materials"}, status=200)

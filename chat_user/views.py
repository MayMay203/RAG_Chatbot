from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from .llm_model import (get_llm_qdrant, detect_has_context_with_gemini, ask_gemini_with_context)
from .utils import (contains_url, extract_all_urls, classify_url_type, send_material_request)
import jwt
import os
import io
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
from rest_framework.exceptions import APIException
import asyncio
from doc_processing.utils import fetch_url_content, gemini_generate_content
from datetime import datetime, timezone
import json
class MessageView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            conversationId =  request.data.get('conversationId')
            query = request.data.get("query")
            fileTypes = request.data.get('fileTypes')
            nameList = request.data.get('nameList')

            accessToken = request.data.get('accessToken')
            SECRET_KEY = os.getenv("JWT_ACCESS_SECRET")
            decoded_token = jwt.decode(accessToken, SECRET_KEY, algorithms=["HS256"])
            roleId = decoded_token['roleId']
            accountId = decoded_token['id']

            isHasContext = detect_has_context_with_gemini(query)
            # Case: query has context
            if isHasContext:
                # context query only has url
                if contains_url(query):
                    urls = extract_all_urls(query)
                    full_content = ""

                    for index, url in enumerate(urls):
                        print(f"Handling URL: {url}")
                        response = None
                        if 'https://drive.google.com' in url or 'https://docs.google.com' in url:
                            file_id = url.split("d/")[-1].split("/")[0]
                            download_url = f"https://drive.google.com/uc?id={file_id}&export=download"
                            response = requests.get(download_url)
                        else:
                            response = requests.get(url)

                        url_type = classify_url_type(url, fileTypes)
                        content_type = response.headers.get('Content-Type', '')
                        content = ''

                        # URL File
                        if url_type == "document":
                            if "pdf" in content_type or url.endswith('.pdf') or 'pdf' in fileTypes[index]:
                                file_data = io.BytesIO(response.content)
                                reader = PdfReader(file_data)
                                text_list = [page.extract_text() for page in reader.pages if page.extract_text()]
                                content = "\n".join(text_list) if text_list else ""
                            # Cũ
                            elif "msword" in content_type or url.endswith('.doc') or 'msword' in fileTypes[index]:
                                with open("temp.doc", "wb") as f:
                                    f.write(response.content)
                                content = docx2txt.process("temp.doc")
                            # Mới
                            elif "officedocument.wordprocessingml.document" in content_type or url.endswith('.docx') or 'vnd.openxmlformats-officedocument.wordprocessingml.document' in fileTypes[index]:
                                try:
                                    file_data = io.BytesIO(response.content)
                                    doc = Document(file_data)
                                    content = "\n".join(para.text for para in doc.paragraphs)
                                except Exception as e:
                                    print(f"Lỗi khi xử lý file DOCX: {e}")
                            elif "excel" in content_type or url.endswith((".xls", ".xlsx", ".xlsm", ".csv")) or 'vnd.openxmlformats-officedocument.spreadsheetml.sheet' in fileTypes[index]:
                                file_data = io.BytesIO(response.content)
                                ext = os.path.splitext(nameList[index])[-1]
                                if ext in [".xlsx", ".xlsm"]:
                                    df = pd.read_excel(file_data, engine='openpyxl', dtype=str)
                                elif ext == ".xls":
                                    df = pd.read_excel(file_data, engine='xlrd', dtype=str)
                                elif ext == ".csv":
                                    df = pd.read_csv(file_data, dtype=str)
                                content = df.to_string(index=False)
                            elif "image" in content_type or url.endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff")) or any(ext in fileTypes[index] for ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"]):
                                image = Image.open(io.BytesIO(response.content))
                                gray_image = cv2.cvtColor(np.array(image), cv2.COLOR_BGR2GRAY)
                                _, thresholded_image = cv2.threshold(gray_image, 150, 255, cv2.THRESH_BINARY)
                                processed_image = Image.fromarray(thresholded_image)
                                text = pytesseract.image_to_string(processed_image, config='--psm 6 -c preserve_interword_spaces=1')
                                content = re.sub(r'[^a-zA-Z0-9\s]', '', text)
                            # handle save into db

                        # URL Website
                        else:
                            try:
                                raw_content = asyncio.run(fetch_url_content(url))
                                prompt = f'Bạn hãy đọc đoạn văn bản dưới đây và tóm tắt lại nội dung chính, chỉ lấy phần văn bản chính, bỏ qua tất cả các link, địa chỉ URL, hình ảnh, biểu tượng, quảng cáo, các phần điều hướng hoặc nội dung không liên quan khác. Chỉ trả về phần nội dung văn bản thuần túy. Nội dung phải đầy đủ các đoạn văn bản. Đoạn văn bản: "{raw_content}"'
                                content = gemini_generate_content(prompt)
                                prompt_2 = f"""
                                    Từ nội dung văn bản sau, hãy giúp tôi:
                                    1. Đặt một tiêu đề ngắn gọn, súc tích (name) phản ánh đúng nội dung chính của tài liệu. Tiêu đề không quá 255 ký tự.
                                    2. Viết một đoạn mô tả ngắn (description) giới thiệu tài liệu, độ dài khoảng 1–2 câu. Tiêu đề không quá 255 ký tự.

                                    Nội dung tài liệu:
                                    \"\"\"{content}\"\"\"
                                    Trả về kết quả dưới dạng JSON với các khóa: name, description.
                                    """
                                result_json = gemini_generate_content(prompt_2)

                                def clean_json_response(response_str):
                                    return re.sub(r"^```(?:json)?\s*|\s*```$", "", response_str.strip(), flags=re.MULTILINE)
                                
                                cleaned_json = clean_json_response(result_json)
                                result = json.loads(cleaned_json)

                                # handle save into db
                                material_data = {
                                    "name": result['name'],
                                    "description": result['description'],
                                    "url": url,
                                    "createdAt": datetime.now(timezone.utc).isoformat(),
                                    "updatedAt": datetime.now(timezone.utc).isoformat(),
                                    "materialType": {"id": 3},
                                    "accessLevel": {"id": 1},
                                    "account": {"id": accountId}
                                }
                                send_material_request(material_data, accessToken)
                            except Exception as e:
                                print(e)
                                continue  # skip this URL and move on

                        # Combine content
                        full_content += f"\n[URL: {url}]\n{content}\n"

                    if full_content.strip() == "":
                        raise APIException("Have error when extract content this url.")

                    combined_content = f"Câu hỏi: {query}\n\nNội dung từ các URL:\n{full_content}"
                    answer = ask_gemini_with_context(combined_content)
                    return Response(answer, status=status.HTTP_200_OK)
                # context query only has content
                else:
                    gemini_answer = ask_gemini_with_context(query)
                    return Response(gemini_answer, status=status.HTTP_200_OK)

            # The query has no context
            print('Question has no context')

            response = get_llm_qdrant(conversationId, query, roleId)

            return Response(
                response,
                status=status.HTTP_200_OK
            )
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            raise APIException(f"Đã xảy ra lỗi: {str(e)}")
    
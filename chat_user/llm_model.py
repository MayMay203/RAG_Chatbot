# from chat.models import Message
from langchain import OpenAI, ConversationChain
from langchain.memory import ConversationBufferMemory
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from google import genai
import google.generativeai as genaiModel
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
import os
from sklearn.metrics.pairwise import cosine_similarity
import requests
from collections import defaultdict

model = SentenceTransformer('all-MiniLM-L6-v2')
genaiModel.configure(api_key=os.getenv("GEMINI_API_KEY"))
gemini_model = genaiModel.GenerativeModel("gemini-2.0-flash")

# def get_final_prompt(query):
#     # Get Embeddings
#     open_ai.api_key = settings.OPENAI_API_KEY
#     response = open_ai.Embedding.create(
#         input=query,
#         model="text-embedding-ada-002"
#     )
#     embeddings = response['data'][0]['embedding']
    
#     # Qdrant Client search
#     connection = QdrantClient("localhost", port=6333)
#     all_collections = [
#                     'HubSpot_Certification_Study_Guide_2014_pro_ent',
#                     'hubspot-ebook_river-pools-blogging-case-study',
#                     'impromptu-rh',
#                     'small-business-social-media-ebook-hubspot'
#                 ]
    
#     search_results = []
#     for collection_name in all_collections:
#         try:
#             result = connection.search(
#                 collection_name=collection_name,
#                 query_vector=embeddings,
#                 limit=3
#             )
#             search_results.extend(result)
#         except Exception as e:
#             print(f"Error searching in collection {collection_name}: {e}")
    
#     # get final query to pass open_ai
#     prompt=""
#     for search_result in search_results:
#         prompt += search_result.payload["text"]
    
#     concatenated_string = f""" This is the previous data or context. \n
#             {prompt}
#             \n
#             Here's the user query from the data or context I have provided. \n
#             Question: {query} 
#         """

#     return concatenated_string

# Custom

# Encode label 1 lần duy nhất
# def get_embedding_store(stores):
#     for store in stores:
#         store["embedding"] = model.encode(store["storeDesc"])

# def detect_top_stores_from_query(query, stores, top_k=3, min_similarity=0.5):
#     query_embedding = model.encode(query)
#     get_embedding_store(stores)
    
#     similarities = []
#     for store in stores:
#         sim = cosine_similarity(
#             [query_embedding],
#             [store["embedding"]]
#         )[0][0]
#         similarities.append((store["storeName"], sim))

#     # Sắp xếp theo similarity giảm dần
#     similarities.sort(key=lambda x: x[1], reverse=True)

#     # Lọc theo ngưỡng
#     filtered = [(name, sim) for name, sim in similarities if sim >= min_similarity]

#     # Lấy top K store phù hợp
#     top_stores = filtered[:top_k]

#     return [store_name for store_name, _ in top_stores]

# def get_final_prompt(query, stores, roleId, top_k=3, min_similarity=0.5):
#     # Tạo embedding bằng mô hình local
#     query_embedding = model.encode(query).tolist()

#     # Sử dụng detect_top_stores_from_query để tìm các store liên quan
#     top_stores = detect_top_stores_from_query(query, stores, top_k, min_similarity)

#     # Kết nối với Qdrant client
#     connection = QdrantClient("localhost", port=6333)

#     # Xử lí chat với loại tài liệu nào theo roleId
#     filter = {}
#     if roleId == 2:
#         filter = {
#             "must": [
#                 {
#                     "key": "accessLevelType",
#                     "match": {
#                         "value": "public"
#                     }
#                 }
#             ]
#         }
#     elif roleId == 3:
#         filter = {
#             "must": [
#                 {
#                     "key": "accessLevelType",
#                     "match": {
#                         "any": ["public", "internal"]
#                     }
#                 }
#             ]
#         }

#     search_results = []    
#     print('Related store to query', top_stores)
#     # Lặp qua từng tên store trong top_stores
#     for store_name in top_stores:
#         try:
#             # Lấy danh sách collection (tên tài liệu) liên quan đến store
#             store = next((store for store in stores if store["storeName"] == store_name), None)
#             store_collections = store['materials']

#             # 2. Lấy tất cả collections từ Qdrant
#             qdrant_collections_response = requests.get("http://localhost:6333/collections")
#             qdrant_collections_data = qdrant_collections_response.json()

#             # 3. Lọc các collection có tên bắt đầu bằng 'collection_'
#             qdrant_collections = [
#                 collection['name'] for collection in qdrant_collections_data.get('result', {}).get('collections', [])
#                 if collection['name'].startswith("collection_")
#             ]

#             # 4. Gộp và loại bỏ trùng lặp
#             collections = list(set(store_collections + qdrant_collections))
#             print(collections)
#             # Tìm kiếm trong từng collection của store
#             for collection_name in collections:
#                 # Gửi yêu cầu HTTP POST đến Qdrant
#                 result = requests.post(
#                     f"http://localhost:6333/collections/{collection_name}/points/search",
#                     json={
#                         "vector": query_embedding,  # Vector tìm kiếm
#                         "filter": filter,  # Bộ lọc
#                         "limit": 3,  # Giới hạn số kết quả
#                         "with_payload": True,  # Lấy payload
#                         "with_vector": False  # Không lấy vector
#                     }
#                 )
#                 result_data = result.json()
#                 print('result_data', result_data)
#                 for search_result in result_data.get('result', []):
#                     search_results.append(search_result)

#         except Exception as e:
#             print(f"Error searching in collection {store_name}: {e}")

#     # Tạo prompt từ kết quả tìm kiếm
#     prompt = ""
#     for search_result in search_results:
#         text = search_result.get("payload", {}).get("text", "")
#         prompt += text

#     concatenated_string = f"""This is the previous data or context:\n{prompt}\n\nHere's the user query:\nQuestion: {query}"""
    
#     return concatenated_string


def get_final_prompt(query, roleId):    
    # Step 1: get all collections from qdrant
    try:
        response = requests.get("http://localhost:6333/collections")
        response.raise_for_status()
        collections_data = response.json()
        collections = [
            col['name']
            for col in collections_data.get("result", {}).get("collections", [])
        ]
    except Exception as e:
        print(f"Error to get collections list: {e}")
        return "Cannot access Qdrant."

    # Step 2: encode query
    query_embedding = model.encode(query).tolist()

    # Step 3: Define filter by role
    filter = {}
    if roleId == 2:
        filter = {
            "must": [
                {"key": "accessType", "match": {"value": "public"}},
                {"key": "active", "match": {"value": True}}
            ]
        }
    elif roleId == 3:
        filter = {
            "must": [
                {"key": "accessType", "match": {"any": ["public", "internal"]}},
                {"key": "active", "match": {"value": True}}
            ]
        }
    else:
        filter = {
            "must": [
                {"key": "active", "match": {"value": True}}
            ]
        }

    # Step 4: Search on all collections
    search_results = []
    for collection_name in collections:
        try:
            result = requests.post(
                f"http://localhost:6333/collections/{collection_name}/points/search",
                json={
                    "vector": query_embedding,
                    "filter": filter,
                    "limit": 3,
                    "with_payload": True,
                    "with_vector": False
                }
            )
            result.raise_for_status()
            result_data = result.json()
            for search_result in result_data.get('result', []):
                search_results.append(search_result)
        except Exception as e:
            print(f"Search error in collection '{collection_name}': {e}")

    # Step 5: Combine the results into Prompt
    grouped_results = defaultdict(list)

    for search_result in search_results:
        payload = search_result.get("payload", {})
        text = payload.get("text", "")
        material_name = payload.get("materialName", "Nguồn không xác định")
        grouped_results[material_name].append(text)

    result = ""
    for material_name, texts in grouped_results.items():
        result += f"\nNguồn: {material_name}\n"
        for text in texts:
            result += f"- {text}\n"

    concatenated_string = f"""
        Dưới đây là các thông tin liên quan được tìm thấy dựa trên câu hỏi trước đó:

        {result}

        Vui lòng trả lời chính xác câu hỏi dưới đây dựa trên thông tin đã cho.
        Không được suy đoán nếu thông tin không có.
        Phần nguồn thông tin được gom lại, đặt ở cuối câu trả lời theo dạng:
        Nguồn:
        1. <url 1>
        2. <url 2>
        Không lặp lại các nguồn giống nhau.

        Câu hỏi: {query}
        """
    return concatenated_string

def get_llm(query, conver_id):
    memory = ConversationBufferMemory()
    try:
        if not conver_id == "" or not conver_id is None:
            memorybuffer = Message.objects.filter(
                conversation_id=conver_id).order_by('-created_at')

            for item in memorybuffer:
                memory.chat_memory.add_user_message(item.query)
                memory.chat_memory.add_ai_message(item.response)
            memory.load_memory_variables({})
    except Exception as e:
        print(e)

    llm = OpenAI(temperature=0, model_name="gpt-3.5-turbo")
    conversation = ConversationChain(
        llm=llm,
        verbose=True,
        memory=memory,
    )
    output = conversation.predict(input=query)
    return output



# def get_llm_qdrant(query, conver_id):
#     # ghi nhớ hội thoại trước đó, ví dụ tôi là Nhung, hỏi lại t là ai thì nó nhớ
#     # chat gpt nói ghi nhớ theo id_conver
#     memory = ConversationBufferMemory()
#     try:
#         # promt này là gồm context: cái search được từ qdrant và cả câu hỏi query
#         prompt = get_final_prompt(query)
#         memory.chat_memory.add_user_message(prompt)
#         memory.load_memory_variables({})
#     except Exception as e:
#         print(e)
#     # print(prompt)
#     llm = OpenAI(temperature=0, model_name="gpt-3.5-turbo")
#     conversation = ConversationChain(
#         llm=llm,
#         verbose=True,
#         memory=memory,
#     )
#     output = conversation.predict(input=query)
#     return output

# custom
# Định nghĩa hàm sử dụng Gemini API và bộ nhớ
def get_llm_qdrant(conversationId, query, roleId):
    memory = ConversationBufferMemory()

    try:
        prompt = get_final_prompt(query, roleId)
        memory.chat_memory.add_user_message(prompt)  # Thêm câu hỏi vào bộ nhớ
        memory.load_memory_variables({})  # Load các biến trong bộ nhớ
    except Exception as e:
        print(e)

    # Tạo client của Gemini API
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=gemini_api_key)
    

    # Cập nhật prompt bằng cách thêm vào bộ nhớ
    # Lấy toàn bộ lịch sử hội thoại từ bộ nhớ
    conversation_history = memory.chat_memory.messages  # Lấy tất cả các tin nhắn trong bộ nhớ

    # Tạo chuỗi prompt bao gồm lịch sử hội thoại và câu hỏi của người dùng
    full_prompt = "\n".join([msg.content for msg in conversation_history])

    # Gửi yêu cầu tới Gemini API để tạo nội dung với bộ nhớ
    response = client.models.generate_content(
        model="gemini-2.0-flash", 
        contents=full_prompt 
    )
    
    # Trả về kết quả từ Gemini API
    return response.text

def detect_has_context_with_gemini(user_input: str) -> bool:
    prompt = f"""
        Xác định xem người dùng có đang cung cấp một đoạn nội dung có ngữ cảnh (context) để hỏi về nó hay không.

        Nếu có, trả lời: "True"  
        Nếu không, trả lời: "False"  

        Input: \"\"\"{user_input}\"\"\"
        """
    response = gemini_model.generate_content(prompt)
    return "True" in response.text

def ask_gemini_with_context(user_input: str) -> str:
    prompt = f"""
        Dưới đây là nội dung người dùng cung cấp. Hãy đọc kỹ và trả lời dựa trên nội dung này:

        \"\"\"{user_input}\"\"\"

        Hãy trả lời một cách rõ ràng và chính xác.
        """
    response = gemini_model.generate_content(prompt)
    return response.text.strip()

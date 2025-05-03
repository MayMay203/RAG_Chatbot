# from chat.models import Message
from django.conf import settings
from langchain import OpenAI, ConversationChain
from langchain.memory import ConversationBufferMemory
from qdrant_client import QdrantClient
import openai as open_ai
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
import google.generativeai as genai
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
import os

model = SentenceTransformer('all-MiniLM-L6-v2')


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
def get_final_prompt(query):
    # Tạo embedding bằng mô hình local
    embeddings = model.encode(query).tolist()

    connection = QdrantClient("localhost", port=6333)
    all_collections = [
        'Ha tang-TiengViet',
        'Viet-Education2024',
        'Viet-HitechPark2024',
        'Viet-Logistics2024',
        'Viet-Trade2024'
    ]

    search_results = []
    for collection_name in all_collections:
        try:
            # search có thể sẽ không trả về gì nhé
            result = connection.search(
                collection_name=collection_name,
                query_vector=embeddings,
                limit=3
            )
            search_results.extend(result)
        except Exception as e:
            print(f"Error searching in collection {collection_name}: {e}")

    # Tạo prompt
    print('search result........', search_results)
    prompt = ""
    for search_result in search_results:
        prompt += search_result.payload["text"]

    concatenated_string = f"""This is the previous data or context:\n{prompt}\n\nHere's the user query:\nQuestion: {query}"""
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
def get_llm_qdrant(query, conver_id):
    # Ghi nhớ hội thoại trước đó, giống như một bộ nhớ cuộc trò chuyện
    memory = ConversationBufferMemory()

    try:
        # Lấy prompt gồm context từ Qdrant và câu hỏi query
        prompt = get_final_prompt(query)
        memory.chat_memory.add_user_message(prompt)  # Thêm câu hỏi vào bộ nhớ
        memory.load_memory_variables({})  # Load các biến trong bộ nhớ
    except Exception as e:
        print(e)

    # Tạo client của Gemini API
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=gemini_api_key)  # Thay YOUR_API_KEY bằng API key của bạn
    

    # Cập nhật prompt bằng cách thêm vào bộ nhớ
    # Lấy toàn bộ lịch sử hội thoại từ bộ nhớ
    conversation_history = memory.chat_memory.messages  # Lấy tất cả các tin nhắn trong bộ nhớ

    # Tạo chuỗi prompt bao gồm lịch sử hội thoại và câu hỏi của người dùng
    full_prompt = "\n".join([msg.content for msg in conversation_history]) + "\n" + f"Question: {query}"

    # Gửi yêu cầu tới Gemini API để tạo nội dung với bộ nhớ
    response = client.models.generate_content(
        model="gemini-2.0-flash",  # Chọn model Gemini bạn muốn sử dụng
        contents=full_prompt  # Cung cấp toàn bộ lịch sử hội thoại và câu hỏi
    )
    
    # Trả về kết quả từ Gemini API
    return response.text

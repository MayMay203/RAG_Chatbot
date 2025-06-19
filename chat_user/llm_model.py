from langchain.memory import ConversationBufferMemory
from sentence_transformers import SentenceTransformer
import google.generativeai as genaiModel
import os
from sklearn.metrics.pairwise import cosine_similarity
import requests
from collections import defaultdict
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue, MatchAny

model = SentenceTransformer('all-MiniLM-L6-v2')
genaiModel.configure(api_key=os.getenv("GEMINI_API_KEY"))
gemini_model = genaiModel.GenerativeModel("gemini-2.0-flash")

QDRANT_CLOUD_URL = os.getenv("QDRANT_CLOUD_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
client = QdrantClient(
    url=QDRANT_CLOUD_URL,
    # api_key=QDRANT_API_KEY
)
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {QDRANT_API_KEY}"
}

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
    filter = {
        "must": [
            {"key": "active", "match": {"value": True}} 
        ]
    }

    if roleId == 2:
        filter["must"].append(
            {"key": "accessType", "match": {"value": 'public'}}
        )
    elif roleId == 3:
        filter["must"].append(
            {"key": "accessType", "match": {"any": ['public', 'internal']}}
        )
        
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
        2. Các thông tin đã được tìm thấy từ cơ sở dữ liệu (Qdrant) liên quan tới câu hỏi:

        {result}

        Dựa vào các thông tin trên, hãy trả lời chính xác câu hỏi sau.
        Tuyệt đối không được suy đoán nếu thông tin không có.

        Nếu câu hỏi được viết bằng tiếng Anh, vui lòng trả lời hoàn toàn bằng tiếng Anh.
        Nếu câu hỏi được viết bằng tiếng Việt, vui lòng trả lời bằng tiếng Việt.

        Nếu có nguồn trích dẫn, hãy liệt kê cuối câu trả lời theo định dạng **tùy theo ngôn ngữ của câu hỏi**:

        - Nếu câu hỏi bằng tiếng Việt:
        Nguồn:
        1. <url 1>
        2. <url 2>

        - Nếu câu hỏi bằng tiếng Anh:
        Sources:
        1. <url 1>
        2. <url 2>

        Không lặp lại các nguồn giống nhau.

        Nếu không có nguồn, không cần thêm phần nguồn.

        Câu hỏi: {query}
        """
    return concatenated_string

# Return answer from gemini API and save memory
conversations_memory = {}
def get_llm_qdrant(conversationId, query, roleId):
     # create memory for every conversation
    if conversationId not in conversations_memory:
        conversations_memory[conversationId] = ConversationBufferMemory()
    memory = conversations_memory[conversationId]

    # Step 1: Step 1: Get the last 10 pairs of conversation
    conversation_history = memory.chat_memory.messages
    history_text = ""
    for msg in conversation_history[-20:]:
        role = "User" if msg.type == "human" else "Bot"
        history_text += f"{role}: {msg.content}\n"
    try:
        # Prompt from qdrant search result + query
        rag_prompt = get_final_prompt(query, roleId)
    except Exception as e:
        print('Error', e)
        return "Xin lỗi, hiện tại hệ thống gặp sự cố, bạn vui lòng thử lại sau nhé."

     # Step 3: Kết hợp lịch sử hội thoại và prompt mới
    full_prompt = f"""
    Bạn là một trợ lý AI chuyên hỗ trợ trả lời các câu hỏi về xúc tiến đầu tư tại Đà Nẵng.

    1. Dưới đây là lịch sử hội thoại gần nhất giữa người dùng và hệ thống:
    {history_text}

    ----

    {rag_prompt}
    """

    # Step 4: Return answer
    response = gemini_model.generate_content(full_prompt)

    # Step 5: Save memory
    memory.chat_memory.add_user_message(query)
    memory.chat_memory.add_ai_message(response.text)

    return response.text

def detect_has_context_with_gemini(user_input: str) -> bool:
    prompt = f"""
        Bạn là một trợ lý AI.

        Nhiệm vụ của bạn là xác định xem đoạn nhập của người dùng có cung cấp ngữ cảnh tài liệu rõ ràng hay không — nghĩa là có đề cập đến tài liệu đính kèm, liên kết URL, hoặc những nội dung có vẻ như người dùng đang chia sẻ tài liệu để AI đọc và hiểu trước khi trả lời câu hỏi.

        Một số ví dụ về ngữ cảnh tài liệu:
        - "Tôi gửi file dưới đây, giúp tôi tóm tắt."
        - "Trong văn bản sau, tôi muốn hỏi..."
        - "Nội dung trong link này là gì?"
        - Hoặc có chứa các URL liên quan tới file, như Google Drive, Dropbox, hoặc trang web.
        - Hoặc khi người dùng gửi một đoạn văn bản dài và nói: "Dựa vào đoạn văn bản này, hãy trả lời câu hỏi sau."

        Nếu người dùng chỉ đặt một câu hỏi thông thường hoặc chèn một đoạn văn bản ngắn để hỏi trong đó, thì KHÔNG được coi là ngữ cảnh tài liệu. Trường hợp đó vẫn được xử lý như câu hỏi bình thường.

        Trả lời duy nhất một trong hai giá trị: "True" hoặc "False".

        Input người dùng:
        \"\"\"{user_input}\"\"\"
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

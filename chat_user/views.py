from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from .llm_model import (get_llm_qdrant, detect_has_context_with_gemini, ask_gemini_with_context)
from .utils import (contains_url, extract_first_url, classify_url_type)
import jwt
import os


class MessageView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            conversationId =  request.data.get('conversationId')
            query = request.data.get("query")
            storeCollections = request.data.get('materialsByStore')
            isHasContext = detect_has_context_with_gemini(query)
            if isHasContext:
                if contains_url(query):
                    url = extract_first_url(query)
                    print(url)
                    url_type = classify_url_type(url)

                    if url_type == "document":
                        print("Context with URL (Document)")
                        return Response({"type": "context_with_url", "url_type": "document", "url": url})
                    else:
                        print("Context with URL (Website)")
                        return Response({"type": "context_with_url", "url_type": "website", "url": url})
                else:
                    gemini_answer = ask_gemini_with_context(query)
                    return Response(
                        gemini_answer,
                        status=status.HTTP_200_OK
                    )
                    
            accessToken = request.data.get('accessToken')

            SECRET_KEY = os.getenv("JWT_ACCESS_SECRET")
            decoded_token = jwt.decode(accessToken, SECRET_KEY, algorithms=["HS256"])
            roleId = decoded_token['roleId']

            response = get_llm_qdrant(conversationId, query, storeCollections, roleId)

            return Response(
                response,
                status=status.HTTP_200_OK
            )
        except Exception as e:
            error_message = f"An error occurred: {str(e)}"
            print(error_message)
            return Response(
                {"error": error_message},
                status=status.HTTP_400_BAD_REQUEST
            )
    
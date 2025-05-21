from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from .llm_model import (get_llm_qdrant)
import jwt
import os


class MessageView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            conversationId =  request.data.get('conversationId')
            query = request.data.get("query")
            storeCollections = request.data.get('materialsByStore')
            accessToken = request.data.get('accessToken')

            SECRET_KEY = os.getenv("JWT_ACCESS_SECRET")
            decoded_token = jwt.decode(accessToken, SECRET_KEY, algorithms=["HS256"])
            roleId = decoded_token['roleId']

            # response = get_llm_qdrant(conversationId, query, storeCollections, filter, roleId)

            return Response(
                'jojo',
                status=status.HTTP_200_OK
            )
        except Exception as e:
            error_message = f"An error occurred: {str(e)}"
            print(error_message)
            return Response(
                {"error": error_message},
                status=status.HTTP_400_BAD_REQUEST
            )
    
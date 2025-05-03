from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from .llm_model import (get_llm_qdrant)


class MessageView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        print(request)
        # conversation_id =  request.data.get('conversation_id')
        # conversation = Conversation.objects.filter(id=conversation_id, user=request.user).first()
        
        # if conversation is None:
        #     return Response({'detail': 'Conversation not found'}, status=status.HTTP_404_NOT_FOUND)

        prompt = request.data.get("prompt")
        print('promtttt: ', prompt)
        # response = get_llm_qdrant(prompt, conversation_id)
        response = get_llm_qdrant(prompt)
        # message = Message(
        #     conversation=conversation,
        #     query=prompt,
        #     response=response
        # )
        # message.save()
        
        # Saving the last message to get conversations more faster
        # conversation.last_message = response
        # conversation.save()
        # logger.info(f"Answer from GPT for prompt '{prompt}' Asked By User {request.user}  is {response}")
        # return Response(
        #     MessageSerializer(message).data,
        #     status=status.HTTP_200_OK
        # )
        return Response(
            response,
            status=status.HTTP_200_OK
        )

    def get(self, request, *args, **kwargs):
        conversation_id =  request.query_params.get('conversation_id', 0)
        conversation = Conversation.objects.filter(id=conversation_id, user=request.user).first()
        
        if conversation is None:
            return Response({'detail': 'Conversation not found'}, status=status.HTTP_404_NOT_FOUND)
        
        messages = Message.objects.filter(conversation__id=conversation_id)
        serializer = MessageSerializer(messages, many=True)

        return Response(serializer.data,status=status.HTTP_200_OK)
    
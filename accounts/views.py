from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .serializers import LoginSerializer, RegisterSerializer


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    token, _ = Token.objects.get_or_create(user=user)
    return Response(
        {'token': token.key, 'username': user.username, 'role': user.role},
        status=status.HTTP_201_CREATED,
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = authenticate(
        username=serializer.validated_data['username'],
        password=serializer.validated_data['password'],
    )
    if user is None:
        return Response(
            {'detail': 'Invalid username or password.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key, 'username': user.username, 'role': user.role})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    # Deleting the token invalidates it immediately — the user (or
    # anyone who intercepted the token) can no longer authenticate
    # with it. They'd need to log in again to get a new one.
    request.user.auth_token.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from crm.models import UserProfile
from api.serializers import UserSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    """Get current authenticated user details"""
    # Ensure user has a profile
    if not hasattr(request.user, 'profile'):
        UserProfile.objects.get_or_create(
            user=request.user,
            defaults={'role': 'sales_executive'}
        )
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


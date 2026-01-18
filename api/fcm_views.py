from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from crm.models import UserProfile


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_fcm_token(request):
    """Update FCM token for the current user"""
    user = request.user
    fcm_token = request.data.get('fcm_token')
    
    if not fcm_token:
        return Response(
            {'error': 'fcm_token is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Ensure user has a profile
    if not hasattr(user, 'profile'):
        UserProfile.objects.create(user=user, role='sales_executive')
    
    # Update FCM token
    user.profile.fcm_token = fcm_token
    user.profile.save()
    
    return Response({
        'success': True,
        'message': 'FCM token updated successfully'
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_update_fcm_token(request):
    """Update FCM token for admin user (web dashboard)"""
    user = request.user
    
    # Check if user is admin
    if not (hasattr(user, 'profile') and user.profile.role == 'admin'):
        return Response(
            {'error': 'Unauthorized'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    fcm_token = request.data.get('fcm_token')
    
    if not fcm_token:
        return Response(
            {'error': 'fcm_token is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Update FCM token
    user.profile.fcm_token = fcm_token
    user.profile.save()
    
    return Response({
        'success': True,
        'message': 'FCM token updated successfully'
    })


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from django.db.models import Q
from crm.services import send_fcm_notification


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_notification(request):
    """
    Test endpoint to send FCM notification
    POST /api/test-notification/
    Body: {
        "user_id": 1,  # Optional: specific user ID, or omit to send to current user
        "title": "Test Notification",
        "message": "This is a test notification",
        "type": "test"
    }
    """
    user = request.user
    
    # Check if user is admin
    if not (hasattr(user, 'profile') and user.profile.role == 'admin'):
        return Response(
            {'error': 'Only admins can send test notifications'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get target user
    user_id = request.data.get('user_id')
    if user_id:
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    else:
        # Send to current user
        target_user = user
    
    # Check if target user has FCM token
    if not hasattr(target_user, 'profile') or not target_user.profile.fcm_token:
        return Response(
            {
                'error': f'User {target_user.username} does not have an FCM token',
                'message': 'Please log in from the app/dashboard first to register the token'
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get notification data
    title = request.data.get('title', 'Test Notification')
    message = request.data.get('message', 'This is a test notification from the API')
    notification_type = request.data.get('type', 'test')
    
    # Send notification
    success = send_fcm_notification(
        user=target_user,
        title=title,
        message=message,
        notification_type=notification_type
    )
    
    if success:
        return Response({
            'success': True,
            'message': f'Notification sent successfully to {target_user.username}',
            'user': {
                'id': target_user.id,
                'username': target_user.username,
                'email': target_user.email,
                'role': target_user.profile.role if hasattr(target_user, 'profile') else None,
            },
            'notification': {
                'title': title,
                'message': message,
                'type': notification_type
            }
        })
    else:
        return Response(
            {
                'success': False,
                'error': 'Failed to send notification',
                'message': 'Check NotificationLog in admin panel for error details'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_users_with_tokens(request):
    """
    List all users with FCM tokens
    GET /api/test-notification/users/
    """
    user = request.user
    
    # Check if user is admin
    if not (hasattr(user, 'profile') and user.profile.role == 'admin'):
        return Response(
            {'error': 'Only admins can view this'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    users = User.objects.filter(
        profile__fcm_token__isnull=False
    ).exclude(profile__fcm_token='').select_related('profile')
    
    users_data = []
    for u in users:
        users_data.append({
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'first_name': u.first_name,
            'last_name': u.last_name,
            'role': u.profile.role if hasattr(u, 'profile') else None,
            'has_token': bool(u.profile.fcm_token if hasattr(u, 'profile') else False),
            'token_preview': u.profile.fcm_token[:50] + '...' if hasattr(u, 'profile') and u.profile.fcm_token else None,
        })
    
    return Response({
        'count': len(users_data),
        'users': users_data
    })


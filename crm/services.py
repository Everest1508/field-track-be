"""
FCM Notification Service using Firebase Cloud Messaging API v2
"""
import json
import os
from google.auth import default
from google.auth.transport.requests import Request
from google.oauth2 import service_account
import requests
from django.conf import settings
from .models import NotificationLog, FollowUp, SystemNotification
from django.utils import timezone
from datetime import timedelta


def get_access_token():
    """Get OAuth2 access token for Firebase Cloud Messaging API v2"""
    try:
        # Try to use service account JSON file
        service_account_path = getattr(settings, 'FCM_SERVICE_ACCOUNT_PATH', None)
        
        # Convert Path object to string if needed
        if hasattr(service_account_path, '__str__'):
            service_account_path = str(service_account_path)
        
        if service_account_path and os.path.exists(service_account_path):
            credentials = service_account.Credentials.from_service_account_file(
                service_account_path,
                scopes=['https://www.googleapis.com/auth/firebase.messaging']
            )
            credentials.refresh(Request())
            return credentials.token
        else:
            # Fallback to default credentials (for GCP environments)
            credentials, project = default(scopes=['https://www.googleapis.com/auth/firebase.messaging'])
            credentials.refresh(Request())
            return credentials.token
    except Exception as e:
        print(f"Error getting access token: {e}")
        import traceback
        traceback.print_exc()
        return None


def send_fcm_notification(user, title, message, notification_type='followup_reminder'):
    """Send FCM notification to user using Firebase Cloud Messaging API v2"""
    if not hasattr(user, 'profile') or not user.profile.fcm_token:
        return False
    
    fcm_token = user.profile.fcm_token
    project_id = getattr(settings, 'FCM_PROJECT_ID', 'sales-tracking-b2ac5')
    
    # Get OAuth2 access token
    access_token = get_access_token()
    if not access_token:
        NotificationLog.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            fcm_token=fcm_token,
            success=False,
            error_message="Failed to get OAuth2 access token"
        )
        return False
    
    # FCM API v2 endpoint
    url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # FCM API v2 payload structure
    payload = {
        "message": {
            "token": fcm_token,
            "notification": {
                "title": title,
                "body": message
            },
            "data": {
                "type": notification_type,
                "title": title,
                "body": message
            },
            "android": {
                "priority": "high",
                "notification": {
                    "sound": "default",
                    "channel_id": "high_importance_channel"
                }
            },
            "apns": {
                "headers": {
                    "apns-priority": "10"
                },
                "payload": {
                    "aps": {
                        "sound": "default"
                    }
                }
            }
        }
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        success = response.status_code == 200
        
        error_message = ""
        if not success:
            try:
                error_data = response.json()
                error_message = error_data.get('error', {}).get('message', response.text)
            except:
                error_message = response.text
        
        NotificationLog.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            fcm_token=fcm_token,
            success=success,
            error_message=error_message
        )
        
        return success
    except Exception as e:
        NotificationLog.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            fcm_token=fcm_token,
            success=False,
            error_message=str(e)
        )
        return False


def send_system_notification_fcm(system_notification):
    """
    Send FCM notification for a SystemNotification instance
    If user is None, send to all users with FCM tokens
    """
    from django.contrib.auth.models import User
    
    # Determine target users
    if system_notification.user:
        # Send to specific user
        users = [system_notification.user]
    else:
        # Send to all users with FCM tokens (for admin/broadcast notifications)
        users = User.objects.filter(profile__fcm_token__isnull=False).exclude(profile__fcm_token='')
    
    # Send FCM notification to each user
    for user in users:
        if hasattr(user, 'profile') and user.profile.fcm_token:
            # Prepare data payload with notification details
            data_payload = {
                "type": "system_notification",
                "notification_type": system_notification.notification_type,
                "notification_id": str(system_notification.id),
                "title": system_notification.title,
                "body": system_notification.message,
            }
            
            # Add link if provided
            if system_notification.link:
                data_payload["link"] = system_notification.link
            
            # Send FCM notification with custom data
            send_fcm_notification_with_data(
                user,
                system_notification.title,
                system_notification.message,
                system_notification.notification_type,
                data_payload
            )


def send_fcm_notification_with_data(user, title, message, notification_type='system_notification', data=None):
    """Send FCM notification with custom data payload"""
    if not hasattr(user, 'profile') or not user.profile.fcm_token:
        return False
    
    fcm_token = user.profile.fcm_token
    project_id = getattr(settings, 'FCM_PROJECT_ID', 'sales-tracking-b2ac5')
    
    # Get OAuth2 access token
    access_token = get_access_token()
    if not access_token:
        NotificationLog.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            fcm_token=fcm_token,
            success=False,
            error_message="Failed to get OAuth2 access token"
        )
        return False
    
    # FCM API v2 endpoint
    url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # Prepare data payload (convert all values to strings for FCM)
    fcm_data = {}
    if data:
        for key, value in data.items():
            fcm_data[key] = str(value) if value is not None else ""
    
    # FCM API v2 payload structure
    payload = {
        "message": {
            "token": fcm_token,
            "notification": {
                "title": title,
                "body": message
            },
            "data": fcm_data,
            "android": {
                "priority": "high",
                "notification": {
                    "sound": "default",
                    "channel_id": "high_importance_channel"
                }
            },
            "apns": {
                "headers": {
                    "apns-priority": "10"
                },
                "payload": {
                    "aps": {
                        "sound": "default",
                        "badge": 1
                    }
                }
            },
            "webpush": {
                "notification": {
                    "title": title,
                    "body": message,
                    "icon": "/favicon.ico",
                    "badge": "/favicon.ico"
                },
                "fcm_options": {
                    "link": fcm_data.get("link", "/")
                }
            }
        }
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        success = response.status_code == 200
        
        error_message = ""
        if not success:
            try:
                error_data = response.json()
                error_message = error_data.get('error', {}).get('message', response.text)
            except:
                error_message = response.text
        
        NotificationLog.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            fcm_token=fcm_token,
            success=success,
            error_message=error_message
        )
        
        return success
    except Exception as e:
        NotificationLog.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            fcm_token=fcm_token,
            success=False,
            error_message=str(e)
        )
        return False


def send_followup_reminders():
    """Send reminders for follow-ups due today or overdue"""
    today = timezone.now().date()
    tomorrow = today + timedelta(days=1)
    
    # Follow-ups due today
    followups_today = FollowUp.objects.filter(
        due_date__date=today,
        completed=False,
        reminder_sent=False
    )
    
    for followup in followups_today:
        title = "Follow-up Reminder"
        message = f"Follow-up with {followup.customer.name} is due today"
        if followup.sales_executive:
            send_fcm_notification(
                followup.sales_executive,
                title,
                message,
                'followup_reminder'
            )
            followup.reminder_sent = True
            followup.save()
    
    # Optional: Send reminders for tomorrow (can be configured)
    followups_tomorrow = FollowUp.objects.filter(
        due_date__date=tomorrow,
        completed=False,
        reminder_sent=False
    )
    
    for followup in followups_tomorrow:
        title = "Follow-up Reminder"
        message = f"Follow-up with {followup.customer.name} is due tomorrow"
        if followup.sales_executive:
            send_fcm_notification(
                followup.sales_executive,
                title,
                message,
                'followup_reminder'
            )

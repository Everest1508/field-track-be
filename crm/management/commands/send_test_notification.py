"""
Django management command to send a test FCM notification to a specific token
"""
from django.core.management.base import BaseCommand
from django.conf import settings
import os
import requests
from google.auth import default
from google.auth.transport.requests import Request
from google.oauth2 import service_account


class Command(BaseCommand):
    help = 'Send a test FCM notification to a specific token'

    def add_arguments(self, parser):
        parser.add_argument(
            'token',
            type=str,
            help='FCM token to send notification to'
        )
        parser.add_argument(
            '--title',
            type=str,
            default='Test Notification',
            help='Notification title (default: "Test Notification")'
        )
        parser.add_argument(
            '--message',
            type=str,
            default='This is a test notification from the backend',
            help='Notification message'
        )
        parser.add_argument(
            '--type',
            type=str,
            default='test',
            help='Notification type (default: "test")'
        )

    def get_access_token(self):
        """Get OAuth2 access token for Firebase Cloud Messaging API v2"""
        try:
            # Try to use service account JSON file
            service_account_path = getattr(settings, 'FCM_SERVICE_ACCOUNT_PATH', None)
            
            # Convert Path object to string if needed
            if hasattr(service_account_path, '__str__'):
                service_account_path = str(service_account_path)
            
            if service_account_path and os.path.exists(service_account_path):
                self.stdout.write(f'Using service account: {service_account_path}')
                credentials = service_account.Credentials.from_service_account_file(
                    service_account_path,
                    scopes=['https://www.googleapis.com/auth/firebase.messaging']
                )
                credentials.refresh(Request())
                return credentials.token
            else:
                self.stdout.write(self.style.WARNING(
                    f'Service account file not found at: {service_account_path}'
                ))
                # Fallback to default credentials (for GCP environments)
                credentials, project = default(scopes=['https://www.googleapis.com/auth/firebase.messaging'])
                credentials.refresh(Request())
                return credentials.token
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error getting access token: {e}'))
            import traceback
            traceback.print_exc()
            return None

    def handle(self, *args, **options):
        fcm_token = options['token']
        title = options['title']
        message = options['message']
        notification_type = options['type']
        project_id = getattr(settings, 'FCM_PROJECT_ID', 'sales-tracking-b2ac5')
        
        self.stdout.write(f'Project ID: {project_id}')
        self.stdout.write(f'FCM Token: {fcm_token[:50]}...')
        self.stdout.write(f'Title: {title}')
        self.stdout.write(f'Message: {message}')
        
        # Get OAuth2 access token
        self.stdout.write('Getting access token...')
        access_token = self.get_access_token()
        if not access_token:
            self.stdout.write(self.style.ERROR('Failed to get OAuth2 access token'))
            return
        
        self.stdout.write(self.style.SUCCESS('Access token obtained'))
        
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
                },
                "webpush": {
                    "notification": {
                        "title": title,
                        "body": message,
                        "icon": "/favicon.png",
                        "badge": "/favicon.png"
                    }
                }
            }
        }
        
        try:
            self.stdout.write('Sending notification...')
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                self.stdout.write(self.style.SUCCESS('✅ Notification sent successfully!'))
                self.stdout.write(f'Response: {response.json()}')
            else:
                self.stdout.write(self.style.ERROR(f'❌ Failed to send notification'))
                self.stdout.write(f'Status Code: {response.status_code}')
                try:
                    error_data = response.json()
                    self.stdout.write(f'Error: {error_data}')
                except:
                    self.stdout.write(f'Response: {response.text}')
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error sending notification: {e}'))
            import traceback
            traceback.print_exc()


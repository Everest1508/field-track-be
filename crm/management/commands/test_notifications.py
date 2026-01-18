"""
Django management command to test FCM notifications
Usage: python manage.py test_notifications --user <username> --type <mobile|web|both>
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db.models import Q
from crm.services import send_fcm_notification
from crm.models import UserProfile


class Command(BaseCommand):
    help = 'Test FCM notifications for mobile app and web dashboard'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            help='Username or email of the user to send notification to',
        )
        parser.add_argument(
            '--type',
            type=str,
            choices=['mobile', 'web', 'both'],
            default='both',
            help='Type of notification to test (mobile, web, or both)',
        )
        parser.add_argument(
            '--title',
            type=str,
            default='Test Notification',
            help='Notification title',
        )
        parser.add_argument(
            '--message',
            type=str,
            default='This is a test notification from the backend',
            help='Notification message',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Send test notification to all users with FCM tokens',
        )

    def handle(self, *args, **options):
        user_arg = options.get('user')
        notification_type = options.get('type')
        title = options.get('title')
        message = options.get('message')
        send_to_all = options.get('all')

        if send_to_all:
            # Send to all users with FCM tokens
            users_with_tokens = User.objects.filter(
                profile__fcm_token__isnull=False
            ).exclude(profile__fcm_token='')
            
            if not users_with_tokens.exists():
                self.stdout.write(
                    self.style.WARNING('No users found with FCM tokens')
                )
                return
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Found {users_with_tokens.count()} users with FCM tokens'
                )
            )
            
            success_count = 0
            fail_count = 0
            
            for user in users_with_tokens:
                user_type = 'mobile' if user.profile.role == 'sales_executive' else 'web'
                
                if notification_type == 'both' or notification_type == user_type:
                    self.stdout.write(
                        f'Sending notification to {user.username} ({user_type})...'
                    )
                    success = send_fcm_notification(
                        user=user,
                        title=title,
                        message=message,
                        notification_type='test'
                    )
                    if success:
                        success_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'✅ Notification sent to {user.username}'
                            )
                        )
                    else:
                        fail_count += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f'❌ Failed to send to {user.username}'
                            )
                        )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n📊 Summary: {success_count} successful, {fail_count} failed'
                )
            )
        
        elif user_arg:
            # Send to specific user
            try:
                # Try to find user by username or email
                user = User.objects.get(
                    Q(username=user_arg) | Q(email=user_arg)
                )
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'User "{user_arg}" not found')
                )
                return
            except User.MultipleObjectsReturned:
                self.stdout.write(
                    self.style.ERROR(f'Multiple users found for "{user_arg}"')
                )
                return
            
            # Check if user has FCM token
            if not hasattr(user, 'profile') or not user.profile.fcm_token:
                self.stdout.write(
                    self.style.WARNING(
                        f'User {user.username} does not have an FCM token. '
                        'Please log in from the app/dashboard first to register the token.'
                    )
                )
                return
            
            user_type = 'mobile' if user.profile.role == 'sales_executive' else 'web'
            
            if notification_type != 'both' and notification_type != user_type:
                self.stdout.write(
                    self.style.WARNING(
                        f'User {user.username} is a {user_type} user, '
                        f'but you requested {notification_type} notification'
                    )
                )
                return
            
            self.stdout.write(
                f'Sending {notification_type} notification to {user.username} ({user_type})...'
            )
            self.stdout.write(f'Title: {title}')
            self.stdout.write(f'Message: {message}')
            self.stdout.write(f'FCM Token: {user.profile.fcm_token[:50]}...')
            
            success = send_fcm_notification(
                user=user,
                title=title,
                message=message,
                notification_type='test'
            )
            
            if success:
                self.stdout.write(
                    self.style.SUCCESS('✅ Notification sent successfully!')
                )
                self.stdout.write(
                    'Check the device/dashboard to see if the notification arrived.'
                )
            else:
                self.stdout.write(
                    self.style.ERROR('❌ Failed to send notification')
                )
                self.stdout.write(
                    'Check NotificationLog in admin panel for error details.'
                )
        
        else:
            self.stdout.write(
                self.style.ERROR(
                    'Please specify --user <username> or use --all to send to all users'
                )
            )
            self.stdout.write('\nUsage examples:')
            self.stdout.write('  python manage.py test_notifications --user admin')
            self.stdout.write('  python manage.py test_notifications --user sales_exec_1 --type mobile')
            self.stdout.write('  python manage.py test_notifications --all --type web')
            self.stdout.write('  python manage.py test_notifications --user admin --title "Custom Title" --message "Custom message"')


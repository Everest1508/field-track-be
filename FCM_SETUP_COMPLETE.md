# Firebase Cloud Messaging API v2 - Setup Complete ✅

## Configuration Status

✅ **Service Account Key**: `backend/firebase-service-account.json`  
✅ **Project ID**: `sales-tracking-b2ac5`  
✅ **API Version**: Firebase Cloud Messaging API v2  
✅ **Authentication**: OAuth2 with Service Account  

## File Locations

- **Service Account JSON**: `backend/firebase-service-account.json`
- **Settings**: `backend/core/settings.py`
- **FCM Service**: `backend/crm/services.py`
- **Git Ignore**: Updated to exclude service account files

## Next Steps

### 1. Install Dependencies

Activate your virtual environment and install:

```bash
cd backend
source venv/bin/activate  # or your venv activation command
pip install google-auth google-auth-httplib2
```

Or install from requirements.txt:

```bash
pip install -r requirements.txt
```

### 2. Verify Configuration

The service account file is already in place at:
```
backend/firebase-service-account.json
```

The settings are configured to automatically use this file.

### 3. Test Notifications

You can test sending notifications:

```python
from crm.services import send_fcm_notification
from django.contrib.auth.models import User

# Get a user with FCM token
user = User.objects.get(username='your_username')

# Send test notification
send_fcm_notification(
    user=user,
    title="Test Notification",
    message="This is a test from FCM API v2",
    notification_type="test"
)
```

### 4. Check Notification Logs

View sent notifications in Django admin or via API:
- Model: `NotificationLog`
- Admin: `/admin/crm/notificationlog/`
- API: `GET /api/notifications/`

## Security Notes

⚠️ **IMPORTANT**: 
- The service account JSON file is in `.gitignore`
- **DO NOT** commit this file to version control
- Keep the file secure and limit access

## API v2 Features

✅ OAuth2 authentication (more secure)  
✅ Platform-specific configurations (Android/iOS)  
✅ Better error handling  
✅ Future-proof API  

## Troubleshooting

### If notifications fail:

1. **Check access token generation**:
   ```python
   from crm.services import get_access_token
   token = get_access_token()
   print(token)  # Should print a long token string
   ```

2. **Check service account file**:
   ```bash
   ls -la backend/firebase-service-account.json
   ```

3. **Check NotificationLog**:
   - View error messages in Django admin
   - Check `error_message` field for details

4. **Verify FCM token**:
   - Ensure user has `fcm_token` in `UserProfile`
   - Token should be obtained from mobile app or web dashboard

## Ready to Use! 🚀

Your backend is now configured to send notifications using Firebase Cloud Messaging API v2!


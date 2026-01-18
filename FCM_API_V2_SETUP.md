# Firebase Cloud Messaging API v2 Setup

The backend now uses Firebase Cloud Messaging API v2, which requires OAuth2 authentication instead of the legacy server key.

## Setup Instructions

### 1. Get Firebase Service Account Key

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project: `sales-tracking-b2ac5`
3. Click on the gear icon ⚙️ next to "Project Overview"
4. Go to **Project Settings**
5. Click on the **Service Accounts** tab
6. Click **Generate New Private Key**
7. Save the JSON file (e.g., `firebase-service-account.json`)

### 2. Configure Backend

#### Option A: Using Environment Variable (Recommended)

```bash
export FCM_SERVICE_ACCOUNT_PATH="/path/to/firebase-service-account.json"
export FCM_PROJECT_ID="sales-tracking-b2ac5"
```

#### Option B: Using .env File

Add to your `.env` file:
```
FCM_SERVICE_ACCOUNT_PATH=/path/to/firebase-service-account.json
FCM_PROJECT_ID=sales-tracking-b2ac5
```

#### Option C: Place File in Project Root

1. Copy `firebase-service-account.json` to `backend/` directory
2. Update `settings.py` default path:
   ```python
   FCM_SERVICE_ACCOUNT_PATH = os.environ.get('FCM_SERVICE_ACCOUNT_PATH', BASE_DIR / 'firebase-service-account.json')
   ```

### 3. Install Dependencies

```bash
cd backend
pip install google-auth google-auth-httplib2
```

Or if using requirements.txt:
```bash
pip install -r requirements.txt
```

### 4. Security Notes

⚠️ **Important**: Never commit the service account JSON file to version control!

Add to `.gitignore`:
```
firebase-service-account.json
*.json
!package.json
!package-lock.json
```

### 5. Verify Setup

Test the notification service:

```python
from crm.services import send_fcm_notification
from django.contrib.auth.models import User

user = User.objects.get(username='test_user')
send_fcm_notification(
    user=user,
    title="Test Notification",
    message="This is a test notification",
    notification_type="test"
)
```

## API v2 vs Legacy API

### Legacy API (Old - Not Used)
- Endpoint: `https://fcm.googleapis.com/fcm/send`
- Authentication: Server Key in header
- Format: `Authorization: key={server_key}`

### API v2 (Current)
- Endpoint: `https://fcm.googleapis.com/v1/projects/{project_id}/messages:send`
- Authentication: OAuth2 Bearer token
- Format: `Authorization: Bearer {access_token}`
- More secure and feature-rich

## Benefits of API v2

1. **Better Security**: OAuth2 instead of static server keys
2. **More Features**: Better control over notification delivery
3. **Platform-Specific**: Separate configs for Android/iOS
4. **Future-Proof**: Legacy API may be deprecated

## Troubleshooting

### Error: "Failed to get OAuth2 access token"
- Check if service account file path is correct
- Verify file permissions
- Ensure the JSON file is valid

### Error: "Permission denied"
- Verify service account has "Firebase Cloud Messaging API" enabled
- Check IAM permissions in Google Cloud Console

### Error: "Invalid project ID"
- Verify `FCM_PROJECT_ID` matches your Firebase project ID
- Default is `sales-tracking-b2ac5`

## Migration from Legacy API

If you were using the old API with `FCM_SERVER_KEY`:
1. Download service account JSON file
2. Set `FCM_SERVICE_ACCOUNT_PATH` environment variable
3. Remove `FCM_SERVER_KEY` (no longer needed)
4. Restart Django server

The code automatically uses API v2 when service account is configured.


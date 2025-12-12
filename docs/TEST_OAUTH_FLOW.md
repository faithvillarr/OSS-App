# Testing the OAuth Flow

This guide explains how to test the OAuth 2.0 flow for the task client service.

## Prerequisites

1. **Google OAuth Credentials**: You need a `credentials.json` file in the project root with your Google OAuth 2.0 client credentials.
2. **Google Cloud Console Setup**: 
   - Create an OAuth 2.0 client ID in Google Cloud Console
   - Set the authorized redirect URI to: `http://localhost:8001/auth/callback` (or your service port)
   - Download the credentials as `credentials.json`

## Step-by-Step Testing

### 1. Start the FastAPI Service

```bash
# From the project root
uv run uvicorn task_client_service.fast_api_service:app --reload --port 8001
```

The service should start successfully without errors. You should see:
```
INFO:     Task Client Service started (client will be initialized on first request)
```

### 2. Initiate OAuth Flow

Open your browser and navigate to:
```
http://localhost:8001/auth/login
```

**What should happen:**
- You should be redirected to Google's OAuth consent screen
- The URL will look like: `https://accounts.google.com/o/oauth2/v2/auth?...`
- You'll see a page asking you to sign in and grant permissions

### 3. Complete Google Authentication

1. Sign in with your Google account
2. Review the permissions requested (Google Tasks access)
3. Click "Allow" or "Continue"

**What should happen:**
- Google redirects you back to: `http://localhost:8001/auth/callback?code=...&scope=...`
- You should see a message: "Authentication successful! You can close this window."
- The credentials are now stored in your session

### 4. Verify Credentials are Stored

You can verify the credentials are stored by checking the internal endpoint (this requires a session cookie):

```bash
# Using curl with session cookie
curl -v -c cookies.txt -b cookies.txt http://localhost:8001/auth/_give_session_creds
```

Or test by making an actual API call that requires authentication:

```bash
# List tasklists (this will use the session credentials)
curl -v -c cookies.txt -b cookies.txt http://localhost:8001/tasklists
```

### 5. Test API Operations

Once authenticated, you can test the task operations:

```bash
# List all tasklists
curl http://localhost:8001/tasklists

# List tasks in a tasklist
curl http://localhost:8001/tasks/{tasklist_id}

# Get a specific task
curl http://localhost:8001/tasks/{tasklist_id}/{task_id}
```

## Testing with Python Script

Here's a simple Python script to test the OAuth flow programmatically:

```python
import requests
from urllib.parse import urlparse, parse_qs

# Step 1: Start OAuth flow
base_url = "http://localhost:8001"
session = requests.Session()

# Get login page (will redirect to Google)
response = session.get(f"{base_url}/auth/login", allow_redirects=False)
print(f"Login redirect status: {response.status_code}")
print(f"Redirect URL: {response.headers.get('Location', 'None')}")

# Note: In a real test, you'd need to:
# 1. Follow the redirect to Google
# 2. Complete authentication (requires manual intervention)
# 3. Extract the authorization code from the callback
# 4. Verify the callback endpoint stores credentials

# Step 2: After manual authentication, verify credentials
try:
    response = session.get(f"{base_url}/auth/_give_session_creds")
    if response.status_code == 200:
        creds = response.json()
        print("✓ Credentials found in session")
        print(f"  Token: {creds.get('token', 'None')[:20]}...")
    else:
        print(f"✗ No credentials in session: {response.status_code}")
except Exception as e:
    print(f"✗ Error: {e}")
```

## Common Issues and Solutions

### Issue: "credentials.json not found"
**Solution**: Make sure `credentials.json` is in the project root directory.

### Issue: "Redirect URI mismatch"
**Solution**: 
- Check that the redirect URI in Google Cloud Console matches: `http://localhost:8001/auth/callback`
- Make sure the port matches your service port
- Update `OAUTH_REDIRECT_URI` environment variable if using a different port

### Issue: "Connection refused" during startup
**Solution**: This is expected - the service tries to get credentials during startup but the service isn't ready yet. The client is initialized lazily on the first request.

### Issue: "No credentials found in session"
**Solution**: 
- Make sure you completed the OAuth flow in the same browser session
- Check that cookies are being sent with requests
- Verify the session middleware is working

## Verifying the Flow Works

After completing the OAuth flow, you should be able to:

1. ✅ Make API calls without authentication errors
2. ✅ See credentials in the session (via `/_give_session_creds`)
3. ✅ List tasklists and tasks successfully
4. ✅ The client initializes on first request using session credentials

## Environment Variables

You can configure the OAuth flow with these environment variables:

```bash
# Set the redirect URI (default: http://localhost:8000/auth/callback)
export OAUTH_REDIRECT_URI="http://localhost:8001/auth/callback"

# Set the service base URL (default: http://localhost:8000)
export TASK_SERVICE_BASE_URL="http://localhost:8001"

# Set session secret key (for production)
export SESSION_SECRET_KEY="your-secret-key-here"
```

## Next Steps

After verifying the OAuth flow works:

1. Test that credentials persist across requests (same session)
2. Test that expired credentials trigger a refresh
3. Test that missing credentials prompt re-authentication
4. Write automated tests for the OAuth endpoints


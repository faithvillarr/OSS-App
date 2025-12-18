#!/usr/bin/env python3
"""Script to get Google Tasks refresh token interactively."""

import json
import logging
import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src" / "gtask_client_impl" / "src"))
sys.path.insert(0, str(project_root / "src" / "task_client_api" / "src"))

from gtask_client_impl.auth import OAuthManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    """Get refresh token interactively."""
    print("=" * 60)
    print("Google Tasks OAuth - Get Refresh Token")
    print("=" * 60)
    print()
    
    # Get credentials from credentials.json
    creds_path = project_root / "credentials.json"
    if not creds_path.exists():
        print(f"❌ Error: credentials.json not found at {creds_path}")
        print("Please ensure credentials.json is in the project root.")
        return None
    
    try:
        with creds_path.open() as f:
            creds_data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading credentials.json: {e}")
        return None
    
    # Extract client_id and client_secret
    if "installed" in creds_data:
        client_id = creds_data["installed"]["client_id"]
        client_secret = creds_data["installed"]["client_secret"]
    elif "web" in creds_data:
        client_id = creds_data["web"]["client_id"]
        client_secret = creds_data["web"]["client_secret"]
    else:
        print("❌ Error: Invalid credentials.json format")
        print("Expected 'installed' or 'web' key in credentials.json")
        return None
    
    print(f"✓ Found client_id: {client_id[:50]}...")
    print(f"✓ Found client_secret: {'*' * 20}")
    print()
    print("Starting interactive OAuth flow...")
    print("A browser window will open. Please complete the authentication.")
    print("Make sure to grant access to Google Tasks.")
    print()
    
    # Create OAuth manager and run interactive flow
    manager = OAuthManager()
    creds = manager._run_interactive_flow_for_refresh_token(client_id, client_secret)
    
    if creds and creds.refresh_token:
        print()
        print("=" * 60)
        print("✅ SUCCESS! Refresh token obtained:")
        print("=" * 60)
        print()
        print(f"TASKS_REFRESH_TOKEN={creds.refresh_token}")
        print()
        print("=" * 60)
        print("Copy this value for your terraform.tfvars file:")
        print("=" * 60)
        print(creds.refresh_token)
        print()
        print("This token has been saved to your .env file (if possible).")
        print("You can now use it in terraform.tfvars")
        print()
        return creds.refresh_token
    else:
        print()
        print("❌ Failed to obtain refresh token.")
        print("Please try again or check your credentials.json file.")
        return None

if __name__ == "__main__":
    refresh_token = main()
    sys.exit(0 if refresh_token else 1)


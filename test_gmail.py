import os
import json
import pickle
import sys
from google.cloud import secretmanager
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# --- CONFIGURATION ---
# Replace these with your actual values from your settings file
SECRET_NAME = "projects/YOUR_PROJECT_ID/secrets/YOUR_SECRET_NAME/versions/latest"
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def run_diagnostic():
    print("=== 🛠️ GMAIL CONNECTION DIAGNOSTIC 🛠️ ===\n")

    # --- STEP 1: GOOGLE CLOUD AUTHENTICATION ---
    print("[1/4] Testing Google Cloud Client initialization...")
    try:
        client = secretmanager.SecretManagerServiceClient()
        print("✅ Client initialized successfully.\n")
    except Exception as e:
        print(f"❌ FAILED: Could not initialize Secret Manager Client.")
        print(f"   Reason: {e}")
        print("   FIX: Run 'gcloud auth application-default login' in your terminal.\n")
        return

    # --- STEP 2: SECRET MANAGER ACCESS ---
    print(f"[2/4] Attempting to pull secret: {SECRET_NAME}")
    try:
        response = client.access_secret_version(request={"name": SECRET_NAME})
        payload = response.payload.data.decode("UTF-8")
        print("✅ Successfully retrieved data from Secret Manager.")
        
        # Test if it's valid JSON
        try:
            json.loads(payload)
            print("✅ Payload is valid JSON format.\n")
        except:
            print("⚠️ WARNING: Secret exists but is NOT valid JSON. It might be a binary pickle file.\n")
    except Exception as e:
        print(f"❌ FAILED: Could not access Secret Manager.")
        print(f"   Error Type: {type(e).__name__}")
        print(f"   Message: {e}\n")

    # --- STEP 3: LOCAL FILE CHECK ---
    print("[3/4] Checking local 'token.json'...")
    if os.path.exists('token.json'):
        file_size = os.path.getsize('token.json')
        print(f"✅ Found 'token.json' ({file_size} bytes).")
        
        # Peek at the bytes to see if it's text or binary
        with open('token.json', 'rb') as f:
            first_byte = f.read(1)
            f.seek(0)
            content_start = f.read(20)
            
        print(f"   First byte: {first_byte}")
        print(f"   Start of file: {content_start}")
        
        if first_byte == b'{':
            print("   Detected: This is a TEXT/JSON file. (Pickle will fail here!)")
        else:
            print("   Detected: This looks like a BINARY/PICKLE file.\n")
    else:
        print("ℹ️ No local 'token.json' found.\n")

    # --- STEP 4: PERMISSION TEST ---
    print("[4/4] Checking if current identity has access...")
    os.system("gcloud auth application-default print-access-token > /dev/null 2>&1 || echo '❌ No ADC identity found.'")

if __name__ == "__main__":
    run_diagnostic()
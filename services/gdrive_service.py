# services/gdrive_service.py
import json
import mimetypes
import io
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

from services.db import tokens_collection

BASE_DIR = Path(__file__).resolve().parent.parent
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
SCOPES = ["https://www.googleapis.com/auth/drive.file"]
TOKEN_DOC_ID = "google_drive_token"

def get_drive_service():
    """Fetches token from MongoDB Atlas; refreshes or authenticates if missing/expired."""
    credentials = None

    token_doc = tokens_collection.find_one({"_id": TOKEN_DOC_ID})

    if token_doc and "token_info" in token_doc:
        token_info = token_doc["token_info"]
        credentials = Credentials.from_authorized_user_info(token_info, SCOPES)

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            print("Refreshing expired Google Drive token...")
            credentials.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                raise FileNotFoundError(f"Missing {CREDENTIALS_FILE}. Place credentials.json in project root.")

            print("No valid token found in database. Launching browser for Google authentication...")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            credentials = flow.run_local_server(port=0)

        # Save/update token document in MongoDB Atlas
        updated_token_info = json.loads(credentials.to_json())
        tokens_collection.update_one(
            {"_id": TOKEN_DOC_ID},
            {"$set": {"token_info": updated_token_info}},
            upsert=True
        )
        print("Google OAuth Token successfully saved to MongoDB Atlas!")

    return build("drive", "v3", credentials=credentials)

def ensure_google_authenticated():
    """Runs at server startup to verify token presence or trigger OAuth login."""
    print("\n--- Checking Google Drive Credentials ---")
    get_drive_service()
    print("--- Google Drive Authentication Ready ---\n")

def create_drive_folder(folder_name: str, parent_id: str = None) -> str:
    """Creates a new folder on Google Drive and returns its ID."""
    service = get_drive_service()
    metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder"
    }
    if parent_id:
        metadata["parents"] = [parent_id]

    folder = service.files().create(body=metadata, fields="id").execute()
    return folder.get("id")

def upload_bytes_to_drive(file_bytes: bytes, filename: str, mimetype: str, folder_id: str = None):
    """Uploads in-memory bytes directly to Google Drive without saving to disk."""
    service = get_drive_service()

    metadata = {"name": filename}
    if folder_id:
        metadata["parents"] = [folder_id]

    media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mimetype, resumable=True)

    uploaded_file = (
        service.files()
        .create(body=metadata, media_body=media, fields="id, name, webViewLink")
        .execute()
    )

    return {
        "success": True,
        "name": uploaded_file.get("name"),
        "file_id": uploaded_file.get("id"),
        "web_view_link": uploaded_file.get("webViewLink")
    }
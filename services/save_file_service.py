import mimetypes
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ============================================================
# DEFAULT CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "token.json"

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

# Optional Google Drive folder ID
FOLDER_ID = None

# ============================================================
# GET GOOGLE DRIVE SERVICE
# ============================================================

def get_drive_service():
    credentials = None

    # Load existing token
    if TOKEN_FILE.exists():
        credentials = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    # Refresh or request authorization
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            credentials = flow.run_local_server(port=0)

        # Save token whenever it is issued OR refreshed
        TOKEN_FILE.write_text(credentials.to_json(), encoding="utf-8")

    return build("drive", "v3", credentials=credentials)

# ============================================================
# UPLOAD FILE TO GOOGLE DRIVE
# ============================================================

def upload_file(file_path: str | Path):
    """
    Upload a file to Google Drive.

    Args:
        file_path: Full path or filename.

    Returns:
        dict: Uploaded file information.
    """

    path = Path(file_path)

    # If relative path, resolve from current working directory
    if not path.is_absolute():
        path = Path.cwd() / path

    path = path.resolve()

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if not path.is_file():
        raise ValueError(f"Path is not a file: {path}")

    # Get authenticated Drive service
    service = get_drive_service()

    # File metadata
    metadata = {"name": path.name}

    if FOLDER_ID:
        metadata["parents"] = [FOLDER_ID]

    # Dynamically detect MIME type with fallback
    mimetype, _ = mimetypes.guess_type(path)
    if not mimetype:
        if path.suffix.lower() == ".webm":
            mimetype = "video/webm"
        else:
            mimetype = "application/octet-stream"

    # Prepare file upload stream
    media = MediaFileUpload(str(path), mimetype=mimetype, resumable=True)

    # Upload to Google Drive
    uploaded_file = (
        service.files()
        .create(body=metadata, media_body=media, fields="id, name, webViewLink")
        .execute()
    )

    result = {
        "success": True,
        "name": uploaded_file.get("name"),
        "file_id": uploaded_file.get("id"),
        "web_view_link": uploaded_file.get("webViewLink"),
    }

    print("File uploaded successfully!")
    print("Name:", result["name"])
    print("File ID:", result["file_id"])
    print("Link:", result["web_view_link"])

    return result

# if __name__ == "__main__":
#     # Example execution:
#     # upload_file("sample_recording.webm")
#     pass
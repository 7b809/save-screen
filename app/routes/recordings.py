import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from services.gdrive_service import create_drive_folder, upload_bytes_to_drive

router = APIRouter(tags=["Recordings"])

# ============================================================
# CONFIGURATION & ENVIRONMENT VARIABLES
# ============================================================

# Read MAX_PART_SIZE_MB from environment variables (Default: 50 MB)
try:
    MAX_PART_SIZE_MB = int(os.getenv("MAX_PART_SIZE_MB", "50"))
except ValueError:
    MAX_PART_SIZE_MB = 50

# Convert MB to bytes
MAX_PART_SIZE = MAX_PART_SIZE_MB * 1024 * 1024

# Cache active session folders to avoid creating redundant folders during live streaming
SESSION_FOLDERS = {}

# ============================================================
# API ENDPOINTS
# ============================================================

@router.post("/recordings")
async def upload_recording(
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    part_index: Optional[int] = Form(None),
):
    """
    Accepts recording file uploads and stores them in Google Drive.
    Supports both direct single file processing and continuous live batch streaming.
    """
    allowed = {".webm", ".mp4", ".ogg", ".wav", ".m4a"}
    suffix = Path(file.filename or "").suffix.lower() or ".webm"
    if suffix not in allowed:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    mime_types = {
        ".webm": "video/webm",
        ".mp4": "video/mp4",
        ".ogg": "video/ogg",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
    }
    mimetype = mime_types.get(suffix, "video/webm")

    # 1. Resolve or Create Target Google Drive Folder
    if session_id:
        if session_id not in SESSION_FOLDERS:
            SESSION_FOLDERS[session_id] = create_drive_folder(session_id)
        drive_folder_id = SESSION_FOLDERS[session_id]
        folder_name = session_id
    else:
        # Generate timestamp folder name (e.g. "26_09_20_23_17_55")
        folder_name = datetime.now().strftime("%y_%m_%d_%H_%M_%S")
        drive_folder_id = create_drive_folder(folder_name)

    part_number = part_index if part_index is not None else 1
    buffer = bytearray()
    uploaded_parts = []

    # 2. Read Incoming Data Stream in 1MB Increments
    while chunk := await file.read(1024 * 1024):
        buffer.extend(chunk)

        # Upload to Google Drive whenever buffer reaches MAX_PART_SIZE threshold
        if len(buffer) >= MAX_PART_SIZE:
            part_filename = f"part_{part_number}{suffix}"
            result = upload_bytes_to_drive(
                file_bytes=bytes(buffer),
                filename=part_filename,
                mimetype=mimetype,
                folder_id=drive_folder_id,
            )
            uploaded_parts.append(result)

            buffer.clear()
            part_number += 1

    # 3. Upload Remaining Buffer Contents (< MAX_PART_SIZE)
    if len(buffer) > 0:
        if part_index is not None:
            part_filename = f"part_{part_index}{suffix}"
        else:
            part_filename = (
                f"part_{part_number}{suffix}"
                if part_number > 1
                else f"full_recording{suffix}"
            )

        result = upload_bytes_to_drive(
            file_bytes=bytes(buffer),
            filename=part_filename,
            mimetype=mimetype,
            folder_id=drive_folder_id,
        )
        uploaded_parts.append(result)
        buffer.clear()

    return JSONResponse(
        {
            "success": True,
            "folder_name": folder_name,
            "folder_id": drive_folder_id,
            "total_parts": len(uploaded_parts),
            "parts": uploaded_parts,
        }
    )
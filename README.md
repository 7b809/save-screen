# Screen & Audio Share Platform

## Features
- FastAPI backend
- Jinja2 + Bootstrap frontend
- Screen-only, audio-only, or screen + audio mode
- Browser MediaRecorder
- Recordings saved in the backend `output/` folder

## Run on Windows/Linux

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload
```

Open http://127.0.0.1:8000

## Important
- Browser permissions are required.
- Screen sharing generally requires HTTPS when deployed, except localhost.
- The browser may not provide system audio on every operating system/browser.
- This starter saves WebM recordings. Add FFmpeg later if MP4 conversion is required.
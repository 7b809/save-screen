# services/db.py
import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGO_URI = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME", "google_auth")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
tokens_collection = db["tokens"]
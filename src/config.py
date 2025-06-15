from pathlib import Path
import os
import logging
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from minio import Minio

# Load environment variables
load_dotenv()

# UI Colors
ERROR_COLOR = 0xFF5555
SUCCESS_COLOR = 0x50C878
INFO_COLOR = 0x89CFF0

# File paths
COOKIES_PATH = Path("cookies.txt")
DOWNLOAD_FOLDER = Path("downloads")
LOG_PATH = Path("bot.log")

# Cache settings
CACHE_SIZE = 100
QUERIES_CACHE_SIZE = 500

# Timeouts
NO_USERS_DISCONNECT_TIMEOUT = 60 * 20  # 20 minutes
NO_MUSIC_DISCONNECT_TIMEOUT = 60 * 5  # 5 minutes

# MongoDB configuration
MONGODB_HOST = os.getenv("MONGODB_HOST", "localhost")
MONGODB_PORT = int(os.getenv("MONGODB_PORT", "27017"))
MONGODB_USERNAME = os.getenv("MONGO_INITDB_ROOT_USERNAME", "root")
MONGODB_PASSWORD = os.getenv("MONGO_INITDB_ROOT_PASSWORD", "example")
MONGODB_URI = f"mongodb://{MONGODB_USERNAME}:{MONGODB_PASSWORD}@{MONGODB_HOST}:{MONGODB_PORT}"

# MinIO configuration
MINIO_HOST = os.getenv("MINIO_HOST", "localhost")
MINIO_PORT = int(os.getenv("MINIO_PORT", "9000"))
MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "minio")
MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "minio123")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"

# Default bucket name for file storage
DEFAULT_BUCKET_NAME = "music-files"

# Create MongoDB client
try:
    mongo_client = AsyncIOMotorClient(
        MONGODB_URI,
        serverSelectionTimeoutMS=5000
    )
    # Verify connection
    # Note: This is done asynchronously, so it won't actually verify the connection here
    # The actual verification will happen when the client is first used
except Exception as e:
    logging.error(f"Failed to create MongoDB client: {str(e)}")
    mongo_client = None

# Create MinIO client
try:
    minio_client = Minio(
        f"{MINIO_HOST}:{MINIO_PORT}",
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_SECURE
    )
    # Note: Connection verification happens when methods are called
except Exception as e:
    logging.error(f"Failed to create MinIO client: {str(e)}")
    minio_client = None

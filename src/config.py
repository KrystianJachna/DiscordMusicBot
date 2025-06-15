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

# Function to create a FileStorageManager instance
async def create_file_storage_manager(bucket_name=DEFAULT_BUCKET_NAME, create_bucket=True):
    """
    Create and return a FileStorageManager instance using the configured MongoDB and MinIO clients.

    Args:
        bucket_name: Name of the MinIO bucket to use (default: DEFAULT_BUCKET_NAME)
        create_bucket: Whether to create the bucket if it doesn't exist (default: True)

    Returns:
        A FileStorageManager instance or None if creation fails
    """
    from cogs.music.music_database import FileStorageManager

    if mongo_client is None or minio_client is None:
        logging.error("Cannot create FileStorageManager: MongoDB or MinIO client is not available")
        return None

    try:
        # Use the async creation method to avoid blocking the event loop
        storage_manager = await FileStorageManager.create_async(
            mongo_db_client=mongo_client,
            minio_client=minio_client,
            bucket_name=bucket_name,
            create_bucket=create_bucket
        )
        logging.info(f"FileStorageManager created successfully with bucket: {bucket_name}")
        return storage_manager
    except Exception as e:
        logging.error(f"Failed to create FileStorageManager: {str(e)}")
        return None

# Function to create a DatabaserDaemon instance
async def create_database_daemon(interval_seconds=300):  # 5 minutes default
    """
    Create and return a DatabaserDaemon instance using a FileStorageManager.

    Args:
        interval_seconds: Interval in seconds for the daemon to run cleanup (default: 300)

    Returns:
        A tuple containing (DatabaserDaemon instance, FileStorageManager instance) or (None, None) if creation fails
    """
    from cogs.music.music_database import DatabaserDaemon

    # Create a FileStorageManager instance
    storage_manager = await create_file_storage_manager()
    if storage_manager is None:
        return None, None

    try:
        # Create the DatabaserDaemon instance
        daemon = DatabaserDaemon(storage_manager, interval_seconds)
        logging.info(f"DatabaserDaemon created successfully with interval: {interval_seconds} seconds")
        return daemon, storage_manager
    except Exception as e:
        logging.error(f"Failed to create DatabaserDaemon: {str(e)}")
        return None, storage_manager

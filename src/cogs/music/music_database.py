import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
import uuid
import asyncio
import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from bson.objectid import ObjectId
from minio import Minio


logger = logging.getLogger(__name__)


@dataclass
class NewSongQuery:
    title: str
    original_url: str | None
    unique_service_id: str
    duration: int
    thumbnail_file: Path
    music_file: Path


class FileStorageManager:

    def __init__(self,
                 mongo_db_client: AsyncIOMotorClient,
                 minio_client: Minio,
                 bucket_name: str,
                 db_name: str = "file_storage",
                 collection_name: str = "files",
                 create_bucket: bool = False):
        self.minio_client = minio_client
        self.bucket_name = bucket_name

        if create_bucket and not self.minio_client.bucket_exists(self.bucket_name):
            self.minio_client.make_bucket(self.bucket_name)

        self.db: AsyncIOMotorDatabase = mongo_db_client[db_name]
        self.collection: AsyncIOMotorCollection = self.db[collection_name]

        if not self.collection.index_information():
            logger.info(f"Creating indexes for collection {collection_name}.")
            self.create_index()

    @classmethod
    async def create_async(cls, 
                          mongo_db_client: AsyncIOMotorClient,
                          minio_client: Minio,
                          bucket_name: str,
                          db_name: str = "file_storage",
                          collection_name: str = "files",
                          create_bucket: bool = False):
        instance = cls(mongo_db_client, minio_client, bucket_name, db_name, collection_name, False)

        if create_bucket:
            bucket_exists = await asyncio.to_thread(minio_client.bucket_exists, bucket_name)
            if not bucket_exists:
                await asyncio.to_thread(minio_client.make_bucket, bucket_name)

        if not await instance.collection.index_information():
            logger.info(f"Creating indexes for collection {collection_name}.")
            instance.create_index()

        return instance

    def create_index(self):
        self.collection.create_index("unique_service_id", unique=True)
        self.collection.create_index("item_id", unique=True)
        self.collection.create_index("uploaded_successfully")
        self.collection.create_index("modification_date")

    @classmethod
    def music_path(cls, _id: str) -> str:
        return f"music/{_id}"

    @classmethod
    def image_path(cls, _id: str) -> str:
        return f"image/{_id}"

    def _send_to_bucket(self, file: Path, dest: str, content_type: str):
        try:
            with open(file, "rb") as f:
                f.seek(0, os.SEEK_END)
                file_size = f.tell()
                f.seek(0)

                self.minio_client.put_object(
                    bucket_name=self.bucket_name,
                    object_name=dest,
                    data=f,
                    length=file_size,
                    content_type=content_type
                )
        except Exception as e:
            raise RuntimeError(f"Failed to upload file {file} to {dest}: {str(e)}") from e

    async def make_document(self, query: NewSongQuery) -> str | None:
        item_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, self.bucket_name))

        file_data = {
            "item_id": item_id,
            "unique_service_id": query.unique_service_id,
            "title": query.title,
            "url": query.original_url,
            "duration": query.duration,

            "uploaded_successfully": False,
            "creation_date": datetime.now(ZoneInfo("UTC")),
            "modification_date": datetime.now(ZoneInfo("UTC"))
        }

        def send_files():
            self._send_to_bucket(query.music_file, self.music_path(item_id), "audio/mpeg")
            self._send_to_bucket(query.thumbnail_file, self.image_path(item_id), "image/jpeg")

        result = await self.collection.insert_one(file_data)
        if not result.acknowledged:
            logger.error(f"Failed to insert metadata for item {item_id}.")
            return None

        try:
            await asyncio.to_thread(send_files)
        except RuntimeError:
            logger.error(f"Failed to upload files for item {item_id}.")
            return None

        file_metadata = await self.collection.update_one(
            {"_id": ObjectId(result.inserted_id)},
            {
                "$set": {
                    "uploaded_successfully": True,
                    "modification_date": datetime.now(ZoneInfo("UTC"))
                }
            }
        )
        if not file_metadata.modified_count:
            logger.error(f"Failed to update metadata for item {item_id} after upload.")
            return None

        logger.info(f"Successfully stored item {item_id} with metadata in MongoDB and files in MinIO.")
        return item_id

    async def check_file_exists(self, unique_service_id: str) -> bool:
        document = await self.collection.find_one({"unique_service_id": unique_service_id})
        return document is not None and document["uploaded_successfully"]

    @dataclass
    class StoredMusicFile:
        music_url: str
        thumbnail_url: str
        title: str
        duration: int
        expires_at: int

    async def get_item(self, query: dict, expires_minutes: int) -> StoredMusicFile:
        document = await self.collection.find_one(query)
        if not document:
            raise FileNotFoundError(f"No document found for query: {query}")

        if not document.get("uploaded_successfully", False):
            raise FileNotFoundError(f"Item {document['item_id']} has not been uploaded successfully.")

        result = await self.collection.update_one(
            {"_id": document["_id"]},
            {"$set": {"modification_date": datetime.now(ZoneInfo("UTC"))}}
        )
        if result.modified_count == 0:
            logger.warning(f"Failed to update modification date for item {document['item_id']}.")

        music_url = await asyncio.to_thread(
            self.minio_client.presigned_get_object,
            bucket_name=self.bucket_name,
            object_name=self.music_path(document["item_id"]),
            expires=timedelta(minutes=expires_minutes)
        )
        thumbnail_url = await asyncio.to_thread(
            self.minio_client.presigned_get_object,
            bucket_name=self.bucket_name,
            object_name=self.image_path(document["item_id"]),
            expires=timedelta(minutes=expires_minutes)
        )

        return self.StoredMusicFile(
            music_url=music_url,
            thumbnail_url=thumbnail_url,
            title=document["title"],
            duration=document["duration"],
            expires_at=expires_minutes * 60
        )

    async def get_item_by_service_id(self, unique_service_id: str, expires_minutes: int) -> StoredMusicFile:
        query = {"unique_service_id": unique_service_id}
        return await self.get_item(query, expires_minutes)

    async def delete_item(self, query: dict):
        document = await self.collection.find_one(query)
        if not document:
            raise FileNotFoundError(f"No document found for query: {query}")

        try:
            await asyncio.to_thread(
                self.minio_client.remove_object,
                bucket_name=self.bucket_name,
                object_name=self.music_path(document["item_id"])
            )
        except Exception as e:
            logger.error(f"Failed to delete music file for item {document['item_id']}: {str(e)}")
        try:
            await asyncio.to_thread(
                self.minio_client.remove_object,
                bucket_name=self.bucket_name,
                object_name=self.image_path(document["item_id"])
            )
        except Exception as e:
            logger.error(f"Failed to delete thumbnail file for item {document['item_id']}: {str(e)}")

        result = await self.collection.delete_one(query)
        if result.deleted_count == 0:
            logger.error(f"Failed to delete metadata for item {document['item_id']}.")
        else:
            logger.info(f"Successfully deleted item {document['item_id']} and its files.")


class DatabaseDaemon:

    def __init__(self, file_storage_manager: FileStorageManager, interval_seconds: int = 60 * 5):
        self.file_storage_manager = file_storage_manager
        self.interval_seconds = interval_seconds

        self._daemon_task = None
        self._is_running = False
        self._stop_now = False

    async def cleanup(self):
        deleted_count = 0
        try:
            expiration_time = datetime.now(ZoneInfo("UTC")) - timedelta(seconds=self.interval_seconds)
            query = {
                "$or": [
                    {"modification_date": {"$lt": expiration_time}},
                    {"uploaded_successfully": False}
                ]
            }
            async for document in self.file_storage_manager.collection.find(query):
                try:
                    await self.file_storage_manager.delete_item({"_id": document["_id"]})
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Error deleting document {document['_id']}: {str(e)}")
            if deleted_count:
                logger.info(f"Deleted {deleted_count} old or failed entries from the database.")
        except Exception as e:
            logger.error(f"Error during old entries cleanup: {str(e)}")

    def is_running(self) -> bool:
        return self._is_running

    async def loop(self):
        while not self._stop_now:
            try:
                await self.cleanup()
            except Exception as e:
                logger.error(f"Error during cleanup: {str(e)}")
            await asyncio.sleep(self.interval_seconds)

    async def start(self):
        if self._is_running:
            logger.warning("DatabaserDaemon is already running.")
            return

        self._is_running = True
        self._stop_now = False

        self._daemon_task = asyncio.create_task(self.loop())
        logger.info("DatabaserDaemon started.")

    async def stop(self):
        if not self._is_running:
            logger.warning("DatabaserDaemon is not running.")
            return

        self._stop_now = True
        if self._daemon_task:
            await self._daemon_task
            self._daemon_task = None

        self._is_running = False
        logger.info("DatabaserDaemon stopped.")

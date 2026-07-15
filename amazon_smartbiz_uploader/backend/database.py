import os
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from dotenv import load_dotenv

load_dotenv()

import certifi

MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI:
    raise ValueError("MONGODB_URI is not set in the environment variables.")

client = AsyncIOMotorClient(MONGODB_URI, tlsCAFile=certifi.where())
db = client.get_database("FakhriDev") # Explicitly set DB name if not in default connection

# Collections
admin_collection = db["admin_users"]
drafts_collection = db["drafts"]
sheets_collection = db["generated_sheets"]
jobs_collection = db["jobs"]

def get_fs():
    return AsyncIOMotorGridFSBucket(db)

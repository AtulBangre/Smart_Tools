import asyncio
from database import admin_collection
from auth import get_password_hash

async def create_admin():
    username = "admin"
    password = "adminpassword123"
    
    existing_admin = await admin_collection.find_one({"username": username})
    if existing_admin:
        print(f"Admin '{username}' already exists.")
        return
        
    hashed_password = get_password_hash(password)
    await admin_collection.insert_one({
        "username": username,
        "hashed_password": hashed_password
    })
    print(f"Admin '{username}' created successfully with password '{password}'!")

if __name__ == "__main__":
    asyncio.run(create_admin())

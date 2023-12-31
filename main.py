from fastapi import FastAPI, HTTPException, Body, Query, status, File, Form, UploadFile
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from pydantic import BaseModel, Field
from bson import ObjectId
from typing import List
from datetime import datetime
from fastapi.responses import StreamingResponse
import io

app = FastAPI()

# MongoDB connection setup
# Connection details
mongo_host = 'localhost'  # or the IP address of your Docker host
mongo_port = 27017
mongo_username = 'root'
mongo_password = 'root'
mongo_database = 'admin'  # or the name of your database

# Create the MongoDB connection string
connection_string = f"mongodb://{mongo_username}:{mongo_password}@{mongo_host}:{mongo_port}/{mongo_database}"

client = MongoClient(connection_string)
db = client["facebook"]

# collections
user_collection = db["users"]
event_collection = db["events"]
group_collection = db["groups"]
thread_collection = db["threads"]
message_collection = db["Message "]
photo_album_collection = db["photo_album"]
photo_collection = db["photos"]
# Index
user_collection.create_index("email", unique=True)

## Event

class Event(BaseModel):
    name: str
    description: str
    start_date: str
    end_date: str
    location: str
    cover_photo: str
    is_private: bool
    organizers: List[str] = []
    members: List[str] = []
    polls: List[str] = []

class EventInDB(Event):
    id: str

# Create Event
@app.post("/events/", response_model=EventInDB)
async def create_event(event: Event):
    event_data = {**event.model_dump()}
    result = event_collection.insert_one(event_data)
    event_in_db = EventInDB(**event.model_dump(), id=str(result.inserted_id))
    return event_in_db

# Read Event
@app.get("/events/{event_id}", response_model=EventInDB)
async def read_event(event_id: str):
    event_data = event_collection.find_one({"_id": ObjectId(event_id)})
    if event_data:
        event_data["id"] = str(event_data["_id"])  # Convert ObjectId to str
        return EventInDB(**event_data)
    else:
        raise HTTPException(status_code=404, detail="Event not found")

# Update Event
@app.put("/events/{event_id}", response_model=EventInDB)
async def update_event(event_id: str, updated_event: Event):
    existing_event = event_collection.find_one({"_id": ObjectId(event_id)})
    if existing_event:
        event_data = {
            "$set": {
                "name": updated_event.name,
                "description": updated_event.description,
                "start_date": updated_event.start_date,
                "end_date": updated_event.end_date,
                "location": updated_event.location,
                "cover_photo": updated_event.cover_photo,
                "is_private": updated_event.is_private,
                "organizers": updated_event.organizers,
                "members": updated_event.members,
                "polls": updated_event.polls,
            }
        }
        result = event_collection.update_one({"_id": ObjectId(event_id)}, event_data)

        if result.modified_count == 1:
            return EventInDB(id=event_id, **updated_event.model_dump())

    raise HTTPException(status_code=404, detail="Event not found")

# Delete Event
@app.delete("/events/{event_id}", response_model=dict)
async def delete_event(event_id: str):
    result = event_collection.delete_one({"_id": ObjectId(event_id)})
    if result.deleted_count == 1:
        return {"message": "Event deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Event not found")
    
# Search Event
@app.get("/events", response_model=List[EventInDB])
async def search_events(
    name: str = Query(None, title="Event Name", description="Search events by name"),
    location: str = Query(None, title="Event Location", description="Search events by location"),
    is_private: bool = Query(None, title="Is Private", description="Filter events by privacy"),
    start_date_from: str = Query(None, title="Start Date From", description="Filter events starting from a specific date"),
    start_date_to: str = Query(None, title="Start Date To", description="Filter events up to a specific date"),
    end_date_from: str = Query(None, title="End Date From", description="Filter events ending from a specific date"),
    end_date_to: str = Query(None, title="End Date To", description="Filter events ending up to a specific date"),
    organizer: str = Query(None, title="Organizer", description="Search events by organizer"),
    member: str = Query(None, title="Member", description="Search events by member"),
    poll: str = Query(None, title="Poll", description="Search events by poll"),
):
    query = {}

    if name:
        query["name"] = {"$regex": name, "$options": "i"}

    if location:
        query["location"] = {"$regex": location, "$options": "i"}

    if is_private:
        query["is_private"] = is_private

    if start_date_from:
        query["start_date"] = {"$gte": start_date_from}

    if start_date_to:
        query["start_date"]["$lte"] = start_date_to

    if end_date_from:
        query["end_date"] = {"$gte": end_date_from}

    if end_date_to:
        query["end_date"]["$lte"] = end_date_to

    if organizer:
        query["organizers"] = {"$in": [organizer]}

    if member:
        query["members"] = {"$in": [member]}

    if poll:
        query["polls"] = {"$in": [poll]}

    events = event_collection.find(query)
    return [EventInDB(id=str(event["_id"]), **event) for event in events]


# Group

class Group(BaseModel):
    name: str
    description: str
    icon: str
    cover_photo: str
    group_type: str
    allow_members_to_publish: bool
    allow_members_to_create_events: bool
    admin: List[str] = []

class GroupInDB(Group):
    id: str

# Create a group
@app.post("/groups/", response_model=GroupInDB)
async def create_group(group: Group):
    group_data = {**group.model_dump()}
    result = group_collection.insert_one(group_data)
    inserted_id = str(result.inserted_id)
    return GroupInDB(id=inserted_id, **group.model_dump())

# Read a group by ID
@app.get("/groups/{group_id}", response_model=GroupInDB)
async def read_group(group_id: str):
    group_data = group_collection.find_one({"_id": ObjectId(group_id)})
    if group_data:
        group_data["id"] = str(group_data["_id"])  # Convert ObjectId to str
        return GroupInDB(**group_data)
    else:
        raise HTTPException(status_code=404, detail="Group not found")

# Update a group by ID
@app.put("/groups/{group_id}", response_model=GroupInDB)
async def update_group(group_id: str, updated_group: Group):
    existing_group = group_collection.find_one({"_id": ObjectId(group_id)})
    if existing_group:
        group_data = {
            "$set": {
                "name": updated_group.name,
                "description": updated_group.description,
                "icon": updated_group.icon,
                "cover_photo": updated_group.cover_photo,
                "group_type": updated_group.group_type,
                "allow_members_to_publish": updated_group.allow_members_to_publish,
                "allow_members_to_create_events": updated_group.allow_members_to_create_events,
                "admin": updated_group.admin,
            }
        }
        result = group_collection.update_one({"_id": ObjectId(group_id)}, group_data)
        if result.modified_count == 1:
            return GroupInDB(id=group_id, **updated_group.model_dump())

    raise HTTPException(status_code=404, detail="Group not found")

# Delete a group by ID
@app.delete("/groups/{group_id}", response_model=dict)
async def delete_group(group_id: str):
    result = group_collection.delete_one({"_id": ObjectId(group_id)})
    if result.deleted_count == 1:
        return {"message": "Group deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Group not found")

# Search groups
@app.get("/groups", response_model=List[GroupInDB])
async def search_groups(
    name: str = Query(None, title="Group Name", description="Search groups by name"),
    group_type: str = Query(None, title="Group Type", description="Filter groups by type"),
    allow_publish: bool = Query(None, title="Allow Members to Publish", description="Filter groups by publishing permission"),
    allow_create_events: bool = Query(None, title="Allow Members to Create Events", description="Filter groups by event creation permission"),
    admin: str = Query(None, title="Admin", description="Search groups by admin"),
):
    query = {}

    if name:
        query["name"] = {"$regex": name, "$options": "i"}

    if group_type:
        query["group_type"] = group_type

    if allow_publish:
        query["allow_members_to_publish"] = allow_publish

    if allow_create_events:
        query["allow_members_to_create_events"] = allow_create_events

    if admin:
        query["admin"] = {"$in": [admin]}

    groups = group_collection.find(query)
    return [GroupInDB(id=str(group["_id"]), **group) for group in groups]

# User

class User(BaseModel):
    name: str
    email: str

class UserInDB(User):
    id: str

# Create User
@app.post("/users/", response_model=UserInDB)
async def create_user(user: User):
    try:
        user_data = {"name": user.name, "email": user.email}
        result = user_collection.insert_one(user_data)
        user_in_db = UserInDB(**user.model_dump(), id=str(result.inserted_id))
        return user_in_db
    except DuplicateKeyError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

# Read User
@app.get("/users/{user_id}", response_model=UserInDB)
async def read_user(user_id: str):
    user_data = user_collection.find_one({"_id": ObjectId(user_id)})
    if user_data:
        user_data["id"] = str(user_data["_id"])  # Convert ObjectId to str
        return UserInDB(**user_data)
    else:
        raise HTTPException(status_code=404, detail="User not found")
    
# Update User
@app.put("/users/{user_id}", response_model=UserInDB)
async def update_user(user_id: str, updated_user: User):
    existing_user = user_collection.find_one({"_id": ObjectId(user_id)})
    if existing_user:
        # Check if the updated email is already in use by another user
        existing_user_with_updated_email = user_collection.find_one({"email": updated_user.email, "_id": {"$ne": ObjectId(user_id)}})
        if existing_user_with_updated_email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

        # Update the user data
        user_data = {"$set": {"name": updated_user.name, "email": updated_user.email}}
        user_collection.update_one({"_id": ObjectId(user_id)}, user_data)

        # Retrieve and return the updated user data
        updated_user_data = user_collection.find_one({"_id": ObjectId(user_id)})
        updated_user_data["id"] = str(updated_user_data["_id"])  # Convert ObjectId to str

        return UserInDB(**updated_user_data)

    raise HTTPException(status_code=404, detail="User not found")

# Delete User
@app.delete("/users/{user_id}", response_model=dict)
async def delete_user(user_id: str):
    result = user_collection.delete_one({"_id": ObjectId(user_id)})
    if result.deleted_count == 1:
        return {"message": "User deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="User not found")

# Search Users
@app.get("/users/", response_model=List[UserInDB])
async def search_users(name: str = None, email: str = None):
    query = {}
    if name:
        query["name"] = {"$regex": f".*{name}.*", "$options": "i"}
    if email:
        query["email"] = {"$regex": f".*{email}.*", "$options": "i"}

    users_data = user_collection.find(query)
    
    # Convert ObjectId to string and include in the response
    users_with_str_id = [
        UserInDB(**{**user, "id": str(user["_id"])}) for user in users_data
    ]
    
    return users_with_str_id

# Thread

class Thread(BaseModel):
    parents_id: str
    text: str
    user: str
    timestamp: datetime

class ThreadInDB(Thread):
    id: str

# Create a thread
@app.post("/threads", response_model=ThreadInDB)
async def create_thread(thread_data: Thread):
    # Check if parents_id exists if it is not None
    if thread_data.parents_id:
        print(thread_data.parents_id)
        existing_event_parent = event_collection.find_one({"_id": ObjectId(thread_data.parents_id)})
        existing_group_parent = group_collection.find_one({"_id": ObjectId(thread_data.parents_id)})
        if (existing_event_parent == None) and (existing_group_parent == None):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent not found")

    thread_data_dict = {**thread_data.model_dump()}
    result = thread_collection.insert_one(thread_data_dict)
    inserted_id = str(result.inserted_id)
    return ThreadInDB(id=inserted_id, **thread_data_dict)

# Read a thread by ID
@app.get("/threads/{thread_id}", response_model=ThreadInDB)
async def read_thread(thread_id: str):
    thread_data = thread_collection.find_one({"_id": ObjectId(thread_id)})
    if thread_data:
        thread_data["id"] = str(thread_data["_id"])  # Convert ObjectId to str
        return ThreadInDB(**thread_data)
    else:
        raise HTTPException(status_code=404, detail="Thread not found")

# Update a thread by ID
@app.put("/threads/{thread_id}", response_model=ThreadInDB)
async def update_thread(thread_id: str, updated_thread: Thread):
    existing_thread = thread_collection.find_one({"_id": ObjectId(thread_id)})
    if existing_thread:
        thread_data_dict = updated_thread.model_dump()
        result = thread_collection.update_one({"_id": ObjectId(thread_id)}, {"$set": thread_data_dict})
        if result.modified_count == 1:
            return ThreadInDB(id=thread_id, **thread_data_dict)
    raise HTTPException(status_code=404, detail="Thread not found")

# Delete a thread by ID
@app.delete("/threads/{thread_id}", response_model=dict)
async def delete_thread(thread_id: str):
    result = thread_collection.delete_one({"_id": ObjectId(thread_id)})
    if result.deleted_count == 1:
        return {"message": "Thread deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Thread not found")

# Search threads
@app.get("/threads", response_model=List[ThreadInDB])
async def search_threads(
    text: str = Query(None, title="Thread Text", description="Search threads by text"),
    user: str = Query(None, title="Thread User", description="Filter threads by user"),
    timestamp_from: datetime = Query(None, title="Timestamp From", description="Filter threads by timestamp from"),
    timestamp_to: datetime = Query(None, title="Timestamp To", description="Filter threads by timestamp to"),
):
    query = {}

    if text:
        query["text"] = {"$regex": text, "$options": "i"}

    if user:
        query["user"] = user

    if timestamp_from:
        query["timestamp"] = {"$gte": timestamp_from}

    if timestamp_to:
        query["timestamp"]["$lte"] = timestamp_to

    threads = thread_collection.find(query)
    return [ThreadInDB(id=str(thread["_id"]), **thread) for thread in threads]

# Message

class Message(BaseModel):
    text: str
    user: str
    timestamp: datetime
    parents: str

class MessageInDB(Message):
    thread_id:str
    id: str

# Create a message
@app.post("/threads/{thread_id}/messages", response_model=MessageInDB)
async def create_message(thread_id: str, message_data: Message):
    message_data_dict = message_data.model_dump()
    message_data_dict["thread_id"] = thread_id
    result = message_collection.insert_one(message_data_dict)
    inserted_id = str(result.inserted_id)
    return MessageInDB(id=inserted_id, **message_data_dict)

# Read messages in a thread
@app.get("/threads/{thread_id}/messages", response_model=List[MessageInDB])
async def read_messages(thread_id: str):
    messages = message_collection.find({"thread_id": thread_id})
    return [MessageInDB(id=str(message["_id"]), **message) for message in messages]

# Read a message by ID in a thread
@app.get("/threads/{thread_id}/messages/{message_id}", response_model=MessageInDB)
async def read_message(thread_id: str, message_id: str):
    message_data = message_collection.find_one({"_id": ObjectId(message_id), "thread_id": thread_id})
    if message_data:
        message_data["id"] = str(message_data["_id"])  # Convert ObjectId to str
        return MessageInDB(**message_data)
    else:
        raise HTTPException(status_code=404, detail="Message not found")

# Update a message by ID in a thread
@app.put("/threads/{thread_id}/messages/{message_id}", response_model=MessageInDB)
async def update_message(thread_id: str, message_id: str, updated_message: Message):
    existing_message = message_collection.find_one({"_id": ObjectId(message_id), "thread_id": thread_id})
    if existing_message:
        message_data_dict = updated_message.model_dump()
        result = message_collection.update_one({"_id": ObjectId(message_id)}, {"$set": message_data_dict})
        if result.modified_count == 1:
            return MessageInDB(thread_id=thread_id, id=message_id, **message_data_dict)
    raise HTTPException(status_code=404, detail="Message not found")

# Delete a message by ID in a thread
@app.delete("/threads/{thread_id}/messages/{message_id}")
async def delete_message(thread_id: str, message_id: str):
    result = message_collection.delete_one({"_id": ObjectId(message_id), "thread_id": thread_id})
    if result.deleted_count == 1:
        return {"message": "Message deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Message not found")

# Search messages in a thread
@app.get("/threads/{thread_id}/messages/search/", response_model=List[MessageInDB])
async def search_messages_in_thread(
    thread_id: str,
    text: str = Query(None, title="Message Text", description="Search messages by text"),
    user: str = Query(None, title="Message User", description="Filter messages by user"),
    timestamp_from: datetime = Query(None, title="Timestamp From", description="Filter messages by timestamp from"),
    timestamp_to: datetime = Query(None, title="Timestamp To", description="Filter messages by timestamp to"),
):
    query = {"thread_id": thread_id}

    if text:
        query["text"] = {"$regex": text, "$options": "i"}

    if user:
        query["user"] = user

    if timestamp_from:
        query["timestamp"] = {"$gte": timestamp_from}

    if timestamp_to:
        query["timestamp"]["$lte"] = timestamp_to

    messages = message_collection.find(query)
    return [MessageInDB(id=str(message["_id"]), **message) for message in messages]

# Photo Album

class PhotoAlbum(BaseModel):
    pass

class PhotoAlbumInDB(PhotoAlbum):
    id:str
    event_id:str

# Create a photo album in an event
@app.post("/events/{event_id}/photoalbum", response_model=PhotoAlbumInDB)
async def create_photo_album(event_id: str):
    # Check if the event exists
    existing_event = event_collection.find_one({"_id": ObjectId(event_id)})
    if not existing_event:
        raise HTTPException(status_code=404, detail="Event not found")

    photo_album_data = {"event_id": event_id}
    result = photo_album_collection.insert_one(photo_album_data)
    inserted_id = str(result.inserted_id)
    return PhotoAlbumInDB(id=inserted_id, **photo_album_data)

# Read photo albums in an event
@app.get("/events/{event_id}/photoalbum", response_model=List[PhotoAlbumInDB])
async def read_photo_albums(event_id: str):
    photo_albums = photo_album_collection.find({"event_id": event_id})
    return [PhotoAlbumInDB(id=str(photo_album["_id"]), **photo_album) for photo_album in photo_albums]

# Read a photo album by ID in an event
@app.get("/events/{event_id}/photoalbum/{photo_album_id}", response_model=PhotoAlbumInDB)
async def read_photo_album(event_id: str, photo_album_id: str):
    photo_album_data = photo_album_collection.find_one({"_id": ObjectId(photo_album_id), "event_id": event_id})
    if photo_album_data:
        photo_album_data["id"] = str(photo_album_data["_id"])  # Convert ObjectId to str
        return PhotoAlbumInDB(**photo_album_data)
    else:
        raise HTTPException(status_code=404, detail="Photo Album not found")

# Delete a photo album by ID in an event
@app.delete("/events/{event_id}/photoalbum/{photo_album_id}")
async def delete_photo_album(event_id: str, photo_album_id: str):
    result = photo_album_collection.delete_one({"_id": ObjectId(photo_album_id), "event_id": event_id})
    if result.deleted_count == 1:
        return {"message": "Photo Album deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Photo Album not found")
    
# Photo

class PhotoBase(BaseModel):
    user_id: str

class PhotoInDB(PhotoBase):
    id: str
    photo_album_id: str
    filename: str

# Create a photo in a photo album
@app.post("/photoalbum/{photo_album_id}/photo", response_model=PhotoInDB)
async def create_photo(
    photo_album_id: str,
    user_id: str = Body(...),
    photo: UploadFile = File(...),
):
    # Check if the photo album exists
    existing_photo_album = photo_album_collection.find_one({"_id": ObjectId(photo_album_id)})
    if not existing_photo_album:
        raise HTTPException(status_code=404, detail="Photo Album not found")
    
    existing_user = user_collection.find_one({"_id": ObjectId(user_id)})
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")

    photo_data = {
        "photo_album_id": photo_album_id,
        "user_id": user_id,
        "file": photo.file.read(),
        "filename": photo.filename,
    }
    result = photo_collection.insert_one(photo_data)
    inserted_id = str(result.inserted_id)

    # Return the created photo
    return PhotoInDB(id=inserted_id, **photo_data)

# Read photos in a photo album
@app.get("/photoalbum/{photo_album_id}/photo", response_model=List[PhotoInDB])
async def read_photos(photo_album_id: str):
    photos = photo_collection.find({"photo_album_id": photo_album_id})
    return [PhotoInDB(id=str(photo["_id"]), **photo) for photo in photos]

# Read a photo by ID in a photo album
@app.get("/photoalbum/{photo_album_id}/photo/{photo_id}")
async def read_photo(photo_album_id: str, photo_id: str):
    photo_data = photo_collection.find_one({"_id": ObjectId(photo_id), "photo_album_id": photo_album_id})
    
    if photo_data:
        return StreamingResponse(io.BytesIO(photo_data["file"]), media_type="image/jpeg")
    else:
        raise HTTPException(status_code=404, detail="Photo not found")

# Update a photo by ID in a photo album
@app.put("/photoalbum/{photo_album_id}/photo/{photo_id}", response_model=PhotoInDB)
async def update_photo(
    photo_album_id: str,
    photo_id: str,
    user_id: str = Form(...),
    photo: UploadFile = File(...),
):
    existing_photo = photo_collection.find_one({"_id": ObjectId(photo_id), "photo_album_id": photo_album_id})
    if existing_photo:
        # Update the user field
        result = photo_collection.update_one(
            {"_id": ObjectId(photo_id), "photo_album_id": photo_album_id},
            {"$set": {"user": user_id}}
        )

        if result.modified_count == 1:
            # Update the photo file if a new file is provided
            if photo:
                updated_photo_data = {
                    "file": photo.file.read(),
                    "filename": photo.filename,
                }
                result = photo_collection.update_one(
                    {"_id": ObjectId(photo_id), "photo_album_id": photo_album_id},
                    {"$set": updated_photo_data}
                )
                if result.modified_count == 1:
                    existing_photo.update(updated_photo_data)

            # Return the updated photo
            return PhotoInDB(id=photo_id, **existing_photo)

    raise HTTPException(status_code=404, detail="Photo not found")

# Delete a photo by ID in a photo album
@app.delete("/photoalbum/{photo_album_id}/photo/{photo_id}")
async def delete_photo(photo_album_id: str, photo_id: str):
    result = photo_collection.delete_one({"_id": ObjectId(photo_id), "photo_album_id": photo_album_id})
    if result.deleted_count == 1:
        return {"message": "Photo deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Photo not found")
    
# Search photos in a photo album
@app.get("/photoalbum/photo/search", response_model=List[PhotoInDB])
async def search_photos(
    photo_album_id: str = Query(None, title="photo_album_id", description="Search photos by album id"),
    user: str = Query(None, title="User", description="Search photos by user"),
    filename: str = Query(None, title="Filename", description="Search photos by filename"),
):
    query = {}
    
    # Add filters based on query parameters
    if user:
        query["user"] = {"$regex": user, "$options": "i"}
    
    if photo_album_id:
        query['photo_album_id'] = {"$regex": photo_album_id, "$options": "i"}
    
    if filename:
        query["filename"] = {"$regex": filename, "$options": "i"}

    photos = photo_collection.find(query)
    return [PhotoInDB(id=str(photo["_id"]), **photo) for photo in photos]

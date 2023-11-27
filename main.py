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

class GroupBase(BaseModel):
    name: str
    description: str
    icon: str
    cover_photo: str
    group_type: str  # Assuming group_type can be 'public', 'private', or 'secret'
    allow_members_to_publish: bool
    allow_members_to_create_events: bool
    admin: List[str] = []
    members: List[str] = []

class GroupCreate(GroupBase):
    pass

class Group(GroupBase):
    id: int

db_group_df = pd.DataFrame(columns=["id", "name", "description", "icon", "cover_photo", "group_type", "allow_members_to_publish", "allow_members_to_create_events", "admin", "members"])
group_id = 1

@app.post("/groups/", response_model=Group)
async def create_group(group: GroupCreate):
    global group_id
    new_group_data = {"id": group_id, **group.model_dump()}
    db_group_df.loc[group_id] = new_group_data
    group_id += 1
    return new_group_data

@app.get("/groups/{group_id}", response_model=Group)
async def read_group(group_id: int):
    try:
        group_data = db_group_df.loc[group_id].to_dict()
        return group_data
    except: 
        raise HTTPException(status_code=404, detail="Group not found")
    
@app.get("/groups/", response_model=List[Group])
async def read_groups(skip: int = 0, limit: int = 10):
    return db_group_df.iloc[skip : skip + limit].to_dict(orient="records")

# User

class UserBase(BaseModel):
    name: str
    email: str

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: int

db_user_df = pd.DataFrame(columns=["id", "name", "email"])
user_id = 1

@app.post("/users/", response_model=User)
async def create_user(user: UserCreate):
    global user_id
    new_user_data = {"id": user_id, **user.model_dump()}
    db_user_df.loc[user_id] = new_user_data
    user_id += 1
    return new_user_data

@app.get("/users/{user_id}", response_model=User)
async def read_user(user_id: int):
    try:
        user_data = db_user_df.loc[user_id].to_dict()
        return user_data
    except:
        raise HTTPException(status_code=404, detail="User not found")

@app.get("/users/", response_model=List[User])
async def read_users(skip: int = 0, limit: int = 10):
    return db_user_df.iloc[skip : skip + limit].to_dict(orient="records")

# Thread / Message

class MessageBase(BaseModel):
    text: str
    user: str
    timestamp: datetime
    parents: str

class MessageCreate(MessageBase):
    pass

class Message(MessageBase):
    id: str

class ThreadBase(BaseModel):
    text: str
    user: str
    timestamp: datetime
    messages: List[Message] = []

class ThreadCreate(ThreadBase):
    pass

class Thread(ThreadBase):
    id: str

db_threads = {}
thread_id = 1

@app.post("/threads/", response_model=Thread)
async def create_thread(thread: ThreadCreate):
    global thread_id
    new_thread_data = {"id": f"{thread_id}", **thread.model_dump()}
    db_threads[f"{thread_id}"] = new_thread_data
    thread_id += 1
    return Thread(**new_thread_data)

@app.get("/threads/{thread_id}", response_model=Thread)
async def read_thread(thread_id: str):
    thread_data = db_threads.get(thread_id)
    if thread_data is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread_data

@app.get("/threads/{thread_id}/messages/{message_id}", response_model=Message)
async def read_message_in_thread(thread_id: str, message_id: str):
    thread_data = db_threads.get(thread_id)
    if thread_data is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    message_data = next((msg for msg in thread_data["messages"] if msg["id"] == message_id), None)
    if message_data is None:
        raise HTTPException(status_code=404, detail="Message not found in thread")

    return message_data

@app.post("/threads/{thread_id}/messages/", response_model=Message)
async def create_message_in_thread(thread_id: str, message: MessageCreate):
    thread_data = db_threads.get(thread_id)
    if thread_data is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    new_message_data = {
        "id": f"{len(thread_data['messages']) + 1}",
        **message.model_dump(),
    }
    thread_data["messages"].append(new_message_data)
    return new_message_data

# photo NOT FINISH
################################
################################
################################

class PhotoBase(BaseModel):
    user: str


class Photo(PhotoBase):
    id: str
    
class PhotoCreate(PhotoBase):
    pass

class Photo(PhotoBase):
    id: str

class PhotoAlbumBase(BaseModel):
    event_id: str
    photos: List[Photo] = []

class PhotoAlbumCreate(PhotoAlbumBase):
    pass

class PhotoAlbum(PhotoAlbumBase):
    id: str

db_photo_album = {}
photo_album_id = 1

@app.post("/photoalbum/", response_model=PhotoAlbum)
async def create_photo_album(photo_album: PhotoAlbumCreate):
    global photo_album_id
    new_photo_album_data = {"id": f"{photo_album_id}", **photo_album.model_dump()}
    db_photo_album[f"{photo_album_id}"] = new_photo_album_data
    photo_album_id += 1
    return PhotoAlbum(**new_photo_album_data)

@app.get("/photoalbum/{photo_album_id}", response_model=PhotoAlbum)
async def read_photo_album(photo_album_id: str):
    photo_album_data = db_photo_album.get(photo_album_id)
    if photo_album_data is None:
        raise HTTPException(status_code=404, detail="Photo album not found")
    return photo_album_data

# Endpoint to handle photo uploads
@app.post("/photoalbum/{photo_album_id}/photo/")
async def upload_photo(photo_album_id: str, filename: UploadFile = File(...), user:str = Form(...)):
    photo_album_data = db_photo_album.get(photo_album_id)
    if photo_album_data is None:
        raise HTTPException(status_code=404, detail="Photo album not found")
    
    new_photo_album_data = {
        "id": f"{len(photo_album_data['photos']) + 1}",
        "user":user,
    }
    photo_album_data["photos"].append(new_photo_album_data)
    # Do whatever processing you need with the uploaded file
    # For example, save it to a specific directory
    with open(f"photo/{photo_album_id}_{new_photo_album_data['id']}.png", "wb") as f:
        f.write(filename.file.read())

    return {"message": "Photo uploaded successfully"}

################################
################################
################################

# pool
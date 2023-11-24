from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import pandas as pd
from datetime import datetime

app = FastAPI()

# Event

class EventBase(BaseModel):
    name: str
    description: str
    start_date: str
    end_date: str
    location: str
    cover_photo: str
    is_private: bool
    organizers: List[str] = []
    members: List[str] = []

class EventCreate(EventBase):
    pass

class Event(EventBase):
    id: int

db_event = []
event_id = 1

@app.post("/events/", response_model=Event)
async def create_event(event: EventCreate):
    global event_id
    new_event = Event(**event.model_dump(), id=event_id)
    event_id += 1
    db_event.append(new_event)
    return new_event

@app.get("/events/{event_id}", response_model=Event)
async def read_event(event_id: int):
    event = next((e for e in db_event if e.id == event_id), None)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event

@app.get("/events/", response_model=List[Event])
async def read_events(skip: int = 0, limit: int = 10):
    return db_event[skip: skip + limit]


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

class MessageBase(BaseModel):
    text: str
    user: str
    timestamp: datetime

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
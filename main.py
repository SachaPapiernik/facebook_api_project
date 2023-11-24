from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

app = FastAPI()

#Event

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
    db.append(new_event)
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


#Group

class GroupBase(BaseModel):
    name: str
    description: str
    icon: str
    cover_photo: str
    group_type: str  # Assuming group_type can be 'public', 'private', or 'secret'
    allow_members_to_publish: bool
    allow_members_to_create_events: bool

class GroupCreate(GroupBase):
    pass

class Group(GroupBase):
    id: int

db_group = []
group_id = 1

@app.post("/groups/", response_model=Group)
async def create_group(group: GroupCreate):
    global group_id
    new_group = Group(**group.model_dump(), id=group_id)
    group_id += 1
    db_group.append(new_group)
    return new_group

@app.get("/groups/{group_id}", response_model=Group)
async def read_group(group_id: int):
    group = next((g for g in db_group if g.id == group_id), None)
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    return group

@app.get("/groups/", response_model=List[Group])
async def read_groups(skip: int = 0, limit: int = 10):
    return db_group[skip : skip + limit]
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

app = FastAPI()

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

db = []
event_id = 1

@app.post("/events/", response_model=Event)
async def create_event(event: EventCreate):
    global event_id
    new_event = Event(**event.dict(), id=event_id)
    event_id += 1
    db.append(new_event)
    return new_event

@app.get("/events/{event_id}", response_model=Event)
async def read_event(event_id: int):
    event = next((e for e in db if e.id == event_id), None)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event

@app.get("/events/", response_model=List[Event])
async def read_events(skip: int = 0, limit: int = 10):
    return db[skip: skip + limit]
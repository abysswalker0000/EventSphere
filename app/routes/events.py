from fastapi import APIRouter, HTTPException
from app.schemas.event import NewEvent

router = APIRouter()

events = [
    {
        "id": 1,
        "title": "rave",
        "author": "Bless",
    },
    {
        "id": 2,
        "title": "BBQ",
        "author": "Jay-Z",
    },
]

@router.get("/", tags=["Events"], summary="Get all events")
def get_events():
    return events

@router.get("/{event_id}", tags=["Events"], summary="Get specific event")
def get_event_by_id(event_id: int):
    for event in events:
        if event["id"] == event_id:
            return event
    raise HTTPException(status_code=404, detail="Event doesnt exist")

@router.post("/", tags=["Events"])
def create_event(new_event: NewEvent):
    events.append({
        "id": len(events) + 1,
        "title": new_event.title,
        "author": new_event.author, 
    })
    return {"succes": True, "message": "Event added successfully"}
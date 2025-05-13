from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.event import EventSchema
from app.models.event import Event
from app.database import get_db
from sqlalchemy import select

router = APIRouter()

@router.get("/", tags=["Events"], summary="Get all events")
async def get_events(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Event))
    events = result.scalars().all()
    return events

@router.get("/{event_id}", tags=["Events"], summary="Get specific event")
async def get_event_by_id(event_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Event).filter(Event.id == event_id))
    event = result.scalars().first()
    if not event:
        raise HTTPException(status_code=404, detail="Event doesn't exist")
    return event

@router.post("/", tags=["Events"])
async def create_event(new_event: EventSchema, db: AsyncSession = Depends(get_db)):
    db_event = Event(title=new_event.title, author_id=new_event.author_id, event_date = new_event.event_time, category_id = new_event.category_id )
    db.add(db_event)
    await db.commit()
    await db.refresh(db_event)
    return {"success": True, "message": "Event added successfully"}
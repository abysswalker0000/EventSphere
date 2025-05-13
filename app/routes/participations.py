from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.participation import ParticipationCreateSchema, ParticipationSchema
from app.models.participation import Participation
from app.database import get_db
from sqlalchemy import select

router = APIRouter()

@router.post("/", tags=["Participations"], summary="Add new participation")
async def add_participation(participation: ParticipationCreateSchema, db:AsyncSession = Depends(get_db)):
    db_participation = Participation(
        user_id=participation.user_id,
        event_id=participation.event_id,
        status=participation.status)
    db.add(db_participation)
    await db.commit()
    await db.refresh(db_participation)
    return {"ok": True, "message": "Participation added successfully"}

@router.get("/", tags=["Participations"], summary="Get all participations")
async def get_participations(db:AsyncSession = Depends(get_db)):
    result = await db.execute(select(Participation))
    participations = result.scalars().all()
    return participations
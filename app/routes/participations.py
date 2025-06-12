from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, func, delete as sqlalchemy_delete
from typing import List, Optional
import logging

from app.schemas.participation import (
    ParticipationCreateExplicitSchema,
    ParticipationSetStatusSchema,
    ParticipationResponseSchema,
    ParticipationWithUserInfoResponseSchema,
    ParticipationWithEventInfoResponseSchema,
    StatusVariation
)
from app.models.participation import Participation
from app.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/participations",
    tags=["Participations"]
)

@router.post(
    "/",
    response_model=ParticipationResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update a participation record (explicit IDs)"
)
async def create_or_update_participation_explicit(
    participation_data: ParticipationCreateExplicitSchema,
    db: AsyncSession = Depends(get_db)
):
    existing_participation_result = await db.execute(
        select(Participation).where(
            Participation.user_id == participation_data.user_id,
            Participation.event_id == participation_data.event_id
        )
    )
    db_participation = existing_participation_result.scalars().first()

    if db_participation:
        db_participation.status = participation_data.status
        action = "updated"
    else:
        db_participation = Participation(
            user_id=participation_data.user_id,
            event_id=participation_data.event_id,
            status=participation_data.status
        )
        db.add(db_participation)
        action = "created"
    
    try:
        await db.commit()
        await db.refresh(db_participation)
    except IntegrityError as e_integrity:
        await db.rollback()
        logger.warning(
            f"IntegrityError {action} participation for user_id {participation_data.user_id}, event_id {participation_data.event_id}: {str(e_integrity)}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Could not {action} participation due to a data conflict (e.g., invalid user_id or event_id)."
        )
    except Exception as e_general:
        await db.rollback()
        logger.error(
            f"Unexpected error {action} participation for user_id {participation_data.user_id}, event_id {participation_data.event_id}: {str(e_general)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while {action} the participation."
        )
    
    logger.info(f"Participation for user_id {db_participation.user_id}, event_id {db_participation.event_id} successfully {action} with status '{db_participation.status.value}'.")
    return db_participation

@router.get(
    "/",
    response_model=List[ParticipationResponseSchema],
    summary="Get all participation records (admin, paginated)"
)
async def get_all_participations(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    try:
        result = await db.execute(select(Participation).offset(skip).limit(limit).order_by(Participation.joined_at.desc()))
        participations = result.scalars().all()
        return participations
    except Exception as e:
        logger.error(f"Error fetching all participations: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching participation records."
        )

@router.get(
    "/event/{event_id}/users",
    response_model=List[ParticipationWithUserInfoResponseSchema], 
    summary="Get users participating in a specific event"
)
async def get_event_participants(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    status_filter: Optional[StatusVariation] = None,
    skip: int = 0,
    limit: int = 100
):
    query = select(Participation).where(Participation.event_id == event_id)
    if status_filter:
        query = query.where(Participation.status == status_filter)
    query = query.offset(skip).limit(limit).order_by(Participation.joined_at.desc())
    try:
        result = await db.execute(query)
        participations = result.scalars().all()
        return participations 
    except Exception as e:
        logger.error(f"Error fetching participants for event_id {event_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching participants for event {event_id}."
        )

@router.get(
    "/user/{user_id}/events",
    response_model=List[ParticipationWithEventInfoResponseSchema], 
    summary="Get events a specific user is participating in"
)
async def get_user_participations(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    status_filter: Optional[StatusVariation] = None,
    skip: int = 0,
    limit: int = 100
):
    query = select(Participation).where(Participation.user_id == user_id)
    if status_filter:
        query = query.where(Participation.status == status_filter)
    query = query.offset(skip).limit(limit).order_by(Participation.joined_at.desc())
    try:
        result = await db.execute(query)
        participations = result.scalars().all()
        return participations
    except Exception as e:
        logger.error(f"Error fetching participations for user_id {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching participations for user {user_id}."
        )

@router.get(
    "/{participation_id}",
    response_model=ParticipationResponseSchema,
    summary="Get a specific participation record by ID"
)
async def get_participation_by_id(participation_id: int, db: AsyncSession = Depends(get_db)):
    participation: Participation | None = None
    try:
        result = await db.execute(select(Participation).filter(Participation.id == participation_id))
        participation = result.scalars().first()
    except Exception as e:
        logger.error(f"Error fetching participation with id {participation_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching participation record {participation_id}."
        )
    
    if not participation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Participation record with id {participation_id} not found."
        )
    return participation

@router.delete(
    "/{participation_id}",
    summary="Delete a specific participation record",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_participation_record(participation_id: int, db: AsyncSession = Depends(get_db)):
    db_participation: Participation | None = None
    try:
        result = await db.execute(select(Participation).filter(Participation.id == participation_id))
        db_participation = result.scalars().first()

        if not db_participation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Participation record with id {participation_id} not found to delete."
            )

        await db.delete(db_participation)
        await db.commit()
        
        logger.info(f"Participation record (ID: {participation_id}) for user_id {db_participation.user_id}, event_id {db_participation.event_id} deleted successfully.")
        return None

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        user_event_info = f"user_id {db_participation.user_id if db_participation else 'N/A'}, event_id {db_participation.event_id if db_participation else 'N/A'}"
        logger.error(
            f"Error deleting participation record with id {participation_id} ({user_event_info}): {str(e)}", 
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while deleting participation record {participation_id}."
        )

@router.put(
    "/user/{user_id}/event/{event_id}",
    response_model=ParticipationResponseSchema,
    summary="Set or update participation status for a user in an event"
)
async def set_participation_status(
    user_id: int,
    event_id: int,
    status_data: ParticipationSetStatusSchema,
    db: AsyncSession = Depends(get_db)
):
    existing_participation_result = await db.execute(
        select(Participation).where(
            Participation.user_id == user_id,
            Participation.event_id == event_id
        )
    )
    db_participation = existing_participation_result.scalars().first()

    action = ""
    if db_participation:
        db_participation.status = status_data.status
        action = "updated"
    else:
        db_participation = Participation(
            user_id=user_id,
            event_id=event_id,
            status=status_data.status
        )
        db.add(db_participation)
        action = "created"
    
    try:
        await db.commit()
        await db.refresh(db_participation)
    except IntegrityError as e_integrity:
        await db.rollback()
        logger.warning(
            f"IntegrityError {action} participation for user_id {user_id}, event_id {event_id} with status '{status_data.status.value}': {str(e_integrity)}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Could not {action} participation due to a data conflict."
        )
    except Exception as e_general:
        await db.rollback()
        logger.error(
            f"Unexpected error {action} participation for user_id {user_id}, event_id {event_id} with status '{status_data.status.value}': {str(e_general)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while {action} the participation."
        )
    
    logger.info(f"Participation for user_id {user_id}, event_id {event_id} successfully {action} with status '{db_participation.status.value}'.")
    return db_participation
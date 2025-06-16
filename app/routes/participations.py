from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select # func не используется в этом варианте, но может понадобиться для агрегации
from typing import List, Optional
import logging

from app.database import get_db
from app.models.participation import Participation
from app.models.user import User
from app.models.event import Event 
from app.schemas.participation import (
    ParticipationCreateExplicitSchema, 
    ParticipationSetStatusSchema,    
    ParticipationResponseSchema,
    ParticipationWithUserInfoResponseSchema,
    ParticipationWithEventInfoResponseSchema,
    StatusVariation
)
from app.auth.dependencies import get_current_active_user, get_current_admin_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/participations",
    tags=["Participations"]
)
@router.post(
    "/admin_set_participation", 
    response_model=ParticipationResponseSchema,
    status_code=status.HTTP_201_CREATED, 
    summary="Admin: Create or update a participation record with explicit IDs",
    dependencies=[Depends(get_current_admin_user)]
)
async def admin_create_or_update_participation(
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
    action = ""
    if db_participation:
        db_participation.status = participation_data.status
        action = "updated by admin"
    else:
        db_participation = Participation(
            user_id=participation_data.user_id,
            event_id=participation_data.event_id,
            status=participation_data.status
        )
        db.add(db_participation)
        action = "created by admin"
    
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


@router.put(
    "/event/{event_id}/my_status", 
    response_model=ParticipationResponseSchema,
    summary="Set or update current user's participation status for an event"
)
async def set_my_participation_status(
    event_id: int,
    status_data: ParticipationSetStatusSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    event_check = await db.get(Event, event_id)
    if not event_check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Event with id {event_id} not found.")

    existing_participation_result = await db.execute(
        select(Participation).where(
            Participation.user_id == current_user.id,
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
            user_id=current_user.id,
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
            f"IntegrityError {action} participation for current user_id {current_user.id}, event_id {event_id} with status '{status_data.status.value}': {str(e_integrity)}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, \
            detail=f"Could not {action} participation due to a data conflict."
        )
    except Exception as e_general:
        await db.rollback()
        logger.error(
            f"Unexpected error {action} participation for current user_id {current_user.id}, event_id {event_id} with status '{status_data.status.value}': {str(e_general)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while {action} the participation."
        )
    
    logger.info(f"Participation for user_id {current_user.id}, event_id {event_id} successfully {action} with status '{db_participation.status.value}'.")
    return db_participation

@router.get(
    "/",
    response_model=List[ParticipationResponseSchema],
    summary="Get all participation records (Admin only, paginated)",
    dependencies=[Depends(get_current_admin_user)]
)
async def get_all_participations_admin(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    try:
        result = await db.execute(select(Participation).offset(skip).limit(limit).order_by(Participation.joined_at.desc()))
        participations = result.scalars().all()
        return participations
    except Exception as e:
        logger.error(f"Error fetching all participations (admin): {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching participation records."
        )

@router.get(
    "/event/{event_id}/users",
    response_model=List[ParticipationWithUserInfoResponseSchema], 
    summary="Get users participating in a specific event (Authenticated)",
    dependencies=[Depends(get_current_active_user)] 
)
async def get_event_participants_public( 
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
    "/user/me/events", 
    response_model=List[ParticipationWithEventInfoResponseSchema], 
    summary="Get events current user is participating in"
)
async def get_my_participations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    status_filter: Optional[StatusVariation] = None,
    skip: int = 0,
    limit: int = 100
):
    query = select(Participation).where(Participation.user_id == current_user.id)
    if status_filter:
        query = query.where(Participation.status == status_filter)
    query = query.offset(skip).limit(limit).order_by(Participation.joined_at.desc())
    try:
        result = await db.execute(query)
        participations = result.scalars().all()
        return participations
    except Exception as e:
        logger.error(f"Error fetching participations for current user_id {current_user.id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching participations for the current user."
        )


@router.get(
    "/user/{user_id}/events",
    response_model=List[ParticipationWithEventInfoResponseSchema], 
    summary="Get events a specific user is participating in (Admin only)",
    dependencies=[Depends(get_current_admin_user)]
)
async def get_user_participations_admin(
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
        logger.error(f"Error fetching participations for user_id {user_id} (admin access): {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching participations for user {user_id}."
        )

@router.get(
    "/{participation_id}",
    response_model=ParticipationResponseSchema,
    summary="Get a specific participation record by ID (Admin or Owner)"
)
async def get_participation_by_id_restricted( 
    participation_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
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
    
    if participation.user_id != current_user.id and current_user.role != "admin":
        logger.warning(f"User ID {current_user.id} (role: {current_user.role}) attempted to access participation record ID {participation_id} owned by user ID {participation.user_id}.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this participation record."
        )
    return participation

@router.delete(
    "/{participation_id}",
    summary="Delete a specific participation record (Admin or Owner)",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_participation_record_restricted(
    participation_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    db_participation: Participation | None = None
    try:
        result = await db.execute(select(Participation).filter(Participation.id == participation_id))
        db_participation = result.scalars().first()

        if not db_participation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Participation record with id {participation_id} not found to delete."
            )

        is_owner = db_participation.user_id == current_user.id
        is_admin = current_user.role == "admin"

        if not (is_owner or is_admin):
            logger.warning(f"User ID {current_user.id} (role: {current_user.role}) attempted to delete participation record ID {participation_id} owned by user ID {db_participation.user_id}.")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this participation record."
            )

        user_event_info = f"user_id {db_participation.user_id}, event_id {db_participation.event_id}"
        await db.delete(db_participation)
        await db.commit()
        
        deleted_by_role = "admin" if is_admin and not is_owner else "owner"
        logger.info(f"Participation record (ID: {participation_id}) for {user_event_info} deleted successfully by {deleted_by_role} (current_user ID: {current_user.id}).")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

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
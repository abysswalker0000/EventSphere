from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, func
from typing import List, Optional
from datetime import date
import logging

from app.database import get_db
from app.models.event import Event
from app.models.user import User 
from app.schemas.event import (
    EventCreateSchema,
    EventUpdateSchema,
    EventResponseSchema
)
from app.auth.dependencies import get_current_active_user, get_current_admin_user, get_current_organizer_user
from sqlalchemy.orm import selectinload 

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/events",
    tags=["Events"]
)

@router.post(
    "/",
    response_model=EventResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new event (Organizer or Admin only)"
)
async def create_event(
    event_data: EventCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_organizer_user)
):
    db_event = Event(
        title=event_data.title,
        description=event_data.description,
        author_id=current_user.id, 
        event_date=event_data.event_date,
        category_id=event_data.category_id
    )
    db.add(db_event)
    try:
        await db.commit()
        await db.refresh(db_event)
        logger.info(f"Event '{db_event.title}' created by user ID {current_user.id}")
    except IntegrityError as e_integrity:
        await db.rollback()
        logger.warning(
            f"IntegrityError creating event with title '{event_data.title}' by user ID {current_user.id}: {str(e_integrity)}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not create event due to a data conflict (e.g., invalid category_id)."
        )
    except Exception as e_general:
        await db.rollback()
        logger.error(
            f"Unexpected error creating event with title '{event_data.title}' by user ID {current_user.id}: {str(e_general)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the event."
        )
    return db_event

@router.get(
    "/",
    response_model=List[EventResponseSchema],
    summary="Get all events with filtering and pagination (Public)"
)
async def get_all_events_public( 
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    category_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    author_id: Optional[int] = None
):
    query = select(Event)
    if category_id is not None:
        query = query.where(Event.category_id == category_id)
    if date_from is not None:
        query = query.where(Event.event_date >= date_from)
    if date_to is not None:
        query = query.where(Event.event_date <= date_to)
    if author_id is not None:
        query = query.where(Event.author_id == author_id)
    
    query = query.offset(skip).limit(limit).order_by(Event.event_date.desc())

    try:
        result = await db.execute(query)
        events = result.scalars().all()
        return events
    except Exception as e:
        logger.error(f"Error fetching events: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching events."
        )

@router.get(
    "/{event_id}",
    response_model=EventResponseSchema,
    summary="Get a specific event by ID (Public)"
)
async def get_event_by_id_public( 
    event_id: int, 
    db: AsyncSession = Depends(get_db)
):
    event: Event | None = None
    try:
        result = await db.execute(select(Event).filter(Event.id == event_id))
        event = result.scalars().first()
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event with id {event_id} not found."
            )
        return event
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching event with id {event_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching event {event_id}."
        )

@router.patch(
    "/{event_id}",
    response_model=EventResponseSchema,
    summary="Update an event (Author or Admin only)"
)
async def update_event(
    event_id: int,
    event_update_data: EventUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user) 
):
    db_event: Event | None = None
    update_payload_str = event_update_data.model_dump_json(exclude_unset=True) 
    try:
        result = await db.execute(select(Event).filter(Event.id == event_id))
        db_event = result.scalars().first()

        if not db_event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event with id {event_id} not found to update."
            )
        
        if db_event.author_id != current_user.id and current_user.role != "admin":
            logger.warning(f"User ID {current_user.id} (role: {current_user.role}) attempted to update event ID {event_id} owned by user ID {db_event.author_id}.")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this event."
            )
        
        updated_data = event_update_data.model_dump(exclude_unset=True)
        if not updated_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields provided for update."
            )

        for key, value in updated_data.items():
            setattr(db_event, key, value)
        
        await db.commit()
        await db.refresh(db_event)
        logger.info(f"Event ID {event_id} (title: '{db_event.title}') updated by user ID {current_user.id}.")
        return db_event
        
    except IntegrityError as e_integrity:
        await db.rollback()
        logger.warning(
            f"IntegrityError updating event id {event_id} with payload {update_payload_str}: {str(e_integrity)}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not update event due to a data conflict (e.g., invalid category_id)."
        )
    except HTTPException:
        raise
    except Exception as e_general:
        await db.rollback()
        event_title_for_log = db_event.title if db_event else "N/A"
        logger.error(
            f"Unexpected error updating event id {event_id} (title: {event_title_for_log}) with payload {update_payload_str}: {str(e_general)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while updating event {event_id}."
        )

@router.delete(
    "/{event_id}",
    summary="Delete an event (Author or Admin only)",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_event(
    event_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    db_event_to_delete: Event | None = None
    try:
        result = await db.execute(select(Event).filter(Event.id == event_id))
        db_event_to_delete = result.scalars().first()

        if not db_event_to_delete:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event with id {event_id} not found to delete."
            )

        if db_event_to_delete.author_id != current_user.id and current_user.role != "admin":
            logger.warning(f"User ID {current_user.id} (role: {current_user.role}) attempted to delete event ID {event_id} owned by user ID {db_event_to_delete.author_id}.")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this event."
            )
        event_title_for_log = db_event_to_delete.title
        await db.delete(db_event_to_delete)
        await db.commit()
        
        logger.info(f"Event '{event_title_for_log}' (ID: {event_id}) deleted successfully by user ID {current_user.id}.")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except HTTPException:
        raise
    except IntegrityError as e_integrity: 
        await db.rollback()
        event_title_for_log = db_event_to_delete.title if db_event_to_delete else "N/A"
        logger.error(
            f"IntegrityError deleting event id {event_id} (title: {event_title_for_log}): {str(e_integrity)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete event {event_id} as it is referenced by other entities that prevent deletion."
        )
    except Exception as e:
        await db.rollback()
        event_title_for_log = db_event_to_delete.title if db_event_to_delete else "N/A"
        logger.error(
            f"Error deleting event with id {event_id} (title: {event_title_for_log}): {str(e)}", 
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while deleting event {event_id}."
        )
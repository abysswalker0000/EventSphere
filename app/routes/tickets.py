from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from typing import List
import logging

from app.database import get_db
from app.models.tickets import Ticket
from app.models.user import User
from app.models.event import Event
from app.schemas.tickets import TicketCreateSchema, TicketResponseSchema, TicketUpdateSchema

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/tickets",
    tags=["Tickets"]
)

@router.post(
    "/",
    response_model=TicketResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new ticket"
)
async def create_ticket(
    new_ticket: TicketCreateSchema,
    db: AsyncSession = Depends(get_db)
):
    try:
        # Check if user exists
        user_result = await db.execute(select(User).filter(User.id == new_ticket.user_id))
        if not user_result.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User with id {new_ticket.user_id} does not exist."
            )
        
        # Check if event exists
        event_result = await db.execute(select(Event).filter(Event.id == new_ticket.event_id))
        if not event_result.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Event with id {new_ticket.event_id} does not exist."
            )

        db_ticket = Ticket(
            user_id=new_ticket.user_id,
            event_id=new_ticket.event_id,
            price=new_ticket.price
        )
        db.add(db_ticket)
        await db.commit()
        await db.refresh(db_ticket)
        logger.info(f"Ticket (ID: {db_ticket.id}) created for user_id {new_ticket.user_id}, event_id {new_ticket.event_id}.")
        return db_ticket

    except IntegrityError as e_integrity:
        await db.rollback()
        logger.warning(
            f"IntegrityError creating ticket for user_id {new_ticket.user_id}, event_id {new_ticket.event_id}: {str(e_integrity)}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not create ticket due to a data conflict (e.g., duplicate ticket or invalid IDs)."
        )
    except HTTPException:
        raise
    except Exception as e_general:
        await db.rollback()
        logger.error(
            f"Unexpected error creating ticket for user_id {new_ticket.user_id}, event_id {new_ticket.event_id}: {str(e_general)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the ticket."
        )

@router.get(
    "/user/{user_id}",
    response_model=List[TicketResponseSchema],
    summary="Get all tickets for a specific user"
)
async def get_tickets_for_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    try:
        result = await db.execute(
            select(Ticket)
            .where(Ticket.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .order_by(Ticket.purchased_at.desc())
        )
        tickets = result.scalars().all()
        if not tickets:
            logger.info(f"No tickets found for user_id {user_id}.")
        return tickets
    except Exception as e:
        logger.error(f"Error fetching tickets for user_id {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching tickets for user {user_id}."
        )

@router.get(
    "/event/{event_id}",
    response_model=List[TicketResponseSchema],
    summary="Get all tickets for a specific event"
)
async def get_tickets_for_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    try:
        result = await db.execute(
            select(Ticket)
            .where(Ticket.event_id == event_id)
            .offset(skip)
            .limit(limit)
            .order_by(Ticket.purchased_at.desc())
        )
        tickets = result.scalars().all()
        if not tickets:
            logger.info(f"No tickets found for event_id {event_id}.")
        return tickets
    except Exception as e:
        logger.error(f"Error fetching tickets for event_id {event_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching tickets for event {event_id}."
        )

@router.delete(
    "/{ticket_id}",
    summary="Delete a ticket by its ID",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db)
):
    db_ticket: Ticket | None = None
    try:
        result = await db.execute(select(Ticket).filter(Ticket.id == ticket_id))
        db_ticket = result.scalars().first()
        if not db_ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticket with id {ticket_id} not found."
            )
        await db.delete(db_ticket)
        await db.commit()
        logger.info(f"Ticket (ID: {ticket_id}) deleted successfully for user_id {db_ticket.user_id}, event_id {db_ticket.event_id}.")
        return None
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(
            f"Error deleting ticket with id {ticket_id}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while deleting ticket with id {ticket_id}."
        )

@router.get(
    "/{ticket_id}",
    response_model=TicketResponseSchema,
    summary="Get a specific ticket by ID"
)
async def get_ticket_by_id(
    ticket_id: int,
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(select(Ticket).filter(Ticket.id == ticket_id))
        ticket = result.scalars().first()
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticket with id {ticket_id} not found."
            )
        return ticket
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching ticket with id {ticket_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching ticket {ticket_id}."
        )

@router.patch(
    "/{ticket_id}",
    response_model=TicketResponseSchema,
    summary="Update ticket price"
)
async def update_ticket(
    ticket_id: int,
    ticket_update: TicketUpdateSchema,
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(select(Ticket).filter(Ticket.id == ticket_id))
        db_ticket = result.scalars().first()
        if not db_ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticket with id {ticket_id} not found."
            )
        updated_data = ticket_update.model_dump(exclude_unset=True)
        if not updated_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields provided to update."
            )
        for key, value in updated_data.items():
            setattr(db_ticket, key, value)
        await db.commit()
        await db.refresh(db_ticket)
        logger.info(f"Ticket (ID: {ticket_id}) updated successfully for user_id {db_ticket.user_id}, event_id {db_ticket.event_id}.")
        return db_ticket
    except IntegrityError as e_integrity:
        await db.rollback()
        logger.warning(
            f"IntegrityError updating ticket id {ticket_id} with data {updated_data}: {str(e_integrity)}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot update ticket due to a data conflict."
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(
            f"Error updating ticket id {ticket_id} with data {updated_data}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while updating ticket {ticket_id}."
        )

@router.get(
    "/event/{event_id}/count",
    summary="Get the number of tickets for a specific event"
)
async def get_tickets_count_for_event(
    event_id: int,
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(
            select(func.count(Ticket.id)).where(Ticket.event_id == event_id)
        )
        ticket_count = result.scalar_one_or_none() or 0
        logger.info(f"Retrieved ticket count ({ticket_count}) for event_id {event_id}.")
        return {"event_id": event_id, "ticket_count": ticket_count}
    except Exception as e:
        logger.error(f"Error fetching ticket count for event_id {event_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching ticket count for event {event_id}."
        )

@router.get(
    "/",
    response_model=List[TicketResponseSchema],
    summary="Get all tickets (admin, paginated)"
)
async def get_all_tickets(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    try:
        result = await db.execute(
            select(Ticket)
            .offset(skip)
            .limit(limit)
            .order_by(Ticket.purchased_at.desc())
        )
        tickets = result.scalars().all()
        if not tickets:
            logger.info("No tickets found.")
        return tickets
    except Exception as e:
        logger.error(f"Error fetching all tickets: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching all tickets."
        )
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, func 
from typing import List, Optional
from decimal import Decimal
import logging
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.tickets import Ticket
from app.models.user import User
from app.models.event import Event
from app.schemas.tickets import (
    TicketPurchaseSchema,
    TicketCreateAdminSchema,
    TicketUpdateAdminSchema,
    TicketResponseSchema
)
from app.auth.dependencies import get_current_active_user, get_current_admin_user, get_current_organizer_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/tickets",
    tags=["Tickets"]
)


@router.post(
    "/purchase", 
    response_model=TicketResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Purchase a ticket for an event (Authenticated User)"
)
async def purchase_ticket(
    event_id_to_purchase: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    event = await db.get(Event, event_id_to_purchase)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Event with id {event_id_to_purchase} not found.")
    ticket_price = getattr(event, 'ticket_price', Decimal("10.00")) # ЗАГЛУШКА ЦЕНЫ
    if ticket_price is None: 
        ticket_price = Decimal("0.00")


    db_ticket = Ticket(
        user_id=current_user.id,
        event_id=event_id_to_purchase,
        price=ticket_price 
    )
    db.add(db_ticket)
    try:
        await db.commit()
        await db.refresh(db_ticket)
        logger.info(f"Ticket (ID: {db_ticket.id}) purchased by user_id {current_user.id} for event_id {event_id_to_purchase}.")
    except IntegrityError as e_integrity: 
        await db.rollback()
        logger.warning(
            f"IntegrityError purchasing ticket for user_id {current_user.id}, event_id {event_id_to_purchase}: {str(e_integrity)}"
        )
        if "uq_user_event_ticket" in str(e_integrity).lower():
            detail_msg = "You have already purchased a ticket for this event."
        else:
            detail_msg = "Could not purchase ticket due to a data conflict (e.g., invalid event_id)."
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail_msg)
    except Exception as e_general:
        await db.rollback()
        logger.error(
            f"Unexpected error purchasing ticket for user_id {current_user.id}, event_id {event_id_to_purchase}: {str(e_general)}",
            exc_info=True
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")
    return db_ticket

@router.post(
    "/admin_create", 
    response_model=TicketResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Admin: Create a new ticket with explicit details",
    dependencies=[Depends(get_current_admin_user)]
)
async def create_ticket_by_admin(
    ticket_data: TicketCreateAdminSchema,
    db: AsyncSession = Depends(get_db)
):
    user_check = await db.get(User, ticket_data.user_id)
    if not user_check:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"User with id {ticket_data.user_id} does not exist.")
    event_check = await db.get(Event, ticket_data.event_id)
    if not event_check:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Event with id {ticket_data.event_id} does not exist.")

    db_ticket = Ticket(
        user_id=ticket_data.user_id,
        event_id=ticket_data.event_id,
        price=ticket_data.price
    )
    db.add(db_ticket)
    try:
        await db.commit()
        await db.refresh(db_ticket)
        logger.info(f"Admin created Ticket (ID: {db_ticket.id}) for user_id {ticket_data.user_id}, event_id {ticket_data.event_id}.")
    except IntegrityError as e_integrity:
        await db.rollback()
        logger.warning(
            f"IntegrityError (admin) creating ticket {ticket_data.model_dump()}: {str(e_integrity)}"
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Could not create ticket due to data conflict.")
    except Exception as e_general:
        await db.rollback()
        logger.error(
            f"Unexpected error (admin) creating ticket {ticket_data.model_dump()}: {str(e_general)}", exc_info=True
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")
    return db_ticket

@router.get(
    "/user/me", 
    response_model=List[TicketResponseSchema],
    summary="Get all tickets for the current authenticated user"
)
async def get_my_tickets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    skip: int = 0,
    limit: int = 100
):
    try:
        result = await db.execute(
            select(Ticket).where(Ticket.user_id == current_user.id)
            .offset(skip).limit(limit).order_by(Ticket.purchased_at.desc())
        )
        tickets = result.scalars().all()
        return tickets
    except Exception as e:
        logger.error(f"Error fetching tickets for current user_id {current_user.id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred.")

@router.get(
    "/event/{event_id}",
    response_model=List[TicketResponseSchema],
    summary="Get all tickets for a specific event (Organizer or Admin)"
)
async def get_tickets_for_event_organizer_admin( 
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    skip: int = 0,
    limit: int = 100
):
    event = await db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Event with id {event_id} not found.")

    if event.author_id != current_user.id and current_user.role != "admin":
        logger.warning(f"User ID {current_user.id} (role {current_user.role}) attempted to access tickets for event ID {event_id} not organized by them.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view tickets for this event.")
        
    try:
        result = await db.execute(
            select(Ticket).where(Ticket.event_id == event_id)
            .offset(skip).limit(limit).order_by(Ticket.purchased_at.desc())
        )
        tickets = result.scalars().all()
        return tickets
    except Exception as e:
        logger.error(f"Error fetching tickets for event_id {event_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred.")

@router.get(
    "/{ticket_id}",
    response_model=TicketResponseSchema,
    summary="Get a specific ticket by ID (Owner or Admin/Organizer of event)"
)
async def get_ticket_by_id_restricted(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    ticket: Ticket | None = None
    try:
         
        query = select(Ticket).options(selectinload(Ticket.event)).filter(Ticket.id == ticket_id)
        result = await db.execute(query)
        ticket = result.scalars().first()
    except Exception as e:
        logger.error(f"Error fetching ticket with id {ticket_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred.")
    
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Ticket with id {ticket_id} not found.")
    ticket_event = await db.get(Event, ticket.event_id) #
    is_owner = ticket.user_id == current_user.id
    is_admin = current_user.role == "admin"
    is_event_organizer = ticket_event and ticket_event.author_id == current_user.id

    if not (is_owner or is_admin or is_event_organizer):
        logger.warning(f"User ID {current_user.id} (role {current_user.role}) attempted to access ticket ID {ticket_id} not belonging to them or their event.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this ticket.")
        
    return ticket

@router.patch(
    "/{ticket_id}/admin_update_price",
    response_model=TicketResponseSchema,
    summary="Admin: Update ticket price (use with caution)",
    dependencies=[Depends(get_current_admin_user)]
)
async def update_ticket_price_by_admin(
    ticket_id: int,
    ticket_update: TicketUpdateAdminSchema,
    db: AsyncSession = Depends(get_db)
):
    db_ticket: Ticket | None = None
    update_payload_str = ticket_update.model_dump_json(exclude_unset=True)
    try:
        result = await db.execute(select(Ticket).filter(Ticket.id == ticket_id))
        db_ticket = result.scalars().first()
        if not db_ticket:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Ticket with id {ticket_id} not found.")
        
        updated_data = ticket_update.model_dump(exclude_unset=True)
        if not updated_data or "price" not in updated_data: 
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Price field is required for update.")

        db_ticket.price = updated_data["price"] 
        
        await db.commit()
        await db.refresh(db_ticket)
        logger.info(f"Admin updated Ticket (ID: {ticket_id}) price to {db_ticket.price}.")
        return db_ticket
    except HTTPException:
        raise
    except Exception as e: 
        await db.rollback()
        logger.error(f"Error (admin) updating ticket id {ticket_id} with payload {update_payload_str}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred.")

@router.delete(
    "/{ticket_id}",
    summary="Delete/Cancel a ticket (Owner or Admin/Organizer of event)",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_ticket_restricted( 
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    db_ticket: Ticket | None = None
    try:
        result = await db.execute(select(Ticket).filter(Ticket.id == ticket_id))
        db_ticket = result.scalars().first()

        if not db_ticket:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Ticket with id {ticket_id} not found.")

        ticket_event = await db.get(Event, db_ticket.event_id)

        is_owner = db_ticket.user_id == current_user.id
        is_admin = current_user.role == "admin"
        is_event_organizer = ticket_event and ticket_event.author_id == current_user.id
        
        if not (is_owner or is_admin or is_event_organizer):
            logger.warning(f"User ID {current_user.id} (role {current_user.role}) attempted to delete ticket ID {ticket_id} not belonging to them or their event.")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this ticket.")

        ticket_info_for_log = f"ID: {ticket_id}, user: {db_ticket.user_id}, event: {db_ticket.event_id}"
        await db.delete(db_ticket)
        await db.commit()
        
        deleted_by = "owner"
        if is_admin and not is_owner: deleted_by = "admin"
        elif is_event_organizer and not is_owner: deleted_by = "event_organizer"
        logger.info(f"Ticket ({ticket_info_for_log}) deleted by {deleted_by} (current_user ID: {current_user.id}).")
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except HTTPException:
        raise
    except Exception as e: 
        await db.rollback()
        ticket_info_for_log = f"user: {db_ticket.user_id if db_ticket else 'N/A'}, event: {db_ticket.event_id if db_ticket else 'N/A'}"
        logger.error(f"Error deleting ticket with id {ticket_id} ({ticket_info_for_log}): {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred.")

@router.get(
    "/admin/all",
    response_model=List[TicketResponseSchema],
    summary="Admin: Get all tickets (paginated)",
    dependencies=[Depends(get_current_admin_user)]
)
async def get_all_tickets_admin(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    try:
        result = await db.execute(select(Ticket).offset(skip).limit(limit).order_by(Ticket.purchased_at.desc()))
        tickets = result.scalars().all()
        return tickets
    except Exception as e:
        logger.error(f"Error fetching all tickets (admin): {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred.")
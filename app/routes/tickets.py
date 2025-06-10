from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from decimal import Decimal

from app.database import get_db
from app.models.tickets import Ticket
from app.schemas.tickets import TicketCreateSchema, TicketResponseSchema

router = APIRouter(
    tags=["Tickets"]
)



@router.post("/as_user", summary="Create a new ticket specifying the author")
async def create_ticket_as_author(
    new_ticket: TicketCreateSchema,
    db:AsyncSession = Depends(get_db)
):
    db_ticket = Ticket(
        user_id = new_ticket.user_id,
        event_id = new_ticket.event_id,
        price = new_ticket.price
    )
    db.add(db_ticket)
    await db.commit()
    await db.refresh(db_ticket)
    return  {"success": True, "message":"Ticket added successfully by specified author", "ticket_id": db_ticket.id}



@router.get(
    "/user/{user_id}",
    response_model=List[TicketResponseSchema],
    summary="Get all tickets for a specific user"
)
async def get_tickets_for_specific_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Ticket).where(Ticket.user_id == user_id).order_by(Ticket.purchased_at.desc())
    )
    tickets = result.scalars().all()
    return tickets



@router.get(
    "event/{event_id}",
    response_model=List[TicketResponseSchema],
    summary="Get all tickets for a specific event"
)
async def get_tickets_for_specific_event(event_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Ticket).where(Ticket.event_id == event_id).order_by(Ticket.purchased_at.desc())
    )
    tickets = result.scalars().all()
    return tickets



@router.delete(
    "/{ticket_id}",
    summary="Delete a ticket by its ID",
    status_code=status.HTTP_200_OK
)
async def delete_ticket_by_id(ticket_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Ticket).filter(Ticket.id == ticket_id))
    ticket_to_delete = result.scalars().first()

    if not ticket_to_delete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket with id {ticket_id} not found"
        )
    await db.delete(ticket_to_delete)
    await db.commit()

    return {"success": True, "message": f"Ticket with id {ticket_to_delete.id} deleted successfully", "ticket_id": ticket_to_delete.id}
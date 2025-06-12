from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
import uvicorn
from app.routes import users, events, categories,participations,subscriptions,comments,reviews, tickets
from app.models import Base
from app.database import engine
import logging
import sys

LOG_LEVEL_STR = "INFO"
LOG_LEVEL = getattr(logging, LOG_LEVEL_STR.upper(), logging.INFO)
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(logging.Formatter(LOG_FORMAT))
logging.basicConfig(level=LOG_LEVEL, handlers=[stream_handler], force=True) 

app = FastAPI()

app.include_router(users.router,  tags=["Users"])
app.include_router(events.router, tags=["Events"])
app.include_router(categories.router, tags=["Categories"])
app.include_router(participations.router, tags=["Participations"])
app.include_router(subscriptions.router, tags=["Subscriptions"]) 
app.include_router(comments.router, tags=["Comments"])
app.include_router(reviews.router, tags=["Reviews"])
app.include_router(tickets.router, tags=["Tickets"])


@app.get("/")
def root():
    return "Hello"

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.post("/reset-database")
async def reset_database():
    """
    Drops all tables in the database and recreates them.
    Use this endpoint with caution as it deletes all data.
    """
    async with engine.begin() as conn:
        # Drop all tables
        await conn.run_sync(Base.metadata.drop_all)
        # Recreate all tables
        await conn.run_sync(Base.metadata.create_all)
    return {"success": True, "message": "Database reset successfully"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", reload=True)
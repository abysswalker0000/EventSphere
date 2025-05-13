from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
import uvicorn
from app.routes import users, events, categories,participations
from app.models import Base
from app.database import engine

app = FastAPI()

app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(events.router, prefix="/events", tags=["Events"])
app.include_router(categories.router, prefix="/categores", tags=["Categories"])
app.include_router(participations.router, prefix="/participations", tags=["Participations"])

@app.get("/")
def root():
    return "Hello"

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# @app.post("/reset-database")
# async def reset_database():
#     """
#     Drops all tables in the database and recreates them.
#     Use this endpoint with caution as it deletes all data.
#     """
#     async with engine.begin() as conn:
#         # Drop all tables
#         await conn.run_sync(Base.metadata.drop_all)
#         # Recreate all tables
#         await conn.run_sync(Base.metadata.create_all)
#     return {"success": True, "message": "Database reset successfully"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", reload=True)
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
import uvicorn
from app.routes import users, events

app = FastAPI()

app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(events.router, prefix="/events", tags=["Events"])

@app.get("/")
def root():
    return "Hello"

if __name__ == "__main__":
    uvicorn.run("app.main:app", reload=True)
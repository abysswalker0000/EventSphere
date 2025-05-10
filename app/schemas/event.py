from pydantic import BaseModel
from datetime import datetime

class NewEvent(BaseModel):
    title: str
    author_id: int
    event_time: datetime
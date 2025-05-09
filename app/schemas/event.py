from pydantic import BaseModel

class NewEvent(BaseModel):
    title: str
    author: str
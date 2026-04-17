from pydantic import BaseModel, Field

class RequestData(BaseModel):
    topic: str = Field(min_length=3, max_length=50)
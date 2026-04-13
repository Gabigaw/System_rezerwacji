from pydantic import BaseModel, Field


class BookSlotRequest(BaseModel):
    slot_id: int = Field(gt=0)
    client_id: int = Field(gt=0)
    service_id: int = Field(gt=0)
    notes: str | None = Field(default=None, max_length=1000)
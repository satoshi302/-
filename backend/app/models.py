from pydantic import BaseModel, Field


class PointCreate(BaseModel):
    name: str
    lat: float
    lng: float
    radius_m: int = Field(default=500, ge=50, le=5000)
    memo: str = ""


class PointOut(PointCreate):
    id: int
    created_at: str


class FetchResult(BaseModel):
    point_id: int
    fetched: int
    inserted: int
    message: str = ""


class CompareRequest(BaseModel):
    point_id: int
    current_start: str  # YYYY-MM-DD
    current_end: str
    past_start: str
    past_end: str

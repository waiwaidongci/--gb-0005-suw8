from pydantic import BaseModel,Field
from ..constants.dimensions import Dimension
class ScheduleInput(BaseModel):
    name:str=Field(min_length=2,max_length=120)
    dimensions:list[Dimension]=Field(default=[Dimension.CHANNEL,Dimension.MONTH],min_length=1,max_length=2)
    interval_minutes:int=Field(default=60,ge=1,le=10080)
    start_delay_seconds:int=Field(default=5,ge=5,le=86400)
class ScheduleState(BaseModel):
    active:bool

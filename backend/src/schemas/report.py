from pydantic import BaseModel,Field
from ..constants.dimensions import Dimension
class ReportInput(BaseModel):
    name:str=Field(min_length=2,max_length=120)
    dimensions:list[Dimension]=Field(default=[Dimension.CHANNEL,Dimension.MONTH],min_length=1,max_length=2)

from pydantic import BaseModel
class SourceOutput(BaseModel):
    source_key:str
    day:str
    channel:str
    region:str
    revenue:float
    cost:float
    refunds:float
    orders:int
    reference_net:float

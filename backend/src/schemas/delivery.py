from pydantic import BaseModel
class DeliveryOutput(BaseModel):
    id:int
    schedule_id:int
    run_id:int
    title:str
    created_at:str

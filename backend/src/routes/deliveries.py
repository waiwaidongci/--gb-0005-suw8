from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from ..config.database import get_db
from ..controllers.dependencies import current_user
from ..schemas.delivery import DeliveryOutput
from ..services.delivery_service import list_deliveries
router=APIRouter(prefix="/deliveries",tags=["deliveries"])
@router.get("",response_model=list[DeliveryOutput])
def index(db:Session=Depends(get_db),user=Depends(current_user)):return list_deliveries(db)

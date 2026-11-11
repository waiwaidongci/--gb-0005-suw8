from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from ..config.database import get_db
from ..controllers.dependencies import current_user,roles
from ..constants.roles import Role
from ..schemas.metric import MetricInput
from ..services.metric_service import list_metrics,create_metric
router=APIRouter(prefix="/metrics",tags=["metrics"])
@router.get("")
def index(db:Session=Depends(get_db),user=Depends(current_user)):return list_metrics(db)
@router.post("",status_code=201)
def create(data:MetricInput,db:Session=Depends(get_db),user=Depends(roles(Role.ADMIN))):return create_metric(db,data,user)

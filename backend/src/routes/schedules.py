from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from ..config.database import get_db
from ..controllers.dependencies import current_user,roles
from ..constants.roles import Role
from ..schemas.schedule import ScheduleInput,ScheduleState
from ..services.schedule_service import list_schedules,create_schedule,change_state
router=APIRouter(prefix="/schedules",tags=["schedules"])
@router.get("")
def index(db:Session=Depends(get_db),user=Depends(current_user)):return list_schedules(db)
@router.post("",status_code=201)
def create(data:ScheduleInput,db:Session=Depends(get_db),user=Depends(roles(Role.ADMIN))):return create_schedule(db,data,user)
@router.patch("/{sid}")
def state(sid:int,data:ScheduleState,db:Session=Depends(get_db),user=Depends(roles(Role.ADMIN))):return change_state(db,sid,data.active,user)

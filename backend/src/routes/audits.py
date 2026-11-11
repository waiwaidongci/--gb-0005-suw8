from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from ..config.database import get_db
from ..controllers.dependencies import current_user
from ..services.audit_service import list_audit
router=APIRouter(prefix="/audits",tags=["audit"])
@router.get("")
def index(db:Session=Depends(get_db),user=Depends(current_user)): return list_audit(db)

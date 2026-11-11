from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from ..config.database import get_db
from ..controllers.dependencies import current_user
from ..schemas.source import SourceOutput
from ..services.source_service import source_preview,reconciliation
router=APIRouter(prefix="/sources",tags=["sources"],dependencies=[Depends(current_user)])
@router.get("",response_model=list[SourceOutput])
def index(db:Session=Depends(get_db)):return source_preview(db)
@router.get("/reconciliation")
def check(db:Session=Depends(get_db)):return reconciliation(db)

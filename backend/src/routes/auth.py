from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from ..config.database import get_db
from ..schemas.auth import Login
from ..controllers.auth_controller import login
from ..controllers.dependencies import current_user
router=APIRouter(prefix="/auth",tags=["auth"])
@router.post("/login")
def sign_in(data:Login,db:Session=Depends(get_db)): return login(db,data)
@router.get("/me")
def me(user=Depends(current_user)): return {"name":user.name,"email":user.email,"role":user.role}

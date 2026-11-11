from fastapi import HTTPException
from ..models import User
from ..utils.security import verify_password,make_token
from ..services.audit_service import log
def login(db,data):
    user=db.query(User).filter_by(email=data.email).first()
    if not user or not verify_password(data.password,user.password_hash): raise HTTPException(401,"账号或密码错误")
    log(db,user.email,"auth.login",user.id); db.commit()
    return {"token":make_token(user),"user":{"id":user.id,"name":user.name,"email":user.email,"role":user.role}}

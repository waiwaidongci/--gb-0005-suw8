import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from ..config.database import get_db
from ..config.settings import JWT_SECRET
from ..models import User
bearer=HTTPBearer(auto_error=False)
def current_user(credentials: HTTPAuthorizationCredentials=Depends(bearer), db: Session=Depends(get_db)):
    try:
        payload=jwt.decode(credentials.credentials,JWT_SECRET,algorithms=["HS256"])
        user=db.get(User,int(payload["sub"]))
        if user: return user
    except (AttributeError,ValueError,jwt.PyJWTError): pass
    raise HTTPException(401,"登录已过期，请重新登录")
def roles(*allowed):
    def check(user=Depends(current_user)):
        if user.role not in allowed: raise HTTPException(403,"当前角色无权执行此操作")
        return user
    return check

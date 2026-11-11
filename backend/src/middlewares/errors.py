import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
class ErrorMiddleware(BaseHTTPMiddleware):
    async def dispatch(self,request,call_next):
        try: return await call_next(request)
        except Exception:
            logging.exception("request failed")
            return JSONResponse({"detail":"服务暂时异常，请重试或联系实验负责人"},status_code=500)

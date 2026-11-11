import time
from collections import defaultdict,deque
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self,app):
        super().__init__(app); self.requests=defaultdict(deque)
    async def dispatch(self,request,call_next):
        if request.url.path=="/auth/login":
            key=request.client.host; q=self.requests[key]; now=time.monotonic()
            while q and q[0]<now-60: q.popleft()
            if len(q)>=30: return JSONResponse({"detail":"登录尝试过多，请一分钟后重试"},status_code=429)
            q.append(now)
        return await call_next(request)

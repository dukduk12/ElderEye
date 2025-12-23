# main.py
# 앱의 진입점
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi import Request
from threading import Thread   
from fastapi.staticfiles import StaticFiles 

from src.infra.redis.redis_subscriber import RedisSubscriber
from src.interface.api.auth import router as auth_router
from src.interface.api.camera import router as camera_router
from src.interface.api.notification import router as notification_router  

app = FastAPI()

# app.mount("/alerts", StaticFiles(directory="/app/alerts"), name="alerts")
app.mount("/alerts", StaticFiles(directory="/app/alerts", html=False), name="alerts")

# redis subscribe runs in the background
@app.on_event("startup")
def startup_event():
    redis_subscriber = RedisSubscriber(redis_host="redis", redis_port=6379)
    
    def run_redis_subscriber():
        redis_subscriber.listen_notifications()   

    thread = Thread(target=run_redis_subscriber)
    thread.daemon = True   
    thread.start()

app.include_router(auth_router, prefix='/auth', tags=['auth'])
app.include_router(camera_router, prefix="/camera", tags=["cameras"])
app.include_router(notification_router, prefix="/notifications", tags=["notifications"])   
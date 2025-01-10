from .event_loop import EventLoopPool
from .fastapi_app import FastApiAppPool

event_loop_pool = EventLoopPool()
fastapi_app_pool = FastApiAppPool()

__all__ = ["event_loop_pool", "fastapi_app_pool"]

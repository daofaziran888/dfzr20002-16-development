"""业务路由汇总：通用资源路由 + 跨模块会展引擎 + 事故临时导视授权。"""
from __future__ import annotations

from app.routers.resource import router as resource_router
from app.routers.exhibition_routes import exhibition_router
from app.routers.emergency_routes import emergency_router

# Match fixed exhibition/emergency paths before /api/{module}/{entry_id}.
ROUTERS = [exhibition_router, emergency_router, resource_router]

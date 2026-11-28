"""领域服务注册表：通用资源路由按模块 key 分派到独立业务服务。"""
from __future__ import annotations

from app.services.base import BaseModuleService
from app.services.venue import VenueService
from app.services.booth import BoothService
from app.services.exhibitor import ExhibitorService
from app.services.design import DesignService
from app.services.material import MaterialService
from app.services.transport import TransportService
from app.services.construction import ConstructionService
from app.services.electrical import ElectricalService
from app.services.safety import SafetyService
from app.services.lighting import LightingService
from app.services.audio_visual import AudioVisualService
from app.services.furniture import FurnitureService
from app.services.signage import SignageService
from app.services.checklist import ChecklistService
from app.services.change_order import ChangeOrderService
from app.services.schedule import ScheduleService
from app.services.handover import HandoverService
from app.services.incident import IncidentService
from app.services.emergency_signage import EmergencySignageService

SERVICES: dict[str, BaseModuleService] = {
    "venue": VenueService(),
    "booth": BoothService(),
    "exhibitor": ExhibitorService(),
    "design": DesignService(),
    "material": MaterialService(),
    "transport": TransportService(),
    "construction": ConstructionService(),
    "electrical": ElectricalService(),
    "safety": SafetyService(),
    "lighting": LightingService(),
    "audio_visual": AudioVisualService(),
    "furniture": FurnitureService(),
    "signage": SignageService(),
    "checklist": ChecklistService(),
    "change_order": ChangeOrderService(),
    "schedule": ScheduleService(),
    "handover": HandoverService(),
    "incident": IncidentService(),
    "emergency_signage": EmergencySignageService(),
}


def service_for(module: str) -> BaseModuleService | None:
    return SERVICES.get(module)

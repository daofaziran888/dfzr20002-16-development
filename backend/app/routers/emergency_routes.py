"""事故临时导视授权路由：应急换向申请、授权、安装回执、解除、通行路线与审计查询。

业务规则全部在 EmergencySignageService 里，路由只负责分派和参数传递。
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services import service_for
from app.services.emergency_signage import EmergencySignageService

emergency_router = APIRouter(prefix="/api/emergency", tags=["事故临时导视授权"])


def emergency_service() -> EmergencySignageService:
    service = service_for("emergency_signage")
    assert isinstance(service, EmergencySignageService)
    return service


class ApplyPayload(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)


class InstallPayload(BaseModel):
    install_note: str = ""
    installer: str = ""


@emergency_router.post("/apply")
def apply_receipt(payload: ApplyPayload) -> dict:
    """申请换向回执：凭事故单号 + 场馆点位登记，初始状态「已申请」。"""
    entry, errors = emergency_service().create_entry(payload.values)
    if errors:
        raise HTTPException(status_code=400, detail="；".join(errors))
    return {"ok": True, "message": "换向回执已登记，待授权", "entry": entry}


@emergency_router.post("/receipts/{receipt_id}/authorize")
def authorize_receipt(receipt_id: int) -> dict:
    """授权换向：仅限事故单所属场馆，越权申请置「已拒绝」并留痕。"""
    entry, message = emergency_service().authorize(receipt_id)
    if entry is None:
        raise HTTPException(status_code=400, detail=message)
    return {"ok": True, "message": message, "entry": entry,
            "granted": entry.get("status") == "已授权"}


@emergency_router.get("/receipts/{receipt_id}/can-install")
def can_install(receipt_id: int) -> dict:
    """预检：该回执当前是否还可安装（同点位已有生效方向时不可）。"""
    ok, reason = emergency_service().can_install(receipt_id)
    return {"ok": ok, "message": reason}


@emergency_router.post("/receipts/{receipt_id}/install")
def install_receipt(receipt_id: int, payload: InstallPayload) -> dict:
    """交回现场安装回执：同点位无其他生效方向才生效，安装结果留痕。"""
    entry, message = emergency_service().submit_install(
        receipt_id, payload.install_note, payload.installer)
    if entry is None:
        raise HTTPException(status_code=400, detail=message)
    return {"ok": True, "message": message, "entry": entry}


@emergency_router.post("/incidents/{incident_ref}/resolve")
def resolve_incident(incident_ref: str) -> dict:
    """解除事故：回收该事故单全部活动回执（已申请/已授权/已生效 → 已解除）。"""
    result = emergency_service().release_incident(incident_ref)
    if not result["ok"]:
        raise HTTPException(status_code=404, detail=result["reason"])
    return result


@emergency_router.get("/incidents/{incident_ref}/route")
def passage_route(incident_ref: str) -> dict:
    """通行路线：按该事故单关联的生效回执向现场发布。"""
    result = emergency_service().passage_route(incident_ref)
    if not result["ok"]:
        raise HTTPException(status_code=404, detail=result["reason"])
    return result


@emergency_router.get("/incidents/{incident_ref}/installed-signs")
def installed_signs(incident_ref: str) -> dict:
    """审计：该事故单实际安装过的临时牌（含事故解除后的历史回执）。"""
    result = emergency_service().installed_signs(incident_ref)
    if not result["ok"]:
        raise HTTPException(status_code=404, detail=result["reason"])
    return result


@emergency_router.get("/rejections")
def rejections() -> dict:
    """审计：全部越权/驳回拒绝记录。"""
    return emergency_service().rejections()

"""事故临时导视授权：突发事件下的应急换向权限入口。

处置人员凭事故单和场馆点位申请换向回执，授权只覆盖事故单所属场馆，
越权申请置为「已拒绝」并留痕；同一时刻同一点位只允许一个「已生效」方向，
先交回安装回执者生效，其余同点位回执在解除前不可再安装；
安装回执、越权拒绝、解除恢复全部写入事件日志，事故解除后仍可反查
旧路线上实际安装过的临时牌。
"""
from __future__ import annotations

import copy
from typing import Any

from app.services.base import BaseModuleService
from app.store import store

DIRECTIONS = ("向东", "向西", "向南", "向北")
# 可被解除回收的活动状态
ACTIVE_STATUSES = ("已申请", "已授权", "已生效")


def find_incident(ref: str) -> dict[str, Any] | None:
    """按登记编号或 id 查找事故单。"""
    text = str(ref or "").strip()
    if not text:
        return None
    for row in store.rows("incident"):
        if str(row.get("登记编号", "")) == text:
            return row
    if text.isdigit():
        return store.find("incident", int(text))
    return None


def venue_of_location(location: str) -> dict[str, Any] | None:
    """按点位/位置文本匹配所属场馆；多个场馆名命中时取最长，避免短名误中。"""
    text = str(location or "").strip()
    if not text:
        return None
    best: dict[str, Any] | None = None
    for venue in store.rows("venue"):
        name = str(venue.get("场馆名称", "")).strip()
        if not name:
            continue
        if name in text or text in name:
            if best is None or len(name) > len(str(best.get("场馆名称", ""))):
                best = venue
    return best


class EmergencySignageService(BaseModuleService):
    MODULE = "emergency_signage"
    ENTITY = "换向回执"
    OPERATION_TERM = "授权换向"
    LIST_FIELDS = ["事故单号", "申请班组", "换向点位", "目标方向", "临时牌编号",
                   "登记编号", "负责人", "生效版本", "备注说明"]
    REQUIRED_FIELDS = ["事故单号", "申请班组", "换向点位", "目标方向", "临时牌编号"]
    STATUS_ORDER = ["已申请", "已授权", "已生效", "已解除"]
    ACTION_RULES = {"授权换向": "已授权", "交回安装回执": "已生效",
                    "解除恢复": "已解除", "驳回申请": "已拒绝"}
    NEGATIVE_ACTIONS = ["驳回申请"]
    RELATED_MODULES = ["incident", "signage"]

    # ---------- 登记申请 ----------

    def validate_entry(self, values: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        incident_ref = str(values.get("事故单号", "")).strip()
        if incident_ref and find_incident(incident_ref) is None:
            errors.append(f"事故单 {incident_ref} 不存在，不能凭它申请换向")
        direction = str(values.get("目标方向", "")).strip()
        if direction and direction not in DIRECTIONS:
            errors.append(f"目标方向 {direction} 不在允许范围（{'、'.join(DIRECTIONS)}）")
        return errors

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        # 事故单号统一规范为登记编号，后续按事故单反查不会漂移
        incident = find_incident(str(values.get("事故单号", "")).strip())
        if incident is not None:
            values = dict(values)
            values["事故单号"] = str(incident.get("登记编号", ""))
        return super().create_entry(values)

    # ---------- 授权：越权申请记录拒绝 ----------

    def authorize(self, receipt_id: int) -> tuple[dict[str, Any] | None, str]:
        """授权换向：临时权限只覆盖事故单所属场馆，越权申请置「已拒绝」并留痕。"""
        receipt = store.find(self.MODULE, receipt_id)
        if receipt is None:
            return None, f"{self.ENTITY} {receipt_id} 不存在或已归档"
        if receipt.get("status") != "已申请":
            return None, f"回执当前状态为「{receipt.get('status')}」，不能重复授权"

        incident = find_incident(str(receipt.get("事故单号", "")))
        if incident is None:
            return self._record_rejection(receipt, "关联事故单不存在，授权拒绝")

        point = str(receipt.get("换向点位", ""))
        incident_venue = venue_of_location(str(incident.get("发生位置", "")))
        point_venue = venue_of_location(point)
        if incident_venue is None:
            return self._record_rejection(receipt, "事故单发生位置未匹配到场馆，无法划定授权范围")
        if point_venue is None:
            return self._record_rejection(
                receipt, f"越权申请：点位 {point} 不属于任何已知场馆，临时权限不覆盖")
        if str(point_venue.get("场馆名称")) != str(incident_venue.get("场馆名称")):
            return self._record_rejection(
                receipt,
                f"越权申请：点位 {point} 属于「{point_venue.get('场馆名称')}」，"
                f"不在事故单所属场馆「{incident_venue.get('场馆名称')}」范围内")

        before = copy.deepcopy(receipt)
        receipt["status"] = "已授权"
        receipt["pending"] = True
        store.event_log.record(
            module=self.MODULE, entry_id=receipt_id, action="授权换向",
            before=before, after=copy.deepcopy(receipt),
            extra={"事故单号": receipt.get("事故单号"),
                   "授权场馆": incident_venue.get("场馆名称")})
        store.rebuild_indices()
        return receipt, f"{self.ENTITY}已授权换向（权限范围：{incident_venue.get('场馆名称')}）"

    def _record_rejection(self, receipt: dict[str, Any], reason: str) -> tuple[dict[str, Any], str]:
        """越权/不合格申请：置「已拒绝」并写入事件日志，供事后审计。"""
        before = copy.deepcopy(receipt)
        receipt["status"] = "已拒绝"
        receipt["pending"] = False
        receipt["abnormal"] = True
        store.event_log.record(
            module=self.MODULE, entry_id=int(receipt["id"]), action="越权拒绝",
            before=before, after=copy.deepcopy(receipt),
            extra={"拒绝原因": reason,
                   "事故单号": receipt.get("事故单号"),
                   "换向点位": receipt.get("换向点位"),
                   "申请班组": receipt.get("申请班组")})
        store.rebuild_indices()
        return receipt, f"已记录拒绝：{reason}"

    def reject_receipt(self, receipt_id: int, reason: str = "") -> tuple[dict[str, Any] | None, str]:
        """人工驳回申请。"""
        receipt = store.find(self.MODULE, receipt_id)
        if receipt is None:
            return None, f"{self.ENTITY} {receipt_id} 不存在或已归档"
        if receipt.get("status") in ("已解除", "已拒绝"):
            return None, f"回执当前状态为「{receipt.get('status')}」，不可驳回"
        before = copy.deepcopy(receipt)
        receipt["status"] = "已拒绝"
        receipt["pending"] = False
        receipt["abnormal"] = True
        store.event_log.record(
            module=self.MODULE, entry_id=receipt_id, action="驳回申请",
            before=before, after=copy.deepcopy(receipt),
            extra={"拒绝原因": reason or "人工驳回", "事故单号": receipt.get("事故单号")})
        store.rebuild_indices()
        return receipt, f"{self.ENTITY}已驳回"

    # ---------- 安装回执：同一点位同一时刻仅一个生效方向 ----------

    def _install_block_reason(self, receipt: dict[str, Any]) -> str:
        """返回阻止安装的原因；可安装时返回空串。"""
        if receipt.get("status") != "已授权":
            return f"回执当前状态为「{receipt.get('status')}」，仅已授权回执可交回安装回执"
        point = str(receipt.get("换向点位", ""))
        for other in store.rows(self.MODULE):
            if other.get("id") == receipt.get("id"):
                continue
            if str(other.get("换向点位", "")) == point and other.get("status") == "已生效":
                return (f"点位 {point} 已存在生效方向「{other.get('目标方向')}」"
                        f"（回执#{other.get('id')} {other.get('申请班组')}），"
                        f"同一时刻同一点位仅允许一个生效方向，本笔不可安装")
        return ""

    def can_install(self, receipt_id: int) -> tuple[bool, str]:
        """预检：该回执当前是否还可安装（不改状态）。"""
        receipt = store.find(self.MODULE, receipt_id)
        if receipt is None:
            return False, f"{self.ENTITY} {receipt_id} 不存在或已归档"
        reason = self._install_block_reason(receipt)
        return (not reason), (reason or "可以交回安装回执")

    def submit_install(
        self,
        receipt_id: int,
        install_note: str = "",
        installer: str = "",
    ) -> tuple[dict[str, Any] | None, str]:
        """交回现场安装回执：通过点位唯一性校验后生效，安装结果留痕。"""
        receipt = store.find(self.MODULE, receipt_id)
        if receipt is None:
            return None, f"{self.ENTITY} {receipt_id} 不存在或已归档"
        reason = self._install_block_reason(receipt)
        if reason:
            return None, reason

        before = copy.deepcopy(receipt)
        receipt["status"] = "已生效"
        receipt["pending"] = True
        store.event_log.record(
            module=self.MODULE, entry_id=receipt_id, action="交回安装回执",
            before=before, after=copy.deepcopy(receipt),
            extra={"事故单号": receipt.get("事故单号"),
                   "换向点位": receipt.get("换向点位"),
                   "目标方向": receipt.get("目标方向"),
                   "临时牌编号": receipt.get("临时牌编号"),
                   "申请班组": receipt.get("申请班组"),
                   "安装结果": install_note or "现场安装完成",
                   "安装人": installer or str(receipt.get("负责人", ""))})
        store.rebuild_indices()
        return receipt, (f"安装回执已确认：{receipt.get('换向点位')} 生效方向"
                         f"「{receipt.get('目标方向')}」，临时牌 {receipt.get('临时牌编号')}")

    # ---------- 解除事故 ----------

    def release_incident(self, incident_ref: str) -> dict[str, Any]:
        """解除事故：该事故单下所有活动回执（已申请/已授权/已生效）置「已解除」。"""
        incident = find_incident(incident_ref)
        if incident is None:
            return {"ok": False, "reason": f"事故单 {incident_ref} 不存在"}
        incident_no = str(incident.get("登记编号", ""))
        released: list[dict[str, Any]] = []
        for receipt in store.rows(self.MODULE):
            if str(receipt.get("事故单号", "")) != incident_no:
                continue
            if receipt.get("status") not in ACTIVE_STATUSES:
                continue
            before = copy.deepcopy(receipt)
            receipt["status"] = "已解除"
            receipt["pending"] = False
            store.event_log.record(
                module=self.MODULE, entry_id=int(receipt["id"]), action="解除恢复",
                before=before, after=copy.deepcopy(receipt),
                extra={"事故单号": incident_no, "换向点位": receipt.get("换向点位"),
                       "临时牌编号": receipt.get("临时牌编号")})
            released.append({"receipt_id": receipt["id"], "登记编号": receipt.get("登记编号"),
                             "换向点位": receipt.get("换向点位"), "目标方向": receipt.get("目标方向"),
                             "临时牌编号": receipt.get("临时牌编号")})
        store.rebuild_indices()
        return {"ok": True, "incident": incident, "released": released, "count": len(released),
                "message": (f"事故单 {incident_no} 已解除，回收 {len(released)} 笔回执"
                            if released else f"事故单 {incident_no} 没有待解除的活动回执")}

    # ---------- 通行路线与安装审计 ----------

    def _incident_receipts(self, incident_no: str) -> list[dict[str, Any]]:
        return [row for row in store.rows(self.MODULE)
                if str(row.get("事故单号", "")) == incident_no]

    def passage_route(self, incident_ref: str) -> dict[str, Any]:
        """事件处置按与事故单关联的生效回执，向现场发布通行路线。"""
        incident = find_incident(incident_ref)
        if incident is None:
            return {"ok": False, "reason": f"事故单 {incident_ref} 不存在"}
        incident_no = str(incident.get("登记编号", ""))
        effective = [r for r in self._incident_receipts(incident_no) if r.get("status") == "已生效"]
        route = [{"receipt_id": r["id"], "登记编号": r.get("登记编号"),
                  "换向点位": r.get("换向点位"), "目标方向": r.get("目标方向"),
                  "临时牌编号": r.get("临时牌编号"), "申请班组": r.get("申请班组")}
                 for r in effective]
        return {"ok": True, "incident": incident, "route": route, "count": len(route),
                "message": (f"已按 {len(route)} 笔生效回执向现场发布通行路线"
                            if route else "当前无生效换向回执，暂无应急通行路线")}

    def installed_signs(self, incident_ref: str) -> dict[str, Any]:
        """审计：该事故单实际安装过的临时牌。

        判定依据是「交回安装回执」事件（当前仍生效的一并纳入），
        仅授权未安装就被解除的回执不算实际安装过。
        """
        incident = find_incident(incident_ref)
        if incident is None:
            return {"ok": False, "reason": f"事故单 {incident_ref} 不存在"}
        incident_no = str(incident.get("登记编号", ""))
        installed: list[dict[str, Any]] = []
        for receipt in self._incident_receipts(incident_no):
            events = [e for e in store.event_log.for_module(self.MODULE, int(receipt["id"]))
                      if e["action"] == "交回安装回执"]
            if not events and receipt.get("status") != "已生效":
                continue
            last = events[-1] if events else None
            extra = (last.get("extra") or {}) if last else {}
            installed.append({
                "receipt_id": receipt["id"], "登记编号": receipt.get("登记编号"),
                "换向点位": receipt.get("换向点位"), "目标方向": receipt.get("目标方向"),
                "临时牌编号": receipt.get("临时牌编号"), "申请班组": receipt.get("申请班组"),
                "当前状态": receipt.get("status"),
                "安装时间": last.get("timestamp") if last else None,
                "安装结果": extra.get("安装结果", ""), "安装人": extra.get("安装人", ""),
            })
        return {"ok": True, "incident": incident, "installed": installed,
                "count": len(installed),
                "message": f"事故单 {incident_no} 实际安装过 {len(installed)} 块临时牌"}

    def rejections(self) -> dict[str, Any]:
        """审计：全部越权/驳回拒绝记录（含拒绝原因）。"""
        result: list[dict[str, Any]] = []
        for receipt in store.rows(self.MODULE):
            if receipt.get("status") != "已拒绝":
                continue
            events = [e for e in store.event_log.for_module(self.MODULE, int(receipt["id"]))
                      if e["action"] in ("越权拒绝", "驳回申请")]
            last = events[-1] if events else None
            extra = (last.get("extra") or {}) if last else {}
            result.append({
                "receipt_id": receipt["id"], "登记编号": receipt.get("登记编号"),
                "事故单号": receipt.get("事故单号"), "申请班组": receipt.get("申请班组"),
                "换向点位": receipt.get("换向点位"), "目标方向": receipt.get("目标方向"),
                "拒绝原因": extra.get("拒绝原因", ""),
                "拒绝时间": last.get("timestamp") if last else None,
            })
        return {"rejections": result, "count": len(result)}

    # ---------- 通用动作路径：与专用方法保持同一套规则 ----------

    def validate_action(self, entry_id: int, action: str) -> tuple[bool, str]:
        receipt = store.find(self.MODULE, entry_id)
        if receipt is None:
            return False, f"{self.ENTITY} {entry_id} 不存在"
        if action == "解除恢复" and receipt.get("status") not in ACTIVE_STATUSES:
            return False, f"回执当前状态为「{receipt.get('status')}」，无需解除"
        return True, ""

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        if action == "授权换向":
            return self.authorize(entry_id)
        if action == "交回安装回执":
            return self.submit_install(entry_id)
        if action == "驳回申请":
            return self.reject_receipt(entry_id)
        return super().run_action(entry_id, action)

    def domain_snapshot(self) -> dict[str, Any]:
        base = super().domain_snapshot()
        rows = store.rows(self.MODULE)
        base["effective_points"] = [
            {"换向点位": r.get("换向点位"), "目标方向": r.get("目标方向"),
             "临时牌编号": r.get("临时牌编号")}
            for r in rows if r.get("status") == "已生效"
        ]
        base["rejected"] = sum(1 for r in rows if r.get("status") == "已拒绝")
        return base

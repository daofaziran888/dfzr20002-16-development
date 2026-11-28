"""事故临时导视授权 - 应急换向业务测试。

覆盖题目场景：A厅中门事故关闭，事故班/常规班各持一笔已授权换向回执
（同一块临时牌、方向相反、均未安装）：
1. 越权申请须记录拒绝（临时权限只覆盖事故单所属场馆）
2. 先交回安装回执者生效，同一点位同一时刻仅一个生效方向
3. 另一笔不可再安装
4. 按生效回执向现场发布通行路线
5. 解除事故后回收回执，旧路线上实际安装过的临时牌可查
"""
import sys
import unittest

import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services import service_for
from app.services.emergency_signage import find_incident, venue_of_location
from app.store import store


def emergency_svc():
    return service_for("emergency_signage")


class TestEmergencySeedScenario(unittest.TestCase):
    """种子场景：INCI-0002（A厅中门）下事故班向东、常规班向西，两笔已授权未安装。"""

    def test_01_seed_receipts_authorized(self):
        """两笔回执已授权、争用同一块临时牌 TEMP-A1-01，事故单属于 A厅。"""
        r1 = store.find("emergency_signage", 1)
        r2 = store.find("emergency_signage", 2)
        self.assertIsNotNone(r1)
        self.assertIsNotNone(r2)
        self.assertEqual(r1["status"], "已授权")
        self.assertEqual(r1["申请班组"], "事故班")
        self.assertEqual(r1["目标方向"], "向东")
        self.assertEqual(r2["status"], "已授权")
        self.assertEqual(r2["申请班组"], "常规班")
        self.assertEqual(r2["目标方向"], "向西")
        self.assertEqual(r1["临时牌编号"], r2["临时牌编号"])
        self.assertEqual(r1["临时牌编号"], "TEMP-A1-01")

        incident = find_incident("INCI-0002")
        self.assertIsNotNone(incident)
        venue = venue_of_location(str(incident["发生位置"]))
        self.assertIsNotNone(venue)
        self.assertEqual(venue["场馆名称"], "A厅")

    def test_02_over_scope_application_recorded_rejected(self):
        """越权申请（B馆点位超出 A厅事故单范围）须记录拒绝。"""
        svc = emergency_svc()
        entry, errors = svc.create_entry({
            "事故单号": "INCI-0002", "申请班组": "常规班", "换向点位": "B馆多功能厅侧门",
            "目标方向": "向西", "临时牌编号": "TEMP-B-01", "登记编号": "EMER-9001",
            "负责人": "陈设计", "生效版本": "v1.0", "备注说明": "越权测试"})
        self.assertFalse(errors)
        self.assertEqual(entry["status"], "已申请")

        entry, message = svc.authorize(entry["id"])
        self.assertEqual(entry["status"], "已拒绝")
        self.assertIn("越权", message)
        self.assertTrue(entry["abnormal"])
        self.assertFalse(entry["pending"])

        # 拒绝记录可查（含原因）
        rejections = svc.rejections()
        hit = [r for r in rejections["rejections"] if r["receipt_id"] == entry["id"]]
        self.assertEqual(len(hit), 1)
        self.assertIn("越权", hit[0]["拒绝原因"])

        # 事件日志留痕
        events = [e for e in store.event_log.for_module("emergency_signage", entry["id"])
                  if e["action"] == "越权拒绝"]
        self.assertTrue(events)

    def test_03_incident_team_installs_east(self):
        """事故班交回安装回执：向东生效。"""
        svc = emergency_svc()
        ok, _ = svc.can_install(1)
        self.assertTrue(ok)
        entry, message = svc.submit_install(1, "中门临时牌已指向东门", "郑安全")
        self.assertIsNotNone(entry, message)
        self.assertEqual(entry["status"], "已生效")

    def test_04_regular_team_blocked(self):
        """同一点位已有生效方向，常规班的向西回执不可再安装。"""
        svc = emergency_svc()
        ok, reason = svc.can_install(2)
        self.assertFalse(ok)
        self.assertIn("仅允许一个生效方向", reason)

        entry, message = svc.submit_install(2, "试图安装向西指示")
        self.assertIsNone(entry)
        self.assertIn("仅允许一个生效方向", message)
        # 状态保持已授权，不被破坏
        self.assertEqual(store.find("emergency_signage", 2)["status"], "已授权")

    def test_05_route_published_from_effective_receipt(self):
        """通行路线按与事故单关联的生效回执发布：中门 → 向东。"""
        svc = emergency_svc()
        route = svc.passage_route("INCI-0002")
        self.assertTrue(route["ok"])
        self.assertEqual(route["count"], 1)
        step = route["route"][0]
        self.assertEqual(step["换向点位"], "A厅中门")
        self.assertEqual(step["目标方向"], "向东")
        self.assertEqual(step["临时牌编号"], "TEMP-A1-01")
        self.assertEqual(step["申请班组"], "事故班")

    def test_06_resolve_releases_receipts(self):
        """解除事故：该事故单的活动回执全部回收为已解除。"""
        svc = emergency_svc()
        result = svc.release_incident("INCI-0002")
        self.assertTrue(result["ok"])
        self.assertEqual(result["count"], 2)
        self.assertEqual(store.find("emergency_signage", 1)["status"], "已解除")
        self.assertEqual(store.find("emergency_signage", 2)["status"], "已解除")

    def test_07_audit_installed_signs_after_resolve(self):
        """解除后仍能查回旧路线上实际安装过的牌；未安装的授权不计入。"""
        svc = emergency_svc()
        audit = svc.installed_signs("INCI-0002")
        self.assertTrue(audit["ok"])
        self.assertEqual(audit["count"], 1)
        sign = audit["installed"][0]
        self.assertEqual(sign["临时牌编号"], "TEMP-A1-01")
        self.assertEqual(sign["目标方向"], "向东")
        self.assertEqual(sign["当前状态"], "已解除")
        self.assertTrue(sign["安装时间"])
        self.assertEqual(sign["安装人"], "郑安全")
        # 通行路线已清空
        self.assertEqual(svc.passage_route("INCI-0002")["count"], 0)

    def test_08_install_after_resolve_rejected(self):
        """事故解除后，未安装的授权回执也不可再安装。"""
        svc = emergency_svc()
        ok, reason = svc.can_install(2)
        self.assertFalse(ok)
        entry, message = svc.submit_install(2)
        self.assertIsNone(entry)


class TestEmergencyFullLifecycle(unittest.TestCase):
    """独立全链路：登记事故单 → 申请 → 授权 → 安装 → 路线 → 解除 → 审计。"""

    def test_full_lifecycle(self):
        incident_svc = service_for("incident")
        incident, errors = incident_svc.create_entry({
            "事件类型": "安全事故", "发生位置": "A厅北门", "处置班组": "事故班",
            "处置结果": "北门临时关闭", "登记编号": "INCI-9001", "负责人": "郑安全",
            "生效版本": "v1.0", "备注说明": "生命周期测试"})
        self.assertFalse(errors)
        svc = emergency_svc()

        # 未登记的事故单不能申请
        bad, errors = svc.create_entry({
            "事故单号": "INCI-9999", "申请班组": "事故班", "换向点位": "A厅北门",
            "目标方向": "向东", "临时牌编号": "TEMP-X-01"})
        self.assertIsNone(bad)
        self.assertTrue(any("不存在" in e for e in errors))

        # 非法方向不能申请
        bad, errors = svc.create_entry({
            "事故单号": "INCI-9001", "申请班组": "事故班", "换向点位": "A厅北门",
            "目标方向": "向里", "临时牌编号": "TEMP-X-02"})
        self.assertIsNone(bad)
        self.assertTrue(any("目标方向" in e for e in errors))

        # 正常申请：事故单号传 id 也会规范化为登记编号
        receipt, errors = svc.create_entry({
            "事故单号": str(incident["id"]), "申请班组": "事故班", "换向点位": "A厅北门",
            "目标方向": "向北", "临时牌编号": "TEMP-N-01", "登记编号": "EMER-9002",
            "负责人": "郑安全", "生效版本": "v1.0", "备注说明": ""})
        self.assertFalse(errors)
        self.assertEqual(receipt["事故单号"], "INCI-9001")
        self.assertEqual(receipt["status"], "已申请")

        # 未授权不能安装
        entry, message = svc.submit_install(receipt["id"])
        self.assertIsNone(entry)

        # 授权：点位与事故单同属 A厅 → 通过
        entry, message = svc.authorize(receipt["id"])
        self.assertIsNotNone(entry, message)
        self.assertEqual(entry["status"], "已授权")

        # 重复授权拒绝
        again, message = svc.authorize(receipt["id"])
        self.assertIsNone(again)

        # 安装生效 → 通行路线出现
        entry, message = svc.submit_install(receipt["id"], "北门临时牌就位", "郑安全")
        self.assertEqual(entry["status"], "已生效")
        route = svc.passage_route("INCI-9001")
        self.assertEqual(route["count"], 1)
        self.assertEqual(route["route"][0]["目标方向"], "向北")

        # 解除 → 审计仍可查回实际安装的牌
        result = svc.release_incident("INCI-9001")
        self.assertEqual(result["count"], 1)
        audit = svc.installed_signs("INCI-9001")
        self.assertEqual(audit["count"], 1)
        self.assertEqual(audit["installed"][0]["临时牌编号"], "TEMP-N-01")
        self.assertEqual(audit["installed"][0]["安装人"], "郑安全")

    def test_unknown_point_rejected(self):
        """点位不属于任何已知场馆：授权拒绝并留痕。"""
        svc = emergency_svc()
        receipt, errors = svc.create_entry({
            "事故单号": "INCI-9001", "申请班组": "常规班", "换向点位": "未知馆西门",
            "目标方向": "向西", "临时牌编号": "TEMP-U-01", "登记编号": "EMER-9005",
            "负责人": "陈设计", "生效版本": "v1.0", "备注说明": ""})
        self.assertFalse(errors)
        entry, message = svc.authorize(receipt["id"])
        self.assertEqual(entry["status"], "已拒绝")
        self.assertIn("越权", message)


class TestGenericActionPath(unittest.TestCase):
    """通用资源动作路径（工作台）与专用方法执行同一套规则。"""

    def test_generic_actions_full_flow(self):
        incident_svc = service_for("incident")
        incident_svc.create_entry({
            "事件类型": "设施故障", "发生位置": "A厅南门", "处置班组": "事故班",
            "处置结果": "南门封闭", "登记编号": "INCI-9002", "负责人": "郑安全",
            "生效版本": "v1.0", "备注说明": "通用路径测试"})
        svc = emergency_svc()
        receipt, errors = svc.create_entry({
            "事故单号": "INCI-9002", "申请班组": "常规班", "换向点位": "A厅南门",
            "目标方向": "向南", "临时牌编号": "TEMP-S-01", "登记编号": "EMER-9003",
            "负责人": "陈设计", "生效版本": "v1.0", "备注说明": ""})
        self.assertFalse(errors)
        rid = receipt["id"]

        entry, message = svc.run_action(rid, "授权换向")
        self.assertEqual(entry["status"], "已授权")
        entry, message = svc.run_action(rid, "交回安装回执")
        self.assertEqual(entry["status"], "已生效")
        entry, message = svc.run_action(rid, "解除恢复")
        self.assertEqual(entry["status"], "已解除")
        self.assertFalse(entry["pending"])

        # 未知动作不在可执行范围
        entry, message = svc.run_action(rid, "不存在的动作")
        self.assertIsNone(entry)

    def test_generic_reject_action(self):
        svc = emergency_svc()
        receipt, errors = svc.create_entry({
            "事故单号": "INCI-0001", "申请班组": "常规班", "换向点位": "A厅西门",
            "目标方向": "向西", "临时牌编号": "TEMP-W-01", "登记编号": "EMER-9004",
            "负责人": "陈设计", "生效版本": "v1.0", "备注说明": ""})
        self.assertFalse(errors)
        entry, message = svc.run_action(receipt["id"], "驳回申请")
        self.assertEqual(entry["status"], "已拒绝")
        self.assertFalse(entry["pending"])
        self.assertTrue(entry["abnormal"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

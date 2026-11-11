"""Unit test cho các khối nhỏ của lõi mô hình. Chạy: python -m unittest discover -s tests -v"""
import io
import unittest

import numpy as np
import pandas as pd

import _paths  # noqa: F401  (thêm mã nguồn vào sys.path)
import fraud_core as F
import fs_realtime as RT


def _csv_bytes(df):
    b = io.StringIO()
    df.to_csv(b, index=False)
    return b.getvalue().encode("utf-8")


class TestRuleWeights(unittest.TestCase):
    def test_wilson_lower_bound(self):
        # 8/10 có cận dưới Wilson 95% khoảng 0,49 – thấp hơn hẳn tỉ lệ thô 0,8 vì mẫu nhỏ
        self.assertAlmostEqual(F.wilson_lb(8, 10), 0.4902, places=3)
        self.assertEqual(F.wilson_lb(0, 0), 0.0)
        # cùng tỉ lệ nhưng nhiều mẫu hơn thì cận dưới cao hơn
        self.assertGreater(F.wilson_lb(80, 100), F.wilson_lb(8, 10))

    def test_noisy_or(self):
        flags = pd.DataFrame({c: [0, 0] for c in F.RULE_W})
        flags.loc[1, "flag_R3"] = 1
        flags.loc[1, "flag_R6"] = 1
        s = F.noisy_or(flags, F.RULE_W)
        self.assertEqual(s[0], 0.0)  # không luật nào bật
        expected = 1 - (1 - F.RULE_W["flag_R3"]) * (1 - F.RULE_W["flag_R6"])
        self.assertAlmostEqual(s[1], expected, places=9)

    def test_fusion_weights_sum_to_one(self):
        self.assertAlmostEqual(sum(F.W_FUSION), 1.0)
        self.assertEqual(F.W_FUSION, (0.60, 0.30, 0.10))


class TestRiskLevel(unittest.TestCase):
    THR, MED = 0.6847, 0.4349

    def test_levels_by_threshold(self):
        lv = RT.level([0.10, 0.50, 0.70], [0, 0, 0], [0, 0, 0], self.THR, self.MED)
        self.assertEqual(list(lv), ["LOW", "MEDIUM", "HIGH"])

    def test_critical_needs_r5_or_r6(self):
        lv = RT.level([0.70, 0.70, 0.70, 0.50], [1, 0, 0, 1], [0, 1, 0, 1], self.THR, self.MED)
        self.assertEqual(list(lv), ["CRITICAL", "CRITICAL", "HIGH", "MEDIUM"])

    def test_context_layer_never_blocks(self):
        # lớp ngữ cảnh chỉ nâng LOW lên MEDIUM, không bao giờ tạo HIGH/CRITICAL
        lv = RT.level([0.10, 0.10, 0.50], [0, 1, 0], [0, 1, 0], self.THR, self.MED, ctx=[99, 99, 99], ctx_thr=13.9)
        self.assertEqual(list(lv), ["MEDIUM", "MEDIUM", "MEDIUM"])
        lv = RT.level([0.10], [0], [0], self.THR, self.MED, ctx=[5.0], ctx_thr=13.9)
        self.assertEqual(list(lv), ["LOW"])


class TestValidate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = _paths.btc_files()

    def test_btc_pack_passes(self):
        _, checks, ok = F.validate(self.files)
        self.assertTrue(ok)
        self.assertFalse([c for c in checks if c["status"] == "LỖI"])

    def test_missing_required_file(self):
        files = {k: v for k, v in self.files.items() if k != "devices.csv"}
        _, checks, ok = F.validate(files)
        self.assertFalse(ok)
        self.assertTrue(any(c["check"] == "devices.csv" and c["status"] == "LỖI" for c in checks))

    def test_missing_column(self):
        gd = pd.read_csv(io.BytesIO(self.files["transactions.csv"])).drop(columns=["amount"])
        _, checks, ok = F.validate({**self.files, "transactions.csv": _csv_bytes(gd)})
        self.assertFalse(ok)
        self.assertTrue(any("amount" in c["detail"] for c in checks if c["status"] == "LỖI"))

    def test_bad_values(self):
        gd = pd.read_csv(io.BytesIO(self.files["transactions.csv"]))
        gd.loc[0, "amount"] = -5
        gd.loc[2, "transaction_id"] = gd.loc[1, "transaction_id"]
        _, checks, ok = F.validate({**self.files, "transactions.csv": _csv_bytes(gd)})
        self.assertFalse(ok)
        bad = {c["check"] for c in checks if c["status"] == "LỖI"}
        self.assertIn("amount là số dương", bad)
        self.assertIn("transaction_id không trùng", bad)

    def test_manifest_detects_edited_file(self):
        gd = pd.read_csv(io.BytesIO(self.files["transactions.csv"]))
        gd.loc[0, "amount"] = gd.loc[0, "amount"] + 1
        _, checks, _ = F.validate({**self.files, "transactions.csv": _csv_bytes(gd)})
        man = [c for c in checks if c["group"] == "Đối chiếu manifest BTC" and c["check"] == "transactions.csv"]
        self.assertEqual(man[0]["status"], "CẢNH BÁO")


class TestCases(unittest.TestCase):
    def test_group_within_30_minutes(self):
        t0 = pd.Timestamp("2026-05-20 18:50")
        df = pd.DataFrame({
            "transaction_id": ["T1", "T2", "T3", "T4"],
            "customer_id": ["C1", "C1", "C1", "C2"],
            "datetime": [t0, t0 + pd.Timedelta(minutes=10), t0 + pd.Timedelta(minutes=50), t0],
            "predicted_fraud": [1, 1, 1, 1], "risk_score": [0.9, 0.95, 0.8, 0.7],
            "risk_level": ["HIGH", "CRITICAL", "HIGH", "HIGH"], "amount": [1, 2, 3, 4],
            "device_id": ["D1", "D1", "D1", "D2"], "alert_reason": ["a", "b", "c", "d"]})
        c = F.make_cases(df)
        self.assertEqual(len(c), 3)  # T1+T2 chung hồ sơ; T3 cách 40 phút; T4 khách khác
        first = c.iloc[0]
        self.assertEqual(first.transaction_ids, "T1;T2")
        self.assertEqual(first.case_level, "CRITICAL")
        self.assertEqual(first.case_id, "CASE0001")


if __name__ == "__main__":
    unittest.main(verbosity=2)

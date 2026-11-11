"""Scenario test: chạy toàn bộ mô hình trên Data Pack BTC rồi kiểm tra KPI, định dạng file nộp, chấm thời gian thực
và 4 kịch bản của app FS Pay. Mất khoảng 1–3 phút.  Chạy: python -m unittest discover -s tests -v"""
import io
import unittest

import pandas as pd

import _paths
import fraud_core as F
import fs_realtime as RT
import fspay_sim as S

B = "Gộp 3 tầng – có hồ sơ (B, chính thức)"


class TestFullRun(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = _paths.btc_files()
        cls.res = F.run(cls.files)
        cls.rep = cls.res["report"]
        cls.b = cls.rep["comparison_nested_cv"][B]

    # --- KPI (kiểm định chéo 5 phần, ngưỡng chọn trên phần học) ---
    def test_kpi_targets(self):
        b, k = self.b, self.rep["kpi"]
        self.assertGreaterEqual(b["recall"], 0.80)       # mục tiêu BTC
        self.assertGreaterEqual(b["f1"], 0.75)           # mục tiêu BTC
        self.assertGreaterEqual(b["precision"], 0.90)    # mục tiêu nhóm
        self.assertGreaterEqual(k["intervene_recall"], 0.90)
        self.assertLessEqual(k["stepup_legit_rate"], 0.05)

    def test_kpi_reproducible(self):
        b = self.b
        self.assertEqual((b["tp"], b["fp"], b["fn"]), (106, 10, 22))
        self.assertEqual(self.rep["kpi"]["intervene_tp"], 120)
        self.assertAlmostEqual(b["pr_auc"], 0.934, places=3)

    def test_levels_and_cases(self):
        self.assertEqual(self.rep["risk_level_counts"], {"LOW": 7143, "MEDIUM": 368, "HIGH": 316, "CRITICAL": 173})
        self.assertEqual(len(self.res["cases"]), 341)
        self.assertAlmostEqual(self.rep["threshold"], 0.6847, places=4)
        self.assertAlmostEqual(self.rep["medium_threshold"], 0.4349, places=4)

    def test_new_fraud_types(self):
        tot = self.rep["loto"][-1]
        self.assertEqual((tot["n"], tot["high"], tot["medium_plus"]), (128, 76, 117))

    # --- File nộp đúng template BTC ---
    def test_submission_matches_template(self):
        tpl = pd.read_csv(io.BytesIO(self.files["submission_output_template.csv"]), encoding="utf-8-sig")
        sub = self.res["submission"]
        self.assertEqual(list(sub.columns), list(tpl.columns))
        self.assertEqual(list(sub.transaction_id), list(tpl.transaction_id))
        self.assertTrue(sub.risk_score.between(0, 1).all())
        self.assertTrue(set(sub.risk_level) <= {"LOW", "MEDIUM", "HIGH", "CRITICAL"})
        held = sub.risk_level.isin(["HIGH", "CRITICAL"]).astype(int)
        self.assertTrue((held == sub.predicted_fraud).all())
        self.assertTrue(sub.alert_reason.notna().all())

    # --- Chấm thời gian thực không dùng dữ liệu tương lai ---
    def test_stream_equals_batch(self):
        p = RT.parity_check(self.res["model"], self.res["tables"])
        self.assertEqual(p["n"], 8000)
        self.assertEqual(p["n_score_mismatch"], 0)
        self.assertEqual(p["n_level_mismatch"], 0)
        self.assertLess(p["latency_mean_ms"], 100)

    # --- 4 kịch bản dựng sẵn của app FS Pay, trên 30 khách demo ---
    def test_fspay_presets(self):
        sc, hist, custs = S.warm_scorer(self.res)
        merch = self.res["tables"]["merchants.csv"]
        expect = {"Mua sắm bình thường": {"LOW"}, "Máy lạ ở nước ngoài": {"HIGH", "CRITICAL"},
                  "Thử sai OTP liên tục": {"CRITICAL"}, "Chuyển gấp 10 lần": {"MEDIUM", "HIGH", "CRITICAL"}}
        for name, ok in expect.items():
            for cid in custs:
                with self.subTest(kich_ban=name, khach=cid):
                    self.assertIn(str(S.send_preset(sc, hist, merch, cid, name)["risk_level"]), ok)


class TestEdgeCases(unittest.TestCase):
    def test_no_labels_scores_with_pretrained_model(self):
        files = {k: v for k, v in _paths.btc_files().items() if k != "fraud_labels_sample.csv"}
        res = F.run(files)
        self.assertNotEqual(res["mode"], "train")
        self.assertEqual(len(res["submission"]), 8000)
        self.assertTrue(res["submission"].risk_score.notna().all())


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""Script đánh giá: chạy lại toàn bộ mô hình trên Data Pack BTC và ghi mọi kết quả, KPI ra một thư mục.

Chạy:  python evaluate.py [thư_mục_đầu_ra]      (mặc định: ./output)
Mất khoảng 1–3 phút. Kết quả giống hệt mỗi lần chạy vì cố định seed 42.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

import _paths
import fraud_core as F
import fs_realtime as RT
import fspay_sim as S

B = "Gộp 3 tầng – có hồ sơ (B, chính thức)"
FRAUD_VN = {"FAILED_THEN_SUCCESS": "Thử sai rồi thành công", "VELOCITY_BURST": "Giao dịch dồn dập",
            "AMOUNT_SPIKE": "Số tiền tăng vọt", "NEW_DEVICE": "Thiết bị mới",
            "LOCATION_ANOMALY": "Nơi lạ, IP nước ngoài", "HIGH_RISK_MERCHANT": "Merchant rủi ro cao"}


def csv(df, path):
    df.to_csv(path, index=False, encoding="utf-8-sig")


def main(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    files = _paths.btc_files()
    t = time.time()
    _, checks, ok = F.validate(files)
    res = F.run(files)
    sec = time.time() - t
    rep, df = res["report"], res["df"]
    b = rep["comparison_nested_cv"][B]
    k = rep["kpi"]

    # 1. Đầu ra hệ thống
    csv(res["submission"], out / "submission_output.csv")
    csv(res["cases"], out / "cases.csv")
    csv(df.drop(columns=["ts"], errors="ignore"), out / "scored_transactions_detail.csv")
    csv(pd.DataFrame(checks), out / "data_checks.csv")
    (out / "kpi_report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    # 2. Bảng KPI, ma trận nhầm lẫn, recall theo kiểu, baseline, top-k
    n_fr = int(res["lab_view"].y.sum())
    n_ok = len(res["lab_view"]) - n_fr
    kpi = [("Precision (chặn)", b["precision"], "TP/(TP+FP)", "≥ 0,90"),
           ("Recall chặn", b["recall"], "TP/(TP+FN)", "≥ 0,80 (BTC)"),
           ("Gian lận bị can thiệp", k["intervene_recall"], "(chặn + xác thực thêm)/128", "≥ 0,90"),
           ("F1", b["f1"], "2PR/(P+R)", "≥ 0,75 (BTC)"),
           ("PR-AUC", b["pr_auc"], "average precision", "tham khảo"),
           ("FPR chặn", b["fp"] / n_ok, "FP/1.872", "tham khảo"),
           ("Khách thật phải xác thực thêm", k["stepup_legit_rate"], "MEDIUM thật/1.872", "≤ 5%"),
           ("Can thiệp khi ẩn từng kiểu", rep["loto"][-1]["medium_plus"] / rep["loto"][-1]["n"], "ca can thiệp/128", "≥ 0,90")]
    csv(pd.DataFrame(kpi, columns=["kpi", "ket_qua", "cong_thuc", "muc_tieu"]), out / "kpi_summary.csv")
    tn = n_ok - b["fp"]
    csv(pd.DataFrame([["Gian lận", b["tp"], b["fn"]], ["Bình thường", b["fp"], tn]],
                     columns=["thuc_te", "du_doan_tam_giu", "du_doan_khong_tam_giu"]), out / "confusion_matrix.csv")
    cnt = {t: v for t, v in rep["labeled_counts"].items() if t != "NORMAL"}
    A, I = rep["detected_by_type"][B], k["intervene_by_type"]
    csv(pd.DataFrame([{"kieu": FRAUD_VN.get(t, t), "so_ca": n, "tam_giu": A.get(t, 0), "recall_tam_giu": A.get(t, 0) / n,
                       "can_thiep": I.get(t, 0), "recall_can_thiep": I.get(t, 0) / n} for t, n in cnt.items()]),
        out / "recall_by_fraud_type.csv")
    csv(pd.DataFrame([{"phuong_phap": m, **{c: v.get(c) for c in ["recall", "precision", "f1", "pr_auc", "tp", "fp", "fn"]}}
                      for m, v in rep["comparison_nested_cv"].items()]), out / "baseline_comparison.csv")
    lv = res["lab_view"]
    order = np.argsort(-lv.score.values, kind="stable")
    y = lv.y.values[order]
    csv(pd.DataFrame([{"k": kk, "gian_lan_trong_top_k": int(y[:kk].sum()), "precision_at_k": y[:kk].sum() / kk,
                       "recall_at_k": y[:kk].sum() / n_fr} for kk in (25, 50, 100, 128, 150, 200)]), out / "topk.csv")
    csv(pd.DataFrame(rep["loto"]).drop(columns=["grid"], errors="ignore"), out / "leave_one_type_out.csv")

    # 3. Kiểm tra chấm thời gian thực trùng chấm theo lô
    par = RT.parity_check(res["model"], res["tables"])
    (out / "parity_stream_vs_batch.json").write_text(json.dumps(par, ensure_ascii=False, indent=2, default=str),
                                                     encoding="utf-8")

    # 4. Bốn kịch bản app FS Pay trên 30 khách demo
    sc, hist, custs = S.warm_scorer(res)
    merch = res["tables"]["merchants.csv"]
    rows = []
    for name in S.PRESETS:
        for cid in custs:
            r = S.send_preset(sc, hist, merch, cid, name)
            rows.append({"kich_ban": name, "khach": cid, "diem": r["risk_score"], "muc": str(r["risk_level"]),
                         "ms": r["latency_ms"]})
    fs = pd.DataFrame(rows)
    csv(fs, out / "fspay_scenarios.csv")

    summary = {
        "thoi_gian_chay_giay": round(sec, 1), "du_lieu_hop_le": ok, "so_giao_dich": len(df),
        "muc_rui_ro": rep["risk_level_counts"], "so_ho_so": len(res["cases"]),
        "nguong_tam_giu": rep["threshold"], "nguong_xac_thuc_them": rep["medium_threshold"],
        "precision": b["precision"], "recall_tam_giu": b["recall"], "recall_can_thiep": k["intervene_recall"],
        "f1": b["f1"], "pr_auc": b["pr_auc"], "tp_fp_fn": [b["tp"], b["fp"], b["fn"]],
        "chay_luong_lech_diem": par["n_score_mismatch"], "chay_luong_lech_muc": par["n_level_mismatch"],
        "latency_tb_ms": par["latency_mean_ms"],
        "fspay": fs.groupby("kich_ban").muc.value_counts().unstack(fill_value=0).to_dict(orient="index"),
    }
    (out / "evaluation_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str),
                                                 encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    return summary


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent / "output")

"""Mô phỏng 4 kịch bản dựng sẵn của app khách FS Pay, giống hệt cách streamlit_app.py tạo giao dịch
(_ph_preset + _ph_submit), nhưng chạy không cần giao diện."""
import copy

import pandas as pd

import _paths  # noqa: F401
import fs_realtime as RT

PROV = ["Hanoi", "Ho Chi Minh City", "Da Nang", "Hai Phong", "Can Tho", "Thanh Hoa", "Nghe An", "Hung Yen",
        "Bac Ninh", "Quang Ninh"]
PRESETS = {
    "Mua sắm bình thường": dict(dev=0, home=True, ip="VN", otp=0, mult=1.0,
                                cat=["FASHION", "GROCERY", "ONLINE_MARKETPLACE"], mrisk="LOW"),
    "Máy lạ ở nước ngoài": dict(dev=1, home=False, ip="SG", otp=0, mult=5.0,
                                cat=["ELECTRONICS", "ONLINE_MARKETPLACE"], mrisk="LOW"),
    "Thử sai OTP liên tục": dict(dev=1, home=True, ip="VN", otp=1, mult=3.0, cat=["GAMING"], mrisk="LOW"),
    "Chuyển gấp 10 lần": dict(dev=0, home=True, ip="VN", otp=0, mult=10.0,
                              cat=["MONEY_TRANSFER", "GAMING", "HOTEL"], mrisk="HIGH"),
}
GAP_S = 3 * 3600  # mặc định "Vài giờ trước"


def warm_scorer(res):
    """Bộ chấm luồng đã nạp toàn bộ lịch sử BTC, như trang Giám sát thời gian thực."""
    T = res["tables"]
    hist = RT.stream_order(T["transactions.csv"])
    sc = RT.OnlineScorer(res["model"], T["customers.csv"], T["merchants.csv"], T["devices.csv"])
    sc.warm(hist.to_dict("records"))
    cnt = hist.customer_id.value_counts()
    demo_custs = sorted(cnt[cnt >= 10].index.tolist(), key=lambda c: -cnt[c])[:30]
    return sc, hist, demo_custs


def send_preset(sc0, hist, merch, cid, name):
    """Gửi một kịch bản cho một khách trên bản sao của bộ chấm (không ảnh hưởng lần gửi khác)."""
    sc = copy.deepcopy(sc0)
    p = PRESETS[name]
    k = sc.cust.get(cid, {})
    h = hist[hist.customer_id == cid]
    home = k.get("home_location", "Hanoi")
    avg = float(k.get("avg_transaction_amount", 1e6) or 1e6)
    other = [x for x in PROV if x != home]
    loc = home if p["home"] else other[sum(map(ord, cid)) % len(other)]
    chan = h.payment_channel.mode().iloc[0] if len(h) else "MOBILE_BANKING"
    pool = merch[merch.merchant_category.isin(p["cat"]) & (merch.merchant_risk_level == p["mrisk"])]
    if not len(pool):
        pool = merch[merch.merchant_risk_level == p["mrisk"]]
    mer = pool.merchant_id.iloc[0]
    clock = pd.Timestamp(hist.datetime.iloc[-1])
    if p["dev"] == 0:
        dev = h.device_id.mode().iloc[0] if len(h) else f"DEV-{cid}"
    else:
        dev = "DEV-LA-0001"
        sc.dev[dev] = {"first_seen_date": clock.normalize(), "registered_customer_id": None,
                       "device_risk_level": "MEDIUM", "rooted_or_jailbroken": False, "emulator_flag": False}
    last = sc.C.get(cid, {}).get("last")
    base = clock + pd.Timedelta(seconds=15)
    if last is not None:
        base = max(base, pd.Timestamp("2000-01-01") + pd.Timedelta(seconds=last + GAP_S))
    statuses = ["FAILED", "FAILED", "SUCCESS"] if p["otp"] else ["SUCCESS"]
    out = None
    for i, stt in enumerate(statuses):
        t = {"transaction_id": f"LIVE-{i}", "customer_id": cid, "merchant_id": mer,
             "datetime": base + pd.Timedelta(seconds=20 * i), "amount": float(int(round(avg * p["mult"] / 1000) * 1000)),
             "currency": "VND", "payment_channel": chan if chan in RT_CHANNELS else "MOBILE_BANKING",
             "device_id": dev, "location": loc, "transaction_status": stt, "ip_country": p["ip"],
             "is_card_present": False, "authentication_method": "BIOMETRIC" if p["dev"] == 0 else "OTP"}
        out = sc.score(t)
    return out  # kết quả của giao dịch cuối (giao dịch thành công)


RT_CHANNELS = {"MOBILE_BANKING", "E_WALLET", "CARD", "QR", "BANK_TRANSFER"}

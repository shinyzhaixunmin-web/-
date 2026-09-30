#!/usr/bin/env python3
"""生成虚构的两店沙龙演示数据（固定随机种子，结果可复现）。

用法: python3 examples/demo-salon/gen_demo_data.py
输出: examples/demo-salon/data/*.csv

虚构设定（仅供演示，不代表任何真实门店）:
- 数据期间 2026-01-01 ~ 2026-06-30，两家店：A店（旗舰）、B店
- A店自 2026-04-01 起在"护理"项目试点"离店当场预约下次"
  - 5 名技师中 A1、A2 执行到位，A3、A4、A5 偶尔执行
  - A5 于 2026-05-15 离职
- B店 3 月做了一次大型储值活动
"""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)
OUT = Path(__file__).parent / "data"
START, END = date(2026, 1, 1), date(2026, 6, 30)
PILOT_START = date(2026, 4, 1)
A5_LEAVE = date(2026, 5, 15)

SERVICES = {"护理": 380, "剪发": 180, "染烫": 880}
STYLISTS = {"A店": ["A1", "A2", "A3", "A4", "A5"], "B店": ["B1", "B2", "B3"]}
NEW_PER_MONTH = {"A店": 80, "B店": 40}
OLD_POOL = {"A店": 300, "B店": 120}
CHANNELS = [("自然到店", 0.30), ("老客介绍", 0.20), ("团购平台", 0.35), ("社交媒体", 0.15)]


def pick(weighted):
    r, acc = random.random(), 0.0
    for item, w in weighted:
        acc += w
        if r < acc:
            return item
    return weighted[-1][0]


def days(d0, d1):
    return [d0 + timedelta(n) for n in range((d1 - d0).days + 1)]


def stylists_on(store, d):
    return [s for s in STYLISTS[store] if not (s == "A5" and d >= A5_LEAVE)]


def booked_rate(store, stylist, service, d):
    if store == "A店" and service == "护理" and d >= PILOT_START:
        return 0.75 if stylist in ("A1", "A2") else 0.25
    return 0.15


customers, visits, cards, vid = [], [], [], 0


def add_visit(d, store, cid, service, pay_type):
    global vid
    vid += 1
    stylist = random.choice(stylists_on(store, d))
    booked = random.random() < booked_rate(store, stylist, service, d)
    visits.append({
        "visit_id": f"V{vid:06d}", "date": d.isoformat(), "store": store,
        "customer_id": cid, "stylist": stylist, "service": service,
        "amount": SERVICES[service], "pay_type": pay_type,
        "booked_next": "是" if booked else "否",
        "complaint": "是" if random.random() < 0.02 else "否",
    })
    return booked


# 存量老客：数据期间内每月约 55% 概率到店一次，约 40% 用储值卡扣款
for store, n in OLD_POOL.items():
    for i in range(n):
        cid = f"{store[0]}O{i:04d}"
        customers.append({"customer_id": cid, "store": store,
                          "first_visit_date": "2024-06-01", "channel": "存量老客"})
        for m in range(1, 7):
            if random.random() < 0.55:
                d = date(2026, m, random.randint(1, 28))
                svc = pick([("护理", 0.45), ("剪发", 0.35), ("染烫", 0.20)])
                add_visit(d, store, cid, svc, "耗卡" if random.random() < 0.4 else "现付")

# 新客
seq = 0
for store, per_month in NEW_PER_MONTH.items():
    for m in range(1, 7):
        for _ in range(per_month):
            seq += 1
            cid = f"C{seq:05d}"
            first = date(2026, m, random.randint(1, 28 if m == 2 else 30))
            channel = pick(CHANNELS)
            customers.append({"customer_id": cid, "store": store,
                              "first_visit_date": first.isoformat(), "channel": channel})
            svc = pick([("护理", 0.55), ("剪发", 0.30), ("染烫", 0.15)])
            booked = add_visit(first, store, cid, svc, "现付")
            # 60 天复购概率：离店预约显著提高；团购客群意向偏低
            p = 0.55 if booked else 0.22
            if channel == "团购平台":
                p -= 0.10
            if random.random() < p:
                back = first + timedelta(random.randint(10, 60))
                if back <= END:
                    add_visit(back, store, cid, svc, "现付")
            # 首次办卡
            if random.random() < 0.12:
                cards.append({"date": first.isoformat(), "store": store,
                              "customer_id": cid, "amount": random.choice([2000, 3000, 5000])})

# B店 3 月储值活动：存量老客集中办卡
for i in range(OLD_POOL["B店"]):
    if random.random() < 0.35:
        cards.append({"date": date(2026, 3, random.randint(8, 22)).isoformat(), "store": "B店",
                      "customer_id": f"BO{i:04d}", "amount": random.choice([3000, 5000, 10000])})

visits.sort(key=lambda v: (v["date"], v["visit_id"]))
cards.sort(key=lambda c: c["date"])
for i, c in enumerate(cards, 1):
    c["sale_id"] = f"S{i:05d}"

staff = [{"date": "2026-05-15", "store": "A店", "stylist": "A5", "event": "离职"}]


def write(name, rows, fields):
    with open(OUT / name, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


OUT.mkdir(exist_ok=True)
write("customers.csv", customers, ["customer_id", "store", "first_visit_date", "channel"])
write("visits.csv", visits, ["visit_id", "date", "store", "customer_id", "stylist", "service",
                             "amount", "pay_type", "booked_next", "complaint"])
write("card_sales.csv", cards, ["sale_id", "date", "store", "customer_id", "amount"])
write("staff_events.csv", staff, ["date", "store", "stylist", "event"])
print(f"顾客 {len(customers)}，到店 {len(visits)}，办卡 {len(cards)} → {OUT}")

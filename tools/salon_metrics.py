#!/usr/bin/env python3
"""沙龙经营基线与试点指标计算（仅用标准库）。

用法:
    python3 tools/salon_metrics.py <数据目录> [--out 报告.md] [--window 60]
        [--pilot-store A店 --pilot-service 护理 --pilot-start 2026-04-01 [--compare-store B店]]

数据格式见 examples/demo-salon/data/数据字典.md。
口径规则:
- 收入 = 服务消耗确认的金额（visits.amount）。办卡金额单列为预收，不计入收入。
- 复购按"首次到店月份"分组；一组新客要等全部成员都满观察窗口后才计算，否则显示到期日。
- 没有 costs.csv 时，利润标注"待补"，不做估算。
"""
import argparse
import calendar
import csv
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path


def read_csv(path: Path, required=True):
    if not path.exists():
        if required:
            raise SystemExit(f"缺少必需文件: {path}")
        return []
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def d(s: str) -> date:
    return date.fromisoformat(s.strip())


def month_end(ym: str) -> date:
    y, m = map(int, ym.split("-"))
    return date(y, m, calendar.monthrange(y, m)[1])


def pct(num, den):
    return f"{num / den:.0%}" if den else "—"


SMALL = 30  # 样本量低于此值时标注"样本小"


def rate(num, den):
    """比例；样本小于 SMALL 时加警示，提醒只能看方向。"""
    if not den:
        return "—"
    return pct(num, den) + (" ⚠️样本小" if den < SMALL else "")


def money(x):
    return f"{x:,.0f}"


def table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


class Data:
    def __init__(self, folder: Path, window: int, until: date = None):
        self.window = window
        self.customers = {c["customer_id"]: c for c in read_csv(folder / "customers.csv")}
        self.visits = [v for v in read_csv(folder / "visits.csv")
                       if until is None or d(v["date"]) <= until]
        self.cards = [c for c in read_csv(folder / "card_sales.csv")
                      if until is None or d(c["date"]) <= until]
        self.staff = [s for s in read_csv(folder / "staff_events.csv", required=False)
                      if until is None or d(s["date"]) <= until]
        self.costs = read_csv(folder / "costs.csv", required=False)
        for v in self.visits:
            v["_d"] = d(v["date"])
            v["_amt"] = float(v["amount"])
        self.start = min(v["_d"] for v in self.visits)
        self.end = max(v["_d"] for v in self.visits)
        self.stores = sorted({v["store"] for v in self.visits})

        by_c = defaultdict(list)
        for v in self.visits:
            by_c[v["customer_id"]].append(v)
        self.new = []  # 数据期间内的新客，附首次到店记录与复购结果
        for cid, c in self.customers.items():
            first = d(c["first_visit_date"])
            if not (self.start <= first <= self.end):
                continue
            vs = sorted(by_c.get(cid, []), key=lambda v: v["_d"])
            first_v = next((v for v in vs if v["_d"] == first), None)
            if first_v is None:
                continue
            back = any(first < v["_d"] <= first + timedelta(window) for v in vs)
            self.new.append({"id": cid, "store": c["store"], "channel": c["channel"],
                             "first": first, "cohort": first.strftime("%Y-%m"),
                             "v": first_v, "back": back})

    def cohort_due(self, cohort: str) -> date:
        return month_end(cohort) + timedelta(self.window)

    def complete(self, cohort: str) -> bool:
        return self.cohort_due(cohort) <= self.end


def section_revenue(D: Data):
    rev = defaultdict(lambda: {"现付": 0.0, "耗卡": 0.0})
    for v in D.visits:
        rev[(v["_d"].strftime("%Y-%m"), v["store"])][v["pay_type"]] += v["_amt"]
    card = defaultdict(float)
    for c in D.cards:
        card[(c["date"][:7], c["store"])] += float(c["amount"])
    cost = defaultdict(float)
    for c in D.costs:
        cost[(c["month"], c["store"])] += float(c["amount"])
    rows = []
    for key in sorted(set(rev) | set(card)):
        r = rev[key]
        income = r["现付"] + r["耗卡"]
        profit = money(income - cost[key]) if D.costs else "待补（无成本数据）"
        rows.append([key[0], key[1], money(income), money(r["现付"]), money(r["耗卡"]),
                     money(card[key]), money(card[key] - r["耗卡"]), profit,
                     money(income + card[key])])
    return ("## 1. 收入与预收（按月 × 门店）\n\n"
            "收入按服务消耗确认；办卡是预收款（负债），单列。"
            "最后一列 ❌ 是**错误口径**（收入与办卡相加），只用来对比，不能拿来看业绩。\n\n"
            + table(["月份", "门店", "服务收入", "其中现付", "其中耗卡", "办卡预收",
                     "预收余额净增", "经营利润", "❌混算营业额"], rows))


def section_new(D: Data):
    cnt = defaultdict(int)
    ch = defaultdict(lambda: defaultdict(int))
    for n in D.new:
        cnt[(n["cohort"], n["store"])] += 1
        ch[n["store"]][n["channel"]] += 1
    rows = [[k[0], k[1], cnt[k]] for k in sorted(cnt)]
    ch_rows = [[s, c, k, pct(k, sum(ch[s].values()))]
               for s in sorted(ch) for c, k in sorted(ch[s].items(), key=lambda x: -x[1])]
    return ("## 2. 新客\n\n" + table(["月份", "门店", "新客数"], rows)
            + "\n\n**渠道构成（全期）**\n\n" + table(["门店", "渠道", "新客数", "占比"], ch_rows))


def section_repurchase(D: Data):
    W = D.window
    g = defaultdict(lambda: [0, 0])
    for n in D.new:
        g[(n["cohort"], n["store"])][0] += 1
        g[(n["cohort"], n["store"])][1] += n["back"]
    rows = []
    for k in sorted(g):
        tot, back = g[k]
        if D.complete(k[0]):
            rows.append([k[0], k[1], tot, back, pct(back, tot)])
        else:
            rows.append([k[0], k[1], tot, "—", f"未满窗口，{D.cohort_due(k[0])} 后可算"])

    def split(key_fn, label):
        s = defaultdict(lambda: [0, 0])
        for n in D.new:
            if D.complete(n["cohort"]):
                s[(n["store"], key_fn(n))][0] += 1
                s[(n["store"], key_fn(n))][1] += n["back"]
        if not s:
            return "（暂无已满窗口的月份组）"
        return table(["门店", label, "新客数", f"{W}天复购率"],
                     [[k[0], k[1], v[0], rate(v[1], v[0])] for k, v in sorted(s.items())])

    return (f"## 3. 固定新客群的 {W} 天复购率\n\n"
            f"按首次到店月份分组；一组新客要等全部成员满 {W} 天后才计算（数据截止 {D.end}）。\n\n"
            + table(["首次到店月份", "门店", "新客数", "复购人数", f"{W}天复购率"], rows)
            + "\n\n**按渠道拆分（只含已满窗口的月份组）**\n\n" + split(lambda n: n["channel"], "渠道")
            + "\n\n**按首次离店是否当场预约拆分（只含已满窗口的月份组）**\n\n"
            + split(lambda n: "当场预约" if n["v"]["booked_next"] == "是" else "未预约", "离店预约"))


def section_booking_complaint(D: Data):
    b = defaultdict(lambda: [0, 0])
    for n in D.new:
        b[(n["cohort"], n["store"])][0] += 1
        b[(n["cohort"], n["store"])][1] += n["v"]["booked_next"] == "是"
    comp = defaultdict(lambda: [0, 0])
    for v in D.visits:
        k = (v["_d"].strftime("%Y-%m"), v["store"])
        comp[k][0] += 1
        comp[k][1] += v["complaint"] == "是"
    keys = sorted(set(b) | set(comp))
    rows = [[k[0], k[1], pct(b[k][1], b[k][0]), comp[k][0], comp[k][1],
             f"{comp[k][1] / comp[k][0] * 100:.1f}" if comp[k][0] else "—"] for k in keys]
    staff = ""
    if D.staff:
        staff = "\n\n**人员变动**\n\n" + table(["日期", "门店", "技师", "变动"],
                                            [[s["date"], s["store"], s["stylist"], s["event"]] for s in D.staff])
    return ("## 4. 离店预约率、服务量与投诉\n\n离店预约率 = 新客首次到店时当场预约下次的比例。\n\n"
            + table(["月份", "门店", "新客离店预约率", "服务单数", "投诉数", "每百单投诉"], rows) + staff)


def section_pilot(D: Data, store, service, start, compare):
    W = D.window

    def group(st, before):
        return [n for n in D.new if n["store"] == st and n["v"]["service"] == service
                and ((n["first"] < start) if before else (n["first"] >= start))]

    def stats(ns):
        book = sum(n["v"]["booked_next"] == "是" for n in ns)
        done = [n for n in ns if D.complete(n["cohort"])]
        back = sum(n["back"] for n in done)
        return [len(ns), rate(book, len(ns)), len(done), rate(back, len(done)) if done else "未满窗口"]

    rows = [[f"{store} 试点前", *stats(group(store, True))],
            [f"{store} 试点后", *stats(group(store, False))]]
    if compare:
        rows += [[f"{compare} 同期前（对照）", *stats(group(compare, True))],
                 [f"{compare} 同期后（对照）", *stats(group(compare, False))]]

    after = group(store, False)
    st = defaultdict(list)
    for n in after:
        st[n["v"]["stylist"]].append(n)
    st_rows = [[s, *stats(ns)] for s, ns in sorted(st.items())]

    def complaints(st_, before):
        vs = [v for v in D.visits if v["store"] == st_ and v["service"] == service
              and ((v["_d"] < start) if before else (v["_d"] >= start))]
        return len(vs), sum(v["complaint"] == "是" for v in vs)

    prot = []
    for st_ in [store] + ([compare] if compare else []):
        for before, label in ((True, "前"), (False, "后")):
            n, c = complaints(st_, before)
            prot.append([f"{st_} 试点{label}", n, c, f"{c / n * 100:.1f}" if n else "—"])

    pending = sorted({n["cohort"] for n in after if not D.complete(n["cohort"])})
    note = ("、".join(f"{c}（{D.cohort_due(c)} 后）" for c in pending)) or "无"
    return (f"## 5. 试点对比：{store} ·「{service}」· {start} 起\n\n"
            f"复购只统计已满 {W} 天窗口的月份组。尚未满窗口的试点月份组：{note}。"
            f"样本少于 {SMALL} 人的比例标注 ⚠️样本小，只能看方向，不能下结论。\n\n"
            + table(["组别", "新客数", "离店预约率（过程）", "已满窗口新客", f"{W}天复购率（结果）"], rows)
            + "\n\n**试点后按技师拆分**\n\n"
            + table(["技师", "新客数", "离店预约率", "已满窗口新客", f"{W}天复购率"], st_rows)
            + f"\n\n**保护指标：「{service}」服务投诉**\n\n"
            + table(["组别", "服务单数", "投诉数", "每百单投诉"], prot))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("data_dir", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--window", type=int, default=60)
    ap.add_argument("--pilot-store")
    ap.add_argument("--pilot-service")
    ap.add_argument("--pilot-start")
    ap.add_argument("--compare-store")
    ap.add_argument("--until", help="只使用该日期（含）之前的数据，用于还原当时能看到的基线")
    a = ap.parse_args()

    D = Data(a.data_dir, a.window, d(a.until) if a.until else None)
    parts = [f"# 经营基线报告\n\n> 由 `tools/salon_metrics.py` 生成 · 数据期间 {D.start} ~ {D.end} · "
             f"门店：{'、'.join(D.stores)} · 新客 {len(D.new)} 人 · 服务单 {len(D.visits)} 张\n",
             section_revenue(D), section_new(D), section_repurchase(D), section_booking_complaint(D)]
    if a.pilot_store and a.pilot_service and a.pilot_start:
        parts.append(section_pilot(D, a.pilot_store, a.pilot_service, d(a.pilot_start), a.compare_store))
    report = "\n\n".join(parts) + "\n"
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(report, encoding="utf-8")
        print(f"已写入 {a.out}")
    else:
        print(report)


if __name__ == "__main__":
    main()

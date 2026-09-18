#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""择日主程序：硬禁忌筛除、吉凶评分、排序定案、择吉时。

用法：
    python3 scripts/select_date.py plan    --config input.json [--out result.json]
    python3 scripts/select_date.py almanac --date 2026-11-14 [--bride-zodiac 兔]
    python3 scripts/select_date.py hours   --date 2026-11-14 [--matter 嫁娶] [--avoid-zodiac 鼠 ...]

玄学参数一律外置在 scripts/rules.json，调规则不必动本文件。
"""

import argparse
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import almanac as A

RULES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rules.json")
XING_HAI_PO = {"三刑", "自刑", "六害", "相破"}


def load_rules(path=RULES_PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def resolve_matter(matter, rules):
    """事由归类由 agent 完成，这里只做名称与别名的对表，认不出则落到「通用」。"""
    table = rules["事由"]
    if matter in table:
        return matter, table[matter]
    for key, cfg in table.items():
        if matter in cfg.get("别名", []):
            return key, cfg
    return "通用", table["通用"]


def folk_enabled(name, rules):
    return rules["民俗开关"].get(name, True)


def hard_taboos(day, rels, cfg, rules, level):
    """返回该日的淘汰原因列表，空列表表示存活。

    正冲主事人与天克地冲主事人恒定执行，不受放宽阶梯影响（program.md 总则二）。
    """
    reasons = []
    for r in rels:
        if r["role"] != "primary":
            continue
        if "六冲" in r["relations"]:
            reasons.append("日支%s正冲主事人%s生肖%s" % (day["day_zhi"], r["name"], r["zodiac"]))
        if r["天克地冲"]:
            reasons.append("日柱%s天克地冲主事人%s日柱" % (day["ganzhi"]["day"], r["name"]))

    off = set(level["停用禁忌"])
    if "*" in off:
        return reasons

    for name in rules["通用硬禁忌"]["凶煞"]:
        if name not in off and name in day["xiongsha"]:
            detail = day["extra"].get(name)
            reasons.append("犯%s%s" % (name, "（%s）" % detail if detail else ""))

    if "出局建星" not in off and day["zhixing"] in cfg["出局建星"]:
        reasons.append("建星值%s，本事由不取" % day["zhixing"])

    for name in cfg["专属大忌"]:
        if name in off or not folk_enabled(name, rules):
            continue
        if name in day["xiongsha"] or day["extra"].get(name) is True:
            reasons.append("犯本事由专属大忌%s" % name)

    allowed = level["行嫁月允许"]
    status = day["extra"].get("行嫁月")
    if cfg["查行嫁月"] and allowed is not None and status and status not in allowed:
        reasons.append("农历%d月于女方为「%s」，非行嫁利月" % (day["lunar_month"], status))
    return reasons


def score_day(day, rels, hours, cfg, rules):
    """按 rules.json 的权重表逐项加减，返回 (总分, 明细)。"""
    w = rules["评分"]
    detail = [{"item": "基准分", "delta": w["基准分"]}]

    if "天赦" in day["jishen"]:
        detail.append({"item": "天赦日", "delta": w["天赦日"]})
    for name in w["天德月德类项目"]:
        if name in day["jishen"]:
            detail.append({"item": "%s值日" % name, "delta": w["天德月德类每项"]})

    if day["tianshen_type"] == "黄道":
        detail.append({"item": "黄道%s值日" % day["tianshen"], "delta": w["黄道六神值日"]})
    else:
        detail.append({"item": "黑道%s值日" % day["tianshen"], "delta": w["黑道六神值日"]})

    if day["zhixing"] in cfg["宜用建星"]:
        detail.append({"item": "建星值%s，与本事由相合" % day["zhixing"],
                       "delta": w["建星与事由相合"]})
    elif day["zhixing"] in cfg["忌用建星"]:
        detail.append({"item": "建星值%s，与本事由相背" % day["zhixing"],
                       "delta": w["建星与事由相背"]})

    for r in rels:
        if r["role"] == "primary":
            if "三合" in r["relations"]:
                detail.append({"item": "日支三合主事人%s生肖%s" % (r["name"], r["zodiac"]),
                               "delta": w["日支三合主事人"]})
            if "六合" in r["relations"]:
                detail.append({"item": "日支六合主事人%s生肖%s" % (r["name"], r["zodiac"]),
                               "delta": w["日支六合主事人"]})
            hit = [x for x in r["relations"] if x in XING_HAI_PO]
            if hit:
                detail.append({"item": "日支%s主事人%s" % ("、".join(hit), r["name"]),
                               "delta": w["刑害破主事人"]})
            if r["太岁"]:
                detail.append({"item": "主事人%s%s" % (r["name"], r["太岁"]),
                               "delta": w["值太岁或冲太岁"]})
        elif "六冲" in r["relations"]:
            detail.append({"item": "日支正冲次要参与者%s生肖%s" % (r["name"], r["zodiac"]),
                           "delta": w["正冲次要参与者每人"]})

    got = [x for x in cfg["专用吉神"] if x in day["jishen"]
           and x not in w["天德月德类项目"]]
    if got:
        delta = min(len(got) * w["专用吉神每项"], w["专用吉神上限"])
        detail.append({"item": "本事由专用吉神：%s" % "、".join(got), "delta": delta})

    for name in w["小煞项目"]:
        if name in day["xiongsha"]:
            detail.append({"item": "犯%s" % name, "delta": w["小煞每项"]})
    if day["extra"].get("杨公忌") and folk_enabled("杨公忌", rules):
        detail.append({"item": "犯杨公忌", "delta": w["杨公忌"]})

    usable = [h for h in hours if not h["excluded"] and h["tianshen_type"] == "黄道"]
    if len(usable) >= 3:
        detail.append({"item": "当日可用黄道吉时 %d 个" % len(usable),
                       "delta": w["黄道吉时三个以上"]})
    return sum(x["delta"] for x in detail), detail


def pick_hours(day, cfg, avoid_zodiacs, limit=2):
    """第八步：先取黄道时，剔除日破与冲主事人之时，再按事由偏好与吉神多寡排序。"""
    all_hours = A.hour_chart(day, avoid_zodiacs)
    pref = cfg["偏好时辰"]
    usable = [h for h in all_hours if not h["excluded"]]
    pool = [h for h in usable if h["tianshen_type"] == "黄道"]
    note = None
    if not pool:
        pool = usable
        note = "当日黄道时尽被日破或冲主事人之冲所占，以下为降级取用的黑道时，须向用户点明"
    pool.sort(key=lambda h: (h["zhi"] not in pref, -len(h["reasons"]), A.zi(h["zhi"])))
    picked = pool[:limit]
    for h in picked:
        if h["zhi"] in pref:
            h["reasons"].append("合本事由取用时段（%s）" % cfg.get("偏好时辰说明", "见 rules.json"))
    return picked, note, all_hours


def rank_days(alive, rules, today):
    """第七步：总分 → 冲者多寡 → 黄道 → 建星等级 → 筹备余地 → 日期先后。"""
    grade = rules["排序"]["建星等级"]
    lead = rules["排序"]["筹备余地天数"]

    def key(d):
        chong_n = sum(1 for r in d["relations"] if "六冲" in r["relations"])
        days_out = (A.parse_date(d["solar"]) - today).days
        return (-d["score"], chong_n, d["tianshen_type"] != "黄道",
                -grade.get(d["zhixing"], 0), days_out < lead, days_out)

    return sorted(alive, key=key)


def spread(ranked, top_n, gap):
    """3 日尽量分散在不同旬或不同周；范围过短则逐级缩小间隔，照实给出。"""
    picked = ranked[:top_n]
    for g in (gap, 3, 1):
        chosen = []
        for d in ranked:
            cur = A.parse_date(d["solar"])
            if all(abs((cur - A.parse_date(c["solar"])).days) >= g for c in chosen):
                chosen.append(d)
            if len(chosen) == top_n:
                picked = chosen
                break
        if len(picked) == top_n:
            break
    dates = sorted(A.parse_date(d["solar"]) for d in picked)
    actual = min((b - a).days for a, b in zip(dates, dates[1:])) if len(dates) > 1 else None
    return picked, actual


def run_plan(config):
    rules = load_rules()
    matter_key, cfg = resolve_matter(config["matter"], rules)
    people = [A.person_chart(p) for p in config["people"]]
    primaries = [p for p in people if p["role"] == "primary"]
    if not primaries:
        return {"error": "people 中没有 role=primary 的主事人。"
                         "按 program.md 第一步，须先问清谁是主事人再排盘。"}

    bride = None
    if cfg["查行嫁月"]:
        brides = [p for p in primaries if p["gender"] == "female"]
        if brides:
            bride = brides[0]["zodiac"]

    dates = A.date_range(config["range"]["start"], config["range"]["end"])
    charts = [A.day_chart(d, bride_zodiac=bride) for d in dates]
    rel_map = {c["solar"]: [A.relations(c, p) for p in people] for c in charts}

    # 逐级放宽：只有一日都筛不出时才降级，不为凑满 top_n 而放宽（program.md 第四步）
    for level in rules["放宽阶梯"]:
        screened = [(c, rel_map[c["solar"]],
                     hard_taboos(c, rel_map[c["solar"]], cfg, rules, level)) for c in charts]
        chosen_level = level
        if any(not reasons for _, _, reasons in screened):
            break

    avoid = [p["zodiac"] for p in primaries]
    out_days, alive = [], []
    for c, rels, reasons in screened:
        hours, hour_note, all_hours = pick_hours(c, cfg, avoid)
        record = dict(c)
        record["relations"] = rels
        record["eliminated"] = bool(reasons)
        record["eliminate_reasons"] = reasons
        if reasons:
            record["score"] = None
            record["score_detail"] = []
            record["hours"] = []
        else:
            record["score"], record["score_detail"] = score_day(c, rels, all_hours, cfg, rules)
            record["hours"] = hours
            if hour_note:
                record["hours_note"] = hour_note
            alive.append(record)
        out_days.append(record)

    top_n = config.get("top_n", 3)
    today = datetime.date.today()
    ranked = rank_days(alive, rules, today)
    picked, actual_gap = spread(ranked, top_n, rules["排序"]["分散间隔天数"])

    result = {
        "matter": config["matter"],
        "matter_key": matter_key,
        "matter_raw": config.get("matter_raw", config["matter"]),
        "range": config["range"],
        "people": people,
        "bride_zodiac": bride,
        "relax_level": chosen_level["level"],
        "relax_note": chosen_level["说明"],
        "未取用": rules["未取用"],
        "counts": {"total": len(out_days), "alive": len(alive), "eliminated": len(out_days) - len(alive)},
        "min_gap_days": actual_gap,
        "selected": [d["solar"] for d in picked],
        "days": out_days,
    }
    if not alive:
        result["unavailable"] = ("逐级放宽至 level %d 仍无合用之日。按 program.md 第四步，"
                                 "不可硬凑，须如实告知用户并建议另择时段。" % chosen_level["level"])
    elif len(picked) < top_n:
        result["shortfall"] = ("范围内仅 %d 日通过硬禁忌，不足 %d 日。不得放宽凑数，"
                               "须如实说明并建议延长时间范围。" % (len(alive), top_n))
    if chosen_level["level"] > 0:
        result["relax_warning"] = ("本次已放宽至 level %d（%s），agent 必须在输出中明示降级情形。"
                                   % (chosen_level["level"], chosen_level["说明"]))
    return result


def main():
    ap = argparse.ArgumentParser(description="择日计算工具")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("plan", help="主命令：读 input.json，输出全量择日结果")
    p.add_argument("--config", required=True)
    p.add_argument("--out")

    a = sub.add_parser("almanac", help="单日排盘，调试用")
    a.add_argument("--date", required=True)
    a.add_argument("--bride-zodiac")

    h = sub.add_parser("hours", help="单日时辰盘，调试用")
    h.add_argument("--date", required=True)
    h.add_argument("--matter", default="通用")
    h.add_argument("--avoid-zodiac", nargs="*", default=[])

    args = ap.parse_args()
    if args.cmd == "plan":
        with open(args.config, encoding="utf-8") as f:
            data = run_plan(json.load(f))
    elif args.cmd == "almanac":
        data = A.day_chart(A.parse_date(args.date), bride_zodiac=args.bride_zodiac)
    else:
        rules = load_rules()
        _, cfg = resolve_matter(args.matter, rules)
        day = A.day_chart(A.parse_date(args.date))
        picked, note, all_hours = pick_hours(day, cfg, args.avoid_zodiac)
        data = {"solar": day["solar"], "day_ganzhi": day["ganzhi"]["day"],
                "picked": picked, "note": note, "all_hours": all_hours}

    text = json.dumps(data, ensure_ascii=False, indent=2)
    if args.cmd == "plan" and args.out and "error" not in data:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print("已写入 %s（共 %d 日，存活 %d 日，relax_level=%d，选定 %s）"
              % (args.out, data["counts"]["total"], data["counts"]["alive"],
                 data["relax_level"], "、".join(data["selected"]) or "无"))
    else:
        print(text)
    return 1 if "error" in data else 0


if __name__ == "__main__":
    sys.exit(main())

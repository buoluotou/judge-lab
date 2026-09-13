# -*- coding: utf-8 -*-
"""抽查原始记录：从 results/*.jsonl 里调出一条完整的证据链——
原文、变体、事实校验结果、四个配置的判分——全部是落盘的真实记录，不是示意。"""
import json, os, sys

sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(BASE, "results")


def load(name):
    return [json.loads(l) for l in open(os.path.join(R, name), encoding="utf-8")]


def hr(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


tid = "sa01"  # SSH 爆破研判——文章里引用过的例子
hr("抽查对象：任务 %s 的完整证据链" % tid)

orig = next(t["answer"] for t in __import__("tasks").TASKS if t["id"] == tid)
print("\n[原文]\n" + orig)

v = [r for r in load("variants.jsonl") if r["task"] == tid and r["style"] == "verbose"][-1]
print("\n[冗长版变体] ok=%s tries=%s chars=%d wall=%dms" % (v["ok"], v["tries"], v["chars"], v["wall_ms"] or 0))
print(v["text"][:120] + " ……")

judges = {}
for cfg in ("q25_base", "q25_rub", "q25_norm", "l32_base", "g22_base"):
    for r in load("judge_%s.jsonl" % cfg):
        if r["task"] == tid:
            judges[(cfg, r["style"])] = r["score"]
print("\n[评分记录]（style '-' = 原文）")
for cfg in ("q25_base", "q25_rub", "q25_norm", "l32_base", "g22_base"):
    print("  %-10s 原文=%s  冗长版=%s" % (cfg, judges.get((cfg, "-")), judges.get((cfg, "verbose"))))

pr = [r for r in load("pairs.jsonl") if r["kind"] == "sty" and r["b_style"] == "report"][:2]
print("\n[配对判定样例]（报告体翻盘实验的原始判定）")
for r in pr:
    print("  赢家原文=%s vs 输家%s的%s变体 | 顺序=%s | 裁判选择=%s" %
          (r["a_task"], r["b_task"], r["b_style"], r["order"], r["better"]))

hr("记录文件")
for f in sorted(os.listdir(R)):
    p = os.path.join(R, f)
    print("  %-24s %8.1f KB" % (f, os.path.getsize(p) / 1024))
print("\n以上每一条都能在 results/ 对应 jsonl 里逐字找到。")

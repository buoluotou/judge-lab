# -*- coding: utf-8 -*-
"""核对文章中的关键数字与 results/summary.json 完全一致。"""
import json, re, sys

sys.stdout.reconfigure(encoding="utf-8")
S = json.load(open("results/summary.json", encoding="utf-8"))
text = open(r"D:\edge\qax\article-judge\article.md", encoding="utf-8").read()

checks = []


def chk(name, cond, detail=""):
    checks.append((name, cond, detail))


si = S["si"]
chk("标题不再含'1945 次评分'口径", "1945 次本地评分" not in text and "文风操纵攻击与防御实测" in text)
chk("封面为'硬事实 0 变化'且带分母", "硬事实 0 变化" in text and "14/16" in text)
chk("无'0 字新事实'/'一分都没撼动'", "0 字新事实" not in text and "一分都没撼动" not in text)
chk("Wilson 置信区间已标注", "Wilson 95% 置信区间 67%~94%" in text)
chk("Judge 参数表已补", "temperature=0.3" in text and "seed=7" in text)
chk("仓库链接占位待填", "待替换为实际 GitHub/Gitee 地址" in text)
chk("标题调用次数 1945", "1945 次" in text)
chk("冗长 mean SI +0.57", "+0.57" in text and si["verbose"]["mean"] == 0.57)
chk("冗长 up16/flat12", si["verbose"]["up"] == 16 and si["verbose"]["flat"] == 12)
chk("冗长 ASR 57%", abs(si["verbose"]["asr"] - 0.571) < 1e-9 and "57%" in text)
chk("冗长 p<0.001", si["verbose"]["p_sign"] < 0.001)
chk("分点 -0.38", si["bullet"]["mean"] == -0.38 and "−0.38" in text)
chk("分点 11跌1涨 p=0.006", si["bullet"]["down"] == 11 and si["bullet"]["up"] == 1 and abs(si["bullet"]["p_sign"] - 0.0059) < 0.001)
chk("术语 0.00 全平", si["jargon"]["mean"] == 0.0 and si["jargon"]["up"] == 0 and si["jargon"]["flat"] == 30)
chk("术语2 +0.07", si["jargon2"]["mean"] == 0.07)
chk("笃定2 -0.07", si["confident2"]["mean"] == -0.07)
chk("报告 +0.17 / 21%", si["report"]["mean"] == 0.17 and abs(si["report"]["asr"] - 0.207) < 1e-9 and "21%" in text)
chk("原文均分锚定表述", "7.97" in text or "接近 8" in text)

prr = S["prr"]
chk("报告 PRR 88% (14/16)", prr["report"]["flips"] == 14 and prr["report"]["n_pairs"] == 16)
chk("冗长 PRR 73% (11/15)", prr["verbose"]["flips"] == 11 and prr["verbose"]["n_pairs"] == 15)
chk("有效配对16 淘汰14", S["prr_total_pairs"] == 30 and len(S["prr_excluded_pairs"]) == 14 and ("47%" in text or "近一半" in text))

d = S["defenses"]
mean_of = lambda cfg, f: round(sum(d[cfg][s][f] for s in S["env"]["styles"]) / 7, 2)
chk("基线 ASR 13%", mean_of("baseline", "asr") == 0.13)
chk("量规 ASR 28%", mean_of("rubric", "asr") == 0.28)
chk("量规报告 +1.03/59%", d["rubric"]["report"]["mean_si"] == 1.03 and abs(d["rubric"]["report"]["asr"] - 0.59) < 0.005)
chk("归一化分点 -0.04", d["normalize"]["bullet"]["mean_si"] == -0.04)
chk("归一化冗长 +0.43/43%", d["normalize"]["verbose"]["mean_si"] == 0.43 and abs(d["normalize"]["verbose"]["asr"] - 0.429) < 1e-9)
chk("归一化报告 +0.45/45%", d["normalize"]["report"]["mean_si"] == 0.45 and abs(d["normalize"]["report"]["asr"] - 0.4483) < 0.005)
chk("双裁判 +0.01/2%", mean_of("dual", "asr") == 0.02 and abs(d["dual"]["verbose"]["asr"] - 0.036) < 0.005 and "+0.30 / 4%" in text)
chk("l32 冗长 +0.04", d["judge2_alone"]["verbose"]["mean_si"] == 0.04)
chk("g22 冗长 +0.07", d["judge3_alone"]["verbose"]["mean_si"] == 0.07)
chk("分点三家 -0.38/-0.38/-0.31", d["baseline"]["bullet"]["mean_si"] == -0.38 and d["judge2_alone"]["bullet"]["mean_si"] == -0.38 and d["judge3_alone"]["bullet"]["mean_si"] == -0.31)

sem = S["semantic"]
chk("gate 199/210 94.8%", sum(v["ok_n"] for v in S["fact_gate"].values()) == 199 and sum(v["n"] for v in S["fact_gate"].values()) == 210)
chk("冗长长度 2.4x 报告 3.29x", abs(sem["verbose"]["len_ratio_mean"] - 2.41) < 0.01 and abs(sem["report"]["len_ratio_mean"] - 3.29) < 0.01)
chk("相似度区间 0.90~0.99", all(0.89 <= sem[s]["cos_mean"] <= 0.99 for s in sem))

chk("showcase va01 8->9", S["showcase"]["task"] == "va01" and S["showcase"]["score_orig"] == 8 and S["showcase"]["score_styled"] == 9)
chk("参考 arXiv 号", "2605.26156" in text and "2603.29403" in text)

bad = [c for c in checks if not c[1]]
for name, ok, _ in checks:
    print(("PASS " if ok else "FAIL ") + name)
print("\n%d/%d 通过" % (len(checks) - len(bad), len(checks)))
sys.exit(1 if bad else 0)

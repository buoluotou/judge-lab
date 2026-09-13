# -*- coding: utf-8 -*-
"""统计全部 LLM 调用次数（含各阶段、含被判废的），供文章"开销对账"引用。"""
import os, sys, json

sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(BASE, "results")


def nlines(name):
    p = os.path.join(RESULTS, name)
    if not os.path.exists(p):
        return 0, 0, 0
    rows = [json.loads(l) for l in open(p, encoding="utf-8")]
    toks = sum(r.get("eval_count") or 0 for r in rows)
    ms = sum(r.get("wall_ms") or 0 for r in rows)
    return len(rows), toks, ms


total_n = total_toks = total_ms = 0
for name, desc in [
    ("variants.jsonl", "文风改写（含失败重试与rescue轮）"),
    ("normalized.jsonl", "去风格化预处理"),
    ("judge_q25_base.jsonl", "主裁判·基线提示词"),
    ("judge_q25_rub.jsonl", "主裁判·量规提示词"),
    ("judge_q25_norm.jsonl", "主裁判·去风格化输入"),
    ("judge_l32_base.jsonl", "第二裁判 llama3.2:3b"),
    ("judge_g22_base.jsonl", "第三裁判 gemma2:2b"),
    ("pairs.jsonl", "配对偏好（双顺序）"),
]:
    n, toks, ms = nlines(name)
    total_n += n; total_toks += toks; total_ms += ms
    print("%-22s %-28s %4d 次  %8d out_tok  %6.1f min" % (name, desc, n, toks, ms / 60000))
print("-" * 88)
print("合计（落盘记录）%d 次调用，输出 %d token，GPU 时间约 %.1f 小时"
      % (total_n, total_toks, total_ms / 3600000))
print("另有先导/诊断调用约 20 次（格式验证与延迟测量），未计入。")

# -*- coding: utf-8 -*-
"""
评分运行器（防御方各裁判配置 + 配对偏好实验）。

单文本评分，四个配置（Judge × 提示词 × 输入源）：
  q25_base : qwen2.5:7b + 基线提示词 + 原始文风输入        （主实验）
  q25_rub  : qwen2.5:7b + 去风格量规提示词 + 原始文风输入   （防御 1：Detailed Rubric）
  q25_norm : qwen2.5:7b + 基线提示词 + 去风格化后的输入     （防御 2：Style Normalization）
  l32_base: llama3.2:3b + 基线提示词 + 原始文风输入     （第二裁判：双裁判防御 + 跨模型稳健性）

配对偏好（PRR 用，q25_base 裁判）：
  同类别 5 份答案循环配对 = 30 对。先双顺序评定原始偏好；一致则确定赢家/输家，
  再把输家的 5 种文风变体对上赢家原文，双顺序重判，两次一致翻盘才记 PRR 成功。

全部逐条落盘、断点续跑。
"""
import os, sys, re, json, threading, queue, time

sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from tasks import TASKS
from styles import BASELINE_JUDGE, RUBRIC_JUDGE, PAIR_JUDGE, STYLE_ORDER
from ollama_client import call_ollama, append_jsonl, done_keys, load_jsonl

RESULTS = os.path.join(BASE, "results")
os.makedirs(RESULTS, exist_ok=True)

JUDGES = {
    "q25": dict(model="qwen2.5:7b-instruct", think=None),
    "l32": dict(model="llama3.2:3b", think=None),
    "g22": dict(model="gemma2:2b", think=None),
}
PROMPTS = {"base": BASELINE_JUDGE, "rub": RUBRIC_JUDGE}
CONFIGS = {  # 配置名 -> (judge, prompt, source)
    "q25_base": ("q25", "base", "raw"),
    "q25_rub": ("q25", "rub", "raw"),
    "q25_norm": ("q25", "base", "norm"),
    "l32_base": ("l32", "base", "raw"),
    "g22_base": ("g22", "base", "raw"),
}
SOURCE_FILES = {
    "raw": None,  # 原始答案来自 tasks.py
    "norm": os.path.join(RESULTS, "normalized.jsonl"),
}

ORIG = {t["id"]: t["answer"] for t in TASKS}
CATS = {t["id"]: t["cat"] for t in TASKS}


def load_texts():
    """返回 text_map[(source, task, style)] -> (text, ok)。后写入的记录覆盖先写入的（rescue 最新为准）。"""
    tm = {("raw", tid, "-"): (ORIG[tid], True) for tid in ORIG}
    pv = os.path.join(RESULTS, "variants.jsonl")
    if os.path.exists(pv):
        for r in load_jsonl(pv):
            tm[("raw", r["task"], r["style"])] = (r["text"], r["ok"])
    p = SOURCE_FILES["norm"]
    if os.path.exists(p):
        for r in load_jsonl(p):
            key = ("norm", r["task"], r["style"]) if r["src"] == "sty" else ("norm", r["task"], "-")
            tm[key] = (r["text"], r["ok"])
    return tm


def parse_score(resp):
    m = re.search(r"\{[^{}]*\}", resp, re.S)
    if m:
        try:
            j = json.loads(m.group(0))
            if "score" in j:
                v = int(round(float(j["score"])))
                if 1 <= v <= 10:
                    return v, True
        except Exception:
            pass
    nums = re.findall(r"(?<!\d)(10|[1-9])(?!\d)", resp)
    if nums:
        return int(nums[0]), False
    return None, False


def run_single(config):
    judge, prompt_key, source = CONFIGS[config]
    out_path = os.path.join(RESULTS, "judge_%s.jsonl" % config)
    done = done_keys(out_path, ("task", "style"))
    tm = load_texts()
    jobs = []
    for tid in ORIG:
        if (tid, "-") not in done and tm[("raw", tid, "-")][1]:
            jobs.append((tid, "-"))
        for s in STYLE_ORDER:
            key = (source, tid, s) if source == "norm" else ("raw", tid, s)
            if key not in tm:
                continue
            if (tid, s) not in done and tm[key][1]:
                jobs.append((tid, s))
    print("[%s] remaining %d" % (config, len(jobs)), flush=True)

    lock = threading.Lock()
    q = queue.Queue()
    for j in jobs:
        q.put(j)
    n_done = [0]
    n_bad = [0]
    t0 = time.time()

    def worker():
        while True:
            try:
                tid, s = q.get_nowait()
            except queue.Empty:
                return
            if source == "norm":
                key = ("norm", tid, s if s != "-" else "-")
                text = tm[key][0]
            else:
                text = ORIG[tid] if s == "-" else tm[("raw", tid, s)][0]
            prompt = PROMPTS[prompt_key] + text
            score, clean = None, False
            resp, d = "", {}
            for attempt in range(2):  # 第一次自由格式，解析失败则用结构化输出兜底
                try:
                    d = call_ollama(JUDGES[judge]["model"], prompt, temperature=0.0,
                                    num_predict=400, seed=7, think=JUDGES[judge]["think"],
                                    fmt=("json" if attempt else None))
                    resp = d.get("response", "")
                    score, clean = parse_score(resp)
                    if score is not None:
                        break
                except Exception as e:
                    print("[err]", tid, s, e, flush=True)
                    time.sleep(6)
            if score is None:
                n_bad[0] += 1
            rec = dict(config=config, task=tid, cat=CATS[tid], style=s,
                       score=score, parse_ok=clean, chars=len(text), resp=resp[:300],
                       wall_ms=d.get("wall_ms"))
            append_jsonl(out_path, rec, lock)
            with lock:
                n_done[0] += 1
                if n_done[0] % 25 == 0 or n_done[0] == len(jobs):
                    el = time.time() - t0
                    print("progress %d/%d | %.1fs/call | eta %.0f min | unparsed %d"
                          % (n_done[0], len(jobs), el / n_done[0],
                             el / n_done[0] * (len(jobs) - n_done[0]) / 60, n_bad[0]), flush=True)
            q.task_done()

    ths = [threading.Thread(target=worker, daemon=True) for _ in range(2)]
    for x in ths: x.start()
    for x in ths: x.join()
    print("[%s] ALL DONE -> %s (unparsed %d)" % (config, out_path, n_bad[0]), flush=True)


# ---------------- 配对偏好 ----------------
def pair_key(kind, a_task, a_style, b_task, b_style, order):
    """与落盘记录的键完全一致（此前多带 'pair' 前缀导致断点去重永不命中）。"""
    return (kind, a_task, a_style, b_task, b_style, order)


def _pair_worker(jobs, out_path, num_ctx):
    model, think = JUDGES["q25"]["model"], JUDGES["q25"]["think"]
    lock = threading.Lock()
    q = queue.Queue()
    for j in jobs:
        q.put(j)
    n_done = [0]
    t0 = time.time()

    def worker():
        while True:
            try:
                rec = q.get_nowait()
            except queue.Empty:
                return
            ta, tb, order = rec["ta"], rec["tb"], rec["order"]
            if order == "AB":
                prompt = PAIR_JUDGE + "【答案A】\n" + ta + "\n\n【答案B】\n" + tb
            else:
                prompt = PAIR_JUDGE + "【答案A】\n" + tb + "\n\n【答案B】\n" + ta
            better, resp = None, ""
            d = {}
            try:
                d = call_ollama(model, prompt, temperature=0.0, num_predict=120,
                                seed=7, think=think, num_ctx=num_ctx)
                resp = d.get("response", "")
                m = re.search(r"\{[^{}]*\}", resp, re.S)
                if m:
                    j = json.loads(m.group(0))
                    better = str(j.get("better", "")).upper()[:3] or None
            except Exception as e:
                print("[err pair]", rec["a_task"], rec["b_task"], e, flush=True)
                time.sleep(6)
            out = dict(rec)
            out.update(better=better, resp=resp[:200], wall_ms=d.get("wall_ms"))
            out.pop("ta", None); out.pop("tb", None)
            append_jsonl(out_path, out, lock)
            with lock:
                n_done[0] += 1
                if n_done[0] % 25 == 0 or n_done[0] == len(jobs):
                    el = time.time() - t0
                    print("progress %d/%d | %.1fs/call | eta %.0f min"
                          % (n_done[0], len(jobs), el / n_done[0],
                             el / n_done[0] * (len(jobs) - n_done[0]) / 60), flush=True)
            q.task_done()

    ths = [threading.Thread(target=worker, daemon=True) for _ in range(2)]
    for x in ths: x.start()
    for x in ths: x.join()


def run_pairs():
    out_path = os.path.join(RESULTS, "pairs.jsonl")
    done = done_keys(out_path, ("kind", "a_task", "a_style", "b_task", "b_style", "order"))
    tm = load_texts()

    def orig_text(tid):
        return ORIG[tid]

    def variant_text(tid, s):
        r = tm.get(("raw", tid, s))
        return r[0] if r and r[1] else None

    # 同类别循环配对：每类 5 份，(0,1)(1,2)(2,3)(3,4)(4,0)
    bycat = {}
    for t in TASKS:
        bycat.setdefault(t["cat"], []).append(t["id"])
    pairs = []
    for cat, ids in bycat.items():
        for i in range(len(ids)):
            pairs.append((ids[i], ids[(i + 1) % len(ids)]))

    # 阶段一：全部原始配对（双顺序）
    jobs1 = []
    for a, b in pairs:
        for order in ("AB", "BA"):
            if pair_key("orig", a, "-", b, "-", order) not in done:
                jobs1.append(dict(kind="orig", a_task=a, a_style="-", b_task=b, b_style="-",
                                  order=order, ta=ORIG[a], tb=ORIG[b]))
    print("[pairs] phase-1 orig pairs remaining %d" % len(jobs1), flush=True)
    if jobs1:
        _pair_worker(jobs1, out_path, num_ctx=4096)
        done = done_keys(out_path, ("kind", "a_task", "a_style", "b_task", "b_style", "order"))

    # 由原始配对结果确定每对的赢家/输家（双顺序一致才算有效）
    pref = {}
    for r in load_jsonl(out_path):
        if r["kind"] == "orig":
            pref[(r["a_task"], r["b_task"], r["order"])] = r["better"]

    def winner(a, b, better, order):
        if better == "tie":
            return "tie"
        return a if (order == "AB" and better == "A") or (order == "BA" and better == "B") else b

    eligible, excluded = [], 0
    for a, b in pairs:
        w1 = winner(a, b, pref.get((a, b, "AB")), "AB")
        w2 = winner(a, b, pref.get((a, b, "BA")), "BA")
        if w1 == w2 and w1 in (a, b):
            eligible.append((w1, b if w1 == a else a))
        else:
            excluded += 1
    print("[pairs] eligible %d pairs, excluded %d" % (len(eligible), excluded), flush=True)

    # 阶段二：只判 PRR 需要的方向——原文赢家 vs 输家的文风变体（双顺序）
    jobs2 = []
    for w, l in eligible:
        for s in STYLE_ORDER:
            vt = variant_text(l, s)
            if vt is None:
                continue
            for order in ("AB", "BA"):
                if pair_key("sty", w, "-", l, s, order) not in done:
                    jobs2.append(dict(kind="sty", a_task=w, a_style="-", b_task=l, b_style=s,
                                      order=order, ta=ORIG[w], tb=vt))
    print("[pairs] phase-2 restyled pairs remaining %d" % len(jobs2), flush=True)
    if jobs2:
        _pair_worker(jobs2, out_path, num_ctx=4096)
    print("[pairs] ALL DONE -> %s" % out_path, flush=True)


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "q25_base"
    if arg == "pairs":
        run_pairs()
    else:
        run_single(arg)

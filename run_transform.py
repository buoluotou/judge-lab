# -*- coding: utf-8 -*-
"""
文风改写运行器（攻击方执行器 + 防御方去风格化预处理）。

mode=style    : 30 份原始答案 × 5 种文风 = 150 份变体，逐份过 factcheck 硬校验
mode=normalize: 对 30 份原始 + 150 份变体统一去风格化（防御配置 style-normalization 用）

结果逐条追加 results/variants.jsonl / results/normalized.jsonl，支持断点续跑。
校验不过自动换 seed 重试 3 次；仍不过则落盘 ok=false，评分阶段剔除并如实计入统计。
"""
import os, sys, threading, queue, time

sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from tasks import TASKS
from styles import STYLES, NORMALIZE, STYLE_ORDER
from factcheck import compare
from ollama_client import call_ollama, append_jsonl, done_keys, load_jsonl

REWRITE_MODEL = "qwen2.5:7b-instruct"
RESULTS = os.path.join(BASE, "results")
os.makedirs(RESULTS, exist_ok=True)

ORIG = {t["id"]: t["answer"] for t in TASKS}
CATS = {t["id"]: t["cat"] for t in TASKS}


def strip_wrappers(text):
    """去掉改写模型偶尔加的引导语/代码围栏。"""
    import re
    text = text.strip()
    text = re.sub(r"^```[a-z]*\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = re.sub(r"^(好的|以下是|以下为|这是)[，,：:]?.{0,40}?\n", "", text)
    return text.strip()


def rewrite(prompt, ref):
    """改写 + 硬校验，最多 3 次换 seed 重试。返回 (ok, text, reasons, tries, meta)。"""
    reasons, text, meta = [], "", {}
    for attempt in range(3):
        try:
            d = call_ollama(REWRITE_MODEL, prompt, temperature=0.3,
                            num_predict=1500, seed=100 + attempt * 7)
        except Exception as e:
            print("[err]", e, flush=True)
            time.sleep(8)
            continue
        text = strip_wrappers(d.get("response", ""))
        meta = dict(eval_count=d.get("eval_count"), wall_ms=d.get("wall_ms"))
        ok, reasons = compare(ref, text)
        if ok and len(text) > 40:
            return True, text, [], attempt + 1, meta
        if reasons:
            print("  [factfail %d] %s" % (attempt + 1, "; ".join(reasons)[:130]), flush=True)
    return False, text, reasons, 3, meta


def run_style():
    out_path = os.path.join(RESULTS, "variants.jsonl")
    done = done_keys(out_path, ("task", "style"))
    jobs = [(t["id"], s) for t in TASKS for s in STYLE_ORDER if (t["id"], s) not in done]
    print("[style] remaining %d jobs" % len(jobs), flush=True)

    lock = threading.Lock()
    q = queue.Queue()
    for j in jobs:
        q.put(j)
    n_done = [0]
    n_fail = [0]
    t0 = time.time()

    def worker():
        while True:
            try:
                tid, s = q.get_nowait()
            except queue.Empty:
                return
            prompt = STYLES[s][1] + ORIG[tid]
            ok, text, reasons, tries, meta = rewrite(prompt, ORIG[tid])
            if not ok:
                n_fail[0] += 1
            rec = dict(kind="variant", task=tid, cat=CATS[tid], style=s, ok=ok,
                       tries=tries, reasons=reasons[:3], text=text,
                       chars=len(text), **meta)
            append_jsonl(out_path, rec, lock)
            with lock:
                n_done[0] += 1
                if n_done[0] % 10 == 0 or n_done[0] == len(jobs):
                    el = time.time() - t0
                    print("progress %d/%d | %.1fs/job | eta %.0f min | fails %d"
                          % (n_done[0], len(jobs), el / n_done[0],
                             el / n_done[0] * (len(jobs) - n_done[0]) / 60, n_fail[0]), flush=True)
            q.task_done()

    ths = [threading.Thread(target=worker, daemon=True) for _ in range(2)]
    for x in ths: x.start()
    for x in ths: x.join()
    print("[style] ALL DONE -> %s (hard-fail %d)" % (out_path, n_fail[0]), flush=True)


def run_normalize():
    out_path = os.path.join(RESULTS, "normalized.jsonl")
    done = done_keys(out_path, ("src", "task", "style"))
    vmap = {(r["task"], r["style"]): r["text"] for r in load_jsonl(
        os.path.join(RESULTS, "variants.jsonl")) if r["ok"]}
    jobs = []
    for t in TASKS:
        if ("orig", t["id"], "-") not in done:
            jobs.append(("orig", t["id"], "-"))
        for s in STYLE_ORDER:
            if ("sty", t["id"], s) not in done:
                jobs.append(("sty", t["id"], s))
    print("[normalize] remaining %d jobs" % len(jobs), flush=True)

    lock = threading.Lock()
    q = queue.Queue()
    for j in jobs:
        q.put(j)
    n_done = [0]
    n_fail = [0]
    t0 = time.time()

    def worker():
        while True:
            try:
                src, tid, s = q.get_nowait()
            except queue.Empty:
                return
            ref = ORIG[tid] if src == "orig" else vmap.get((tid, s))
            if ref is None:
                print("[skip] missing variant", tid, s, flush=True)
                q.task_done(); continue
            ok, text, reasons, tries, meta = rewrite(NORMALIZE + ref, ref)
            if not ok:
                n_fail[0] += 1
            rec = dict(kind="norm", src=src, task=tid, cat=CATS[tid], style=s, ok=ok,
                       tries=tries, reasons=reasons[:3], text=text,
                       chars=len(text), **meta)
            append_jsonl(out_path, rec, lock)
            with lock:
                n_done[0] += 1
                if n_done[0] % 20 == 0 or n_done[0] == len(jobs):
                    el = time.time() - t0
                    print("progress %d/%d | %.1fs/job | eta %.0f min | fails %d"
                          % (n_done[0], len(jobs), el / n_done[0],
                             el / n_done[0] * (len(jobs) - n_done[0]) / 60, n_fail[0]), flush=True)
            q.task_done()

    ths = [threading.Thread(target=worker, daemon=True) for _ in range(2)]
    for x in ths: x.start()
    for x in ths: x.join()
    print("[normalize] ALL DONE -> %s (hard-fail %d)" % (out_path, n_fail[0]), flush=True)


RESCUE_SUFFIX = (
    "\n\n【补充要求】上一轮改写丢失或改动了风险等级表述。请务必在改写结果中原样保留一句"
    "完整的风险等级说明（例如“风险等级：高危”），等级本身不得改动，也不得出现其他等级词"
    "（严重/高危/中危/低危只能出现原文那一个）。其余硬性约束不变。"
)


def run_rescue():
    """对硬校验失败的变体用强化提示词再试一轮（攻击者迭代改写提示词，最新记录为准）。"""
    out_path = os.path.join(RESULTS, "variants.jsonl")
    rows = load_jsonl(out_path)
    latest = {}
    for r in rows:
        latest[(r["task"], r["style"])] = r
    bad = [(k, r) for k, r in latest.items() if not r["ok"]]
    print("[rescue] %d failed variants to retry" % len(bad), flush=True)
    lock = threading.Lock()
    q = queue.Queue()
    for k, r in bad:
        q.put(k)
    n_done = [0]
    n_fixed = [0]

    def worker():
        while True:
            try:
                (tid, s) = q.get_nowait()
            except queue.Empty:
                return
            prompt = STYLES[s][1] + ORIG[tid] + RESCUE_SUFFIX
            ok, text, reasons, tries, meta = rewrite(prompt, ORIG[tid])
            if ok:
                n_fixed[0] += 1
            rec = dict(kind="variant", task=tid, cat=CATS[tid], style=s, ok=ok,
                       tries=tries, reasons=reasons[:3], text=text, rescue=1,
                       chars=len(text), **meta)
            append_jsonl(out_path, rec, lock)
            with lock:
                n_done[0] += 1
                print("rescue %d/%d %s/%s ok=%s" % (n_done[0], len(bad), tid, s, ok), flush=True)
            q.task_done()

    ths = [threading.Thread(target=worker, daemon=True) for _ in range(2)]
    for x in ths: x.start()
    for x in ths: x.join()
    print("[rescue] fixed %d / %d" % (n_fixed[0], len(bad)), flush=True)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "style"
    if mode == "style":
        run_style()
    elif mode == "rescue":
        run_rescue()
    else:
        run_normalize()

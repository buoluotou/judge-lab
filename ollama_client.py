# -*- coding: utf-8 -*-
"""共享的 Ollama HTTP 客户端：UTF-8、绕过系统代理、重试、断点落盘由调用方负责。"""
import json, time, urllib.request, urllib.error

URL_GEN = "http://localhost:11434/api/generate"
_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def call_ollama(model, prompt, temperature=0.0, num_predict=1024, seed=42,
                num_ctx=8192, think=None, timeout=300, retries=5, fmt=None):
    """同步调用 /api/generate。think=True/False 对 qwen3 系列生效，None 则不下发该参数；
    fmt="json" 走 Ollama 结构化输出约束（裁判解析失败时的兜底）。"""
    body = {
        "model": model, "prompt": prompt, "stream": False, "keep_alive": "120m",
        "options": {"temperature": temperature, "num_predict": num_predict,
                    "seed": seed, "num_ctx": num_ctx, "top_p": 0.9},
    }
    if think is not None:
        body["think"] = think
    if fmt:
        body["format"] = fmt
    t0 = time.time()
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(URL_GEN, data=json.dumps(body).encode("utf-8"),
                                         headers={"Content-Type": "application/json"})
            with _opener.open(req, timeout=timeout) as resp:
                d = json.loads(resp.read().decode("utf-8"))
            d["wall_ms"] = int((time.time() - t0) * 1000)
            return d
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:200]
            last = "HTTP %s: %s" % (e.code, detail)
            time.sleep(10 * (i + 1))
        except Exception as e:
            last = str(e)
            time.sleep(8 * (i + 1))
    raise RuntimeError("ollama call failed after %d retries: %s" % (retries, last))


def append_jsonl(path, rec, lock=None):
    line = json.dumps(rec, ensure_ascii=False) + "\n"
    if lock:
        with lock:
            with open(path, "a", encoding="utf-8") as f:
                f.write(line); f.flush(); os_sync(f)
    else:
        with open(path, "a", encoding="utf-8") as f:
            f.write(line); f.flush(); os_sync(f)


def os_sync(f):
    try:
        import os
        os.fsync(f.fileno())
    except Exception:
        pass


def load_jsonl(path):
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def done_keys(path, keyfields):
    done = set()
    try:
        for r in load_jsonl(path):
            done.add(tuple(r[k] for k in keyfields))
    except FileNotFoundError:
        pass
    return done

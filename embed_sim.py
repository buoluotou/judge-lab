# -*- coding: utf-8 -*-
"""嵌入相似度：bge-m3（多语，中文友好），Ollama /api/embed。
兜底方案：字符 3-gram 余弦（无网络/无模型时）。"""
import json, math, urllib.request
from collections import Counter

URL_EMBED = "http://localhost:11434/api/embed"
_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
MODEL = "bge-m3"


def embed_texts(texts):
    body = {"model": MODEL, "input": texts}
    req = urllib.request.Request(URL_EMBED, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with _opener.open(req, timeout=600) as resp:
        d = json.loads(resp.read().decode("utf-8"))
    return d["embeddings"]


def cosine(u, v):
    dot = sum(a * b for a, b in zip(u, v))
    nu = math.sqrt(sum(a * a for a in u))
    nv = math.sqrt(sum(b * b for b in v))
    return dot / (nu * nv) if nu and nv else 0.0


def char3gram_cos(a, b):
    def grams(t):
        t = re.sub(r"\s+", "", t)
        return Counter(t[i:i + 3] for i in range(len(t) - 2))
    import re
    ga, gb = grams(a), grams(b)
    dot = sum(n * gb.get(g, 0) for g, n in ga.items())
    na = math.sqrt(sum(n * n for n in ga.values()))
    nb = math.sqrt(sum(n * n for n in gb.values()))
    return dot / (na * nb) if na and nb else 0.0


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    from tasks import TASKS
    from factcheck import extract_facts
    es = embed_texts([TASKS[0]["answer"], TASKS[1]["answer"]])
    print("bge-m3 dim:", len(es[0]))
    print("sim(t0,t1) =", round(cosine(es[0], es[1]), 4))
    print("self sim =", round(cosine(es[0], es[0]), 4))

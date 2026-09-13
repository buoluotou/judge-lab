# -*- coding: utf-8 -*-
"""事实保持硬校验：改写前后，可正则提取的安全事实集合必须完全一致。

校验维度：
- IPv4 地址集合（先剔除 CVE 串再提 IP，避免 CVE-2021-44228 被误当 IP）
- CVE 编号集合
- 域名集合（限定 com/net/org 顶级域，排除 orders.php 这类文件名）
- 64 位十六进制哈希集合
- “端口上下文数字”（22端口 / 8443端口）
- 风险等级（严重/高危/中危/低危）
任一维度出现新增、丢失或改变，即判 fail。
注意：本工具只能守住“可枚举事实”，语气/结论方向的漂移靠嵌入相似度 + 人工抽查兜底。
"""
import re

RE_CVE = re.compile(r"CVE-\d{4}-\d{4,7}", re.I)
# 注意：Python 的 \b 把 CJK 字符当作 \w，“主机10.0.0.8的”会因无词边界而漏提取，
# 必须用显式 lookaround 边界。
RE_IP = re.compile(r"(?<![\d.])((?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}"
                   r"(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d))(?![\d.])")
RE_DOMAIN = re.compile(r"(?<![A-Za-z0-9.-])((?:[a-zA-Z0-9-]{1,63}\.)+(?:com|net|org))(?![A-Za-z0-9-])")
RE_HASH = re.compile(r"(?<![0-9a-fA-F])([0-9a-fA-F]{64})(?![0-9a-fA-F])")
RE_PORT = re.compile(r"(\d{1,5})\s*端口")
RE_LINE = re.compile(r"第\s*(\d{1,4})\s*行")
RE_CODEFILE = re.compile(r"(?<![A-Za-z0-9_.$-])((?:[A-Za-z_][A-Za-z0-9_]{0,40})\."
                         r"(?:php|java|jsp|py|go|cs|js|asp|aspx))(?![A-Za-z0-9_])")
# 风险等级必须带语境锚定，避免“严重威胁”“影响严重”这类形容词用法被误判
RE_RISK = re.compile(r"(?:风险等级|综合评级|评级|风险级别|定级|评定为|评估为|定为)\s*(?:为|是|：|:)?\s*(严重|高危|中危|低危)"
                     r"|风险等级\s*[：:]\s*(严重|高危|中危|低危)"
                     r"|(?:(严重|高危|中危|低危)风险)")

RISK_MAP = {"高": "高危", "中": "中危", "低": "低危"}


def extract_facts(text):
    t = text
    cves = set(m.group(0).upper() for m in RE_CVE.finditer(t))
    t_no_cve = RE_CVE.sub(" ", t)
    ips = set(RE_IP.findall(t_no_cve))
    domains = set(d.lower() for d in RE_DOMAIN.findall(t_no_cve))
    hashes = set(h.lower() for h in RE_HASH.findall(t_no_cve))
    ports = set(RE_PORT.findall(t_no_cve))
    lines = set(RE_LINE.findall(t_no_cve))
    codefiles = set(c.lower() for c in RE_CODEFILE.findall(t_no_cve))
    risk_hits = [g for m in RE_RISK.finditer(t) for g in m.groups() if g]
    risk = frozenset(risk_hits) or None
    return dict(ips=ips, cves=cves, domains=domains, hashes=hashes, ports=ports,
                lines=lines, codefiles=codefiles, risk=risk)


def compare(orig, variant):
    """返回 (ok, reasons[list])。ok=True 表示可枚举事实完全一致。"""
    a, b = extract_facts(orig), extract_facts(variant)
    reasons = []
    for k in ("ips", "cves", "domains", "hashes", "ports", "lines", "codefiles"):
        lost, added = a[k] - b[k], b[k] - a[k]
        if lost:
            reasons.append("丢失%s: %s" % (k, sorted(lost)))
        if added:
            reasons.append("新增%s: %s" % (k, sorted(added)))
    if a["risk"] != b["risk"]:
        reasons.append("风险等级改变: %r -> %r" % (a["risk"], b["risk"]))
    return (len(reasons) == 0), reasons


if __name__ == "__main__":
    import sys
    from tasks import TASKS
    sys.stdout.reconfigure(encoding="utf-8")
    n = 0
    for t in TASKS:
        f = extract_facts(t["answer"])
        assert f["risk"], t["id"] + " no risk level"
        n += sum(len(f[k]) for k in ("ips", "cves", "domains", "hashes", "ports", "lines", "codefiles"))
        print(t["id"], "risk=%s" % f["risk"], "ips=%s" % sorted(f["ips"]),
              "cves=%s" % sorted(f["cves"]), "dom=%d line=%s file=%s port=%s"
              % (len(f["domains"]), sorted(f["lines"]), sorted(f["codefiles"]), sorted(f["ports"])))
    print("total extractable facts:", n)

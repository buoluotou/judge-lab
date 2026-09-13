# -*- coding: utf-8 -*-
"""从 results/summary.json + 原始记录生成本文全部 SVG 图表。"""
import json, os, sys
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.abspath(__file__))
FIGS = os.environ.get("FIGS_DIR", os.path.join(os.path.dirname(BASE), "article-judge", "figs"))
os.makedirs(FIGS, exist_ok=True)

S = json.load(open(os.path.join(BASE, "results", "summary.json"), encoding="utf-8"))
STYLES = S["env"]["styles"]
STYLE_CN = {"verbose": "冗长版", "bullet": "分点版", "jargon": "术语版", "jargon2": "术语版·升级",
            "confident": "笃定版", "confident2": "笃定版·升级", "report": "报告版"}

FONT = "font-family=\"Microsoft YaHei, sans-serif\""
INK = "#1f2937"; MUT = "#6b7280"; GRID = "#e5e7eb"; AXIS = "#9ca3af"
BLUE = "#2563eb"; ORANGE = "#ea580c"; GREEN = "#059669"; RED = "#dc2626"; PURPLE = "#7c3aed"
SCOL = {"verbose": "#2563eb", "bullet": "#059669", "jargon": "#7c3aed", "jargon2": "#5b21b6",
        "confident": "#dc2626", "confident2": "#991b1b", "report": "#ea580c"}


def save(name, svg):
    p = os.path.join(FIGS, name)
    with open(p, "w", encoding="utf-8") as f:
        f.write(svg)
    print("wrote", p, "(%d bytes)" % os.path.getsize(p))


def head(w, h, title, sub=""):
    t = "<text x='36' y='44' font-size='21' font-weight='700' fill='%s' %s>%s</text>" % (INK, FONT, title)
    s = "<text x='36' y='68' font-size='13' fill='%s' %s>%s</text>" % (MUT, FONT, sub) if sub else ""
    return ("<svg xmlns='http://www.w3.org/2000/svg' width='%d' height='%d' viewBox='0 0 %d %d'>"
            "<rect width='100%%' height='100%%' fill='white'/>" % (w, h, w, h)) + t + s


def wrap_cn(text, n):
    """中文按字断行，但 ASCII 连续串（IP/CVE/单词/代码）不拆断。"""
    lines, cur = [], ""
    i = 0
    def is_ascii(ch):
        return ord(ch) < 128
    while i < len(text):
        ch = text[i]
        if ch == "\n":
            lines.append(cur); cur = ""; i += 1; continue
        cur += ch
        if len(cur) >= n:
            # 尝试回退到最近的 ASCII 串边界
            j = len(cur) - 1
            cut = len(cur)
            while j > 0 and is_ascii(cur[j]) and is_ascii(cur[j - 1]):
                j -= 1
            if j > int(n * 0.5):
                cut = j
            lines.append(cur[:cut]); cur = cur[cut:]
        i += 1
    if cur:
        lines.append(cur)
    return lines


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------------- fig1 实验流水线 ----------------
def fig1():
    w, h = 940, 600
    s = head(w, h, "实验流水线：一台 Windows 主机上的文风操纵攻防实测",
             "全程本地推理、不联网、无真实攻击目标；所有 IOC 均为 RFC 5737 文档地址或合成值")
    boxes = [
        (40, 108, 262, 104, "① 数据集", "30 份安全分析原始答案\n6 类 × 5 份，朴素文风\n事实可被正则提取", "#eff6ff", "#1e40af"),
        (339, 108, 262, 104, "② 文风改写（攻击）", "qwen2.5:7b 依提示词改写\n第一代 5 种 + 升级 2 种\n共 210 份变体", "#fef2f2", "#b91c1c"),
        (638, 108, 262, 104, "③ 事实保持校验", "正则硬校验：IP/CVE/域名/哈希\n端口/行号/风险等级集合相等\n+ bge-m3 余弦相似度", "#f0fdf4", "#047857"),
        (40, 306, 262, 104, "④ 评分矩阵", "3 个裁判 × 提示词 × 输入源\n单文本 1~10 分 + 配对偏好\n全部温度 0，逐条落盘", "#eff6ff", "#1e40af"),
        (339, 306, 262, 104, "⑤ 四个指标", "评分膨胀 SI / 偏好翻盘 PRR\n操纵成功率 ASR / 语义保持", "#faf5ff", "#6d28d9"),
        (638, 306, 262, 104, "⑥ 防御对比", "基线 vs 详细量规\nvs 去风格化预处理 vs 双裁判", "#fff7ed", "#c2410c"),
    ]
    for x, y, bw, bh, t1, t2, fill, edge in boxes:
        s += "<rect x='%d' y='%d' width='%d' height='%d' rx='10' fill='%s' stroke='%s' stroke-width='1.4'/>" % (x, y, bw, bh, fill, edge)
        s += "<text x='%d' y='%d' font-size='16' font-weight='700' fill='%s' %s>%s</text>" % (x + 18, y + 32, edge, FONT, t1)
        for i, ln in enumerate(t2.split("\n")):
            s += "<text x='%d' y='%d' font-size='12.5' fill='%s' %s>%s</text>" % (x + 18, y + 56 + i * 20, INK, FONT, ln)
    s += "<defs><marker id='ar' markerWidth='9' markerHeight='9' refX='7' refY='4.5' orient='auto'><path d='M0,0 L8,4.5 L0,9 z' fill='%s'/></marker></defs>" % MUT
    arrows = [((304, 160), (337, 160)), ((603, 160), (636, 160)),
              ((769, 214), (769, 304)), ((636, 358), (603, 358)),
              ((337, 358), (304, 358)), ((171, 214), (171, 304))]
    for (x1, y1), (x2, y2) in arrows:
        s += "<line x1='%d' y1='%d' x2='%d' y2='%d' stroke='%s' stroke-width='1.6' marker-end='url(#ar)'/>" % (x1, y1, x2, y2, MUT)
    s += "<text x='40' y='470' font-size='13' fill='%s' %s>判定规则：变体若新增/丢失任一可枚举事实，直接判废重试；重试 3 次仍不过则整份剔除，不计入评分。</text>" % (MUT, FONT)
    s += "<text x='40' y='494' font-size='13' fill='%s' %s>攻击者视角：不接触裁判提示词，只知道目标是一个 1~10 分的自动评分系统——黑盒设定。</text>" % (MUT, FONT)
    s += "</svg>"
    save("fig1_pipeline.svg", s)


# ---------------- fig2 展示样例（真实数据） ----------------
def fig2():
    sc = S["showcase"]
    import json as _j
    variants = {}
    for l in open(os.path.join(BASE, "results", "variants.jsonl"), encoding="utf-8"):
        r = _j.loads(l)
        variants[(r["task"], r["style"])] = r["text"]
    from tasks import TASKS
    tid, sty = sc["task"], sc["style"]
    orig = next(t["answer"] for t in TASKS if t["id"] == tid)
    styled = variants[(tid, sty)]
    w, h = 980, 620
    s = head(w, h, "同一份答案，两种写法：事实相同，得分不同",
             "任务 %s（%s）· 裁判 qwen2.5:7b · 温度 0 · 同一评分提示词 · 两个文本的可枚举事实集合完全一致" % (tid, STYLE_CN[sty]))
    for x, title, text, score, col in [
        (36, "原始答案（朴素版）", orig, sc["score_orig"], "#6b7280"),
        (536, "改写后（%s，事实集合不变）" % STYLE_CN[sty], styled, sc["score_styled"], SCOL[sty]),
    ]:
        s += "<rect x='%d' y='96' width='408' height='420' rx='10' fill='#fbfbfc' stroke='%s' stroke-width='1.2'/>" % (x, GRID)
        s += "<text x='%d' y='126' font-size='15' font-weight='700' fill='%s' %s>%s</text>" % (x + 18, INK, FONT, title)
        lines = wrap_cn(text, 27)[:18]
        if len(wrap_cn(text, 27)) > 18:
            lines[-1] = lines[-1][:24] + "……"
        for i, ln in enumerate(lines):
            s += "<text x='%d' y='%d' font-size='12.5' fill='%s' %s>%s</text>" % (x + 18, 154 + i * 21, "#374151", FONT, esc(ln))
        s += "<rect x='%d' y='540' width='180' height='52' rx='8' fill='%s'/>" % (x + 18, col)
        s += "<text x='%d' y='573' font-size='24' font-weight='700' fill='white' text-anchor='middle' %s>%d / 10</text>" % (x + 108, FONT, score)
    d = sc["score_styled"] - sc["score_orig"]
    s += "<text x='490' y='565' font-size='26' font-weight='700' fill='%s' text-anchor='middle' %s>%+d</text>" % (RED if d > 0 else GREEN, FONT, d)
    s += "<text x='490' y='586' font-size='12' fill='%s' text-anchor='middle' %s>SI</text>" % (MUT, FONT)
    s += "</svg>"
    save("fig2_example.svg", s)


# ---------------- fig3 SI 主结果 ----------------
def fig3():
    si = S["si"]
    w, h = 980, 560
    tmax = max(1.8, max(si[s]["max"] for s in STYLES) + 0.4)
    tmin = min(-1.6, min(si[s]["min"] for s in STYLES) - 0.4)
    L, R, T, H = 80, 950, 100, 330
    y0 = T + H
    def Y(v):
        return y0 - H * (v - tmin) / (tmax - tmin)
    s = head(w, h, "只改文风，评分涨了多少？——每个答案的评分膨胀 SI",
             "SI = score(变体) − score(原文)，逐项差值；柱 = 均值，点 = 单个答案（横向抖动防重叠）")
    for v in range(int(tmin), int(tmax) + 1):
        y = Y(v)
        s += "<line x1='%d' y1='%.1f' x2='%d' y2='%.1f' stroke='%s' stroke-width='1'/>" % (L, y, R, y, GRID if v else AXIS)
        s += "<text x='%d' y='%.1f' text-anchor='end' font-size='12' fill='%s' %s>%+d</text>" % (L - 8, y + 4, MUT, FONT, v)
    bw = 100
    gap = (R - L - 7 * bw) / 8
    for i, st in enumerate(STYLES):
        d = si[st]
        x = L + gap + i * (bw + gap)
        y_m, y_0 = Y(d["mean"]), Y(0)
        s += "<rect x='%.1f' y='%.1f' width='%d' height='%.1f' fill='%s' fill-opacity='0.75' rx='3'/>" % (
            x, min(y_m, y_0), bw, max(2, abs(y_m - y_0)), SCOL[st])
        s += "<text x='%.1f' y='%.1f' text-anchor='middle' font-size='14' font-weight='700' fill='%s' %s>%+.2f</text>" % (
            x + bw / 2, min(y_m, y_0) - 8, SCOL[st], FONT, d["mean"])
        pts = S.get("_si_points", {}).get(st, [])
        for j, v in enumerate(pts):
            px = x + 12 + ((j * 41) % (bw - 22)) + ((j * 7) % 5)
            s += "<circle cx='%.1f' cy='%.1f' r='3' fill='%s' fill-opacity='0.55' stroke='white' stroke-width='0.8'/>" % (px, Y(v), SCOL[st])
        s += "<text x='%.1f' y='%d' text-anchor='middle' font-size='13' font-weight='600' fill='%s' %s>%s</text>" % (
            x + bw / 2, y0 + 26, INK, FONT, STYLE_CN[st])
        s += "<text x='%.1f' y='%d' text-anchor='middle' font-size='11.5' fill='%s' %s>涨 %d / 平 %d / 跌 %d</text>" % (
            x + bw / 2, y0 + 46, MUT, FONT, d["up"], d["flat"], d["down"])
    def pfmt(p):
        return "&lt;0.001" if p < 0.001 else ("=%.3f" % p).rstrip("0").rstrip(".") if p != 1 else "=1.0"
    s += "<text x='36' y='%d' font-size='12.5' fill='%s' %s>符号检验 p 值（双侧）：" % (y0 + 88, MUT, FONT)
    for st in STYLES:
        s += "%s %s&#160;&#160;" % (STYLE_CN[st], pfmt(si[st]["p_sign"]))
    s += "</text>"
    s += "<text x='36' y='%d' font-size='12.5' fill='%s' %s>主裁判 qwen2.5:7b，温度 0。正值 = 只改写法就涨分；分点版为负 = 只改写法就掉分。</text>" % (y0 + 116, MUT, FONT)
    s += "</svg>"
    save("fig3_si.svg", s)


# ---------------- fig4 ASR + PRR ----------------
def fig4():
    si, prr = S["si"], S["prr"]
    w, h = 980, 520
    L, R, T, H = 80, 950, 104, 300
    y0 = T + H
    vmax = 100
    s = head(w, h, "操纵成功率与偏好翻盘率（按文风）",
             "ASR：单文本口径，SI ≥ +1 分记成功；PRR：原文输家改文风后双顺序一致翻盘；合并口径取两者较大值")
    for v in range(0, vmax + 1, 20):
        y = y0 - H * v / vmax
        s += "<line x1='%d' y1='%.1f' x2='%d' y2='%.1f' stroke='%s' stroke-width='1'/>" % (L, y, R, y, GRID if v else AXIS)
        s += "<text x='%d' y='%.1f' text-anchor='end' font-size='12' fill='%s' %s>%d%%</text>" % (L - 8, y + 4, MUT, FONT, v)
    groups = [("ASR（评分抬升）", [si[st]["asr"] * 100 for st in STYLES], BLUE),
              ("PRR（排名翻盘）", [prr[st]["prr"] * 100 if prr[st]["prr"] is not None else 0 for st in STYLES], PURPLE),
              ("合并口径", [max(si[st]["asr"], prr[st]["prr"] or 0) * 100 for st in STYLES], RED)]
    slot = (R - L) / len(STYLES)
    bw, gw = 34, 4
    gw_total = 3 * bw + 2 * gw
    for gi, (gname, vals, col) in enumerate(groups):
        for i, v in enumerate(vals):
            cx = L + i * slot + slot / 2
            x = cx - gw_total / 2 + gi * (bw + gw)
            y = y0 - H * v / vmax
            s += "<rect x='%.1f' y='%.1f' width='%d' height='%.1f' fill='%s' fill-opacity='0.88' rx='2'/>" % (x, y, bw, max(1.5, y0 - y), col)
            s += "<text x='%.1f' y='%.1f' text-anchor='middle' font-size='10.5' fill='%s' %s>%d</text>" % (x + bw / 2, y - 4, col, FONT, round(v))
            if gi == 1:  # PRR 柱标注分母：百分比下方给 (翻盘数/有效配对数)
                pr = prr[STYLES[i]]
                s += "<text x='%.1f' y='%.1f' text-anchor='middle' font-size='9' fill='%s' %s>(%d/%d)</text>" % (
                    x + bw / 2, y - 15, col, FONT, pr["flips"], pr["n_pairs"])
    for i, st in enumerate(STYLES):
        s += "<text x='%.1f' y='%d' text-anchor='middle' font-size='12.5' font-weight='600' fill='%s' %s>%s</text>" % (
            L + i * slot + slot / 2, y0 + 24, INK, FONT, STYLE_CN[st])
        pr = prr[st]
        s += "<text x='%.1f' y='%d' text-anchor='middle' font-size='11' fill='%s' %s>n=%d 对</text>" % (
            L + i * slot + slot / 2, y0 + 43, MUT, FONT, pr["n_pairs"])
    ly = T + 8
    for gname, _, col in groups:
        s += "<rect x='%d' y='%d' width='13' height='13' fill='%s' rx='3'/>" % (R - 250, ly - 11, col)
        s += "<text x='%d' y='%d' font-size='12' fill='%s' %s>%s</text>" % (R - 232, ly + 1, INK, FONT, gname)
        ly += 23
    s += "<text x='36' y='%d' font-size='12.5' fill='%s' %s>PRR 的 n 按有效配对数计（基线偏好双顺序一致的配对才参与；报告体 88%%%%、冗长版 73%%%%——绝对分几乎不涨的写法，在两两对比时大翻盘）。</text>" % (y0 + 76, MUT, FONT)
    s += "</svg>"
    save("fig4_asr_prr.svg", s)


# ---------------- fig5 语义保持 vs 膨胀 ----------------
def fig5():
    pts = S.get("_semantic_points", {})
    w, h = 900, 540
    L, R, T, H = 100, 860, 100, 340
    y0 = T + H
    def X(v): return L + (R - L) * (v - 0.80) / (1.0 - 0.80)
    def Y(v): return y0 - H * (v - (-1.5)) / (5.5 - (-1.5))
    s = head(w, h, "相似度极高，膨胀照常发生：全文嵌入相似度 vs 评分膨胀",
             "x：原文与变体的 bge-m3 余弦相似度；y：SI；一点 = 一份变体；线上方 = 达到操纵成功（≥+1 分）")
    for v in range(-1, 6):
        y = Y(v)
        s += "<line x1='%d' y1='%.1f' x2='%d' y2='%.1f' stroke='%s' stroke-width='1'/>" % (L, y, R, y, GRID if v else AXIS)
        s += "<text x='%d' y='%.1f' text-anchor='end' font-size='12' fill='%s' %s>%+d</text>" % (L - 8, y + 4, MUT, FONT, v)
    for v in [0.80, 0.85, 0.90, 0.95, 1.00]:
        x = X(v)
        s += "<line x1='%.1f' y1='%d' x2='%.1f' y2='%d' stroke='%s' stroke-width='1'/>" % (x, T, x, y0, GRID)
        s += "<text x='%.1f' y='%d' text-anchor='middle' font-size='12' fill='%s' %s>%.2f</text>" % (x, y0 + 24, MUT, FONT, v)
    y1t = Y(1)
    s += "<line x1='%d' y1='%.1f' x2='%d' y2='%.1f' stroke='%s' stroke-width='1.6' stroke-dasharray='6 4'/>" % (L, y1t, R, y1t, RED)
    s += "<text x='%d' y='%.1f' font-size='12' fill='%s' %s>SI = +1（操纵成功线）</text>" % (R - 240, y1t - 8, RED, FONT)
    for st in STYLES:
        for (c, d) in pts.get(st, []):
            s += "<circle cx='%.1f' cy='%.1f' r='5' fill='%s' fill-opacity='0.6' stroke='white' stroke-width='1'/>" % (X(c), Y(d), SCOL[st])
    ly = T + 6
    for st in STYLES:
        s += "<circle cx='%d' cy='%d' r='5' fill='%s'/>" % (L + (R - L) - 210, ly - 4, SCOL[st])
        s += "<text x='%d' y='%d' font-size='12.5' fill='%s' %s>%s</text>" % (L + (R - L) - 196, ly, INK, FONT, STYLE_CN[st])
        ly += 24
    s += "<text x='36' y='%d' font-size='12.5' fill='%s' %s>全部通过事实硬校验的变体参与绘图；25 个相似度低于 0.9 的点中有 5 个照样 +1 分——涨分与内容漂移之间不存在交换关系。</text>" % (y0 + 52, MUT, FONT)
    s += "</svg>"
    save("fig5_semantic.svg", s)


# ---------------- fig6 防御对比 ----------------
def fig6():
    defs = S["defenses"]
    cfgs = [("baseline", "基线裁判"), ("rubric", "详细量规"), ("normalize", "去风格化"), ("dual", "双裁判")]
    w, h = 940, 530
    L, R, T, H = 100, 640, 110, 260
    y0 = T + H
    msi = [sum(defs[c][st]["mean_si"] for st in STYLES) / len(STYLES) for c, _ in cfgs]
    asr = [sum(defs[c][st]["asr"] for st in STYLES) / len(STYLES) * 100 for c, _ in cfgs]
    vmax = max(0.5, max(msi) + 0.12); vmin = min(-0.08, min(msi) - 0.06)
    def Y(v): return y0 - H * (v - vmin) / (vmax - vmin)
    s = head(w, h, "四种裁判配置下的文风操纵效果：防御有效，代价不同",
             "左：平均评分膨胀 SI（7 种文风合并均值）；右：整体操纵成功率 ASR（SI ≥ +1 的比例）")
    for v in range(int(vmin), int(vmax) + 1):
        y = Y(v)
        s += "<line x1='%d' y1='%.1f' x2='%d' y2='%.1f' stroke='%s' stroke-width='1'/>" % (L, y, R, y, GRID if v else AXIS)
        s += "<text x='%d' y='%.1f' text-anchor='end' font-size='12' fill='%s' %s>%+.1f</text>" % (L - 8, y + 4, MUT, FONT, v)
    slot = (R - L) / 4
    bw = slot * 0.46
    cols = [BLUE, GREEN, ORANGE, PURPLE]
    for i, (c, cname) in enumerate(cfgs):
        x = L + i * slot + (slot - bw) / 2
        v = msi[i]
        s += "<rect x='%.1f' y='%.1f' width='%.1f' height='%.1f' fill='%s' fill-opacity='0.85' rx='3'/>" % (
            x, Y(max(v, 0)), bw, max(2, abs(Y(v) - Y(0))), cols[i])
        s += "<text x='%.1f' y='%.1f' text-anchor='middle' font-size='14' font-weight='700' fill='%s' %s>%+.2f</text>" % (
            x + bw / 2, Y(max(v, 0)) - 8, cols[i], FONT, v)
        s += "<text x='%.1f' y='%d' text-anchor='middle' font-size='13.5' font-weight='600' fill='%s' %s>%s</text>" % (x + bw / 2, y0 + 28, INK, FONT, cname)
    # 右侧 ASR 面板
    L2, R2 = 680, 900
    y0b = T + H
    for v in [0, 25, 50, 75, 100]:
        y = y0b - H * v / 100
        s += "<line x1='%d' y1='%.1f' x2='%d' y2='%.1f' stroke='%s' stroke-width='1'/>" % (L2, y, R2, y, GRID if v else AXIS)
        s += "<text x='%d' y='%.1f' text-anchor='end' font-size='12' fill='%s' %s>%d%%</text>" % (L2 - 6, y + 4, MUT, FONT, v)
    slot2 = (R2 - L2) / 4
    bw2 = slot2 * 0.46
    for i, (c, cname) in enumerate(cfgs):
        x = L2 + i * slot2 + (slot2 - bw2) / 2
        v = asr[i]
        y = y0b - H * v / 100
        s += "<rect x='%.1f' y='%.1f' width='%.1f' height='%.1f' fill='%s' fill-opacity='0.85' rx='3'/>" % (x, y, bw2, max(2, y0b - y), cols[i])
        s += "<text x='%.1f' y='%.1f' text-anchor='middle' font-size='13' font-weight='700' fill='%s' %s>%d%%</text>" % (x + bw2 / 2, y - 7, cols[i], FONT, round(v))
    s += "<text x='36' y='%d' font-size='12.5' fill='%s' %s>基线 = 朴素提示词；量规 = 明确声明风格不计分；去风格化 = 评分前统一改写为朴素段落；双裁判 = 两个不同家族模型取平均。</text>" % (y0 + 116, MUT, FONT)
    s += "<text x='36' y='%d' font-size='12.5' fill='%s' %s>同一批 30 份答案与全部变体，四个配置各判一遍。注意量规裁判的 ASR 反而高于基线——第九节解释为什么。</text>" % (y0 + 140, MUT, FONT)
    s += "</svg>"
    save("fig6_defense.svg", s)


# ---------------- fig7 类别热力图 ----------------
def fig7():
    cat_si = S["cat_si"]
    cats = ["漏洞分析", "告警研判", "代码审计", "IOC分析", "风险评级", "应急响应"]
    w, h = 1000, 420
    L, T = 130, 100
    cw, chh = 120, 46
    allv = [v for v in cat_si.values()]
    vmax = max(0.5, max(allv)); vmin = min(-0.5, min(allv))
    s = head(w, h, "哪些分析任务最容易被文风带偏？——类别 × 文风平均 SI",
             "颜色越红 = 涨分越多；格子数字为该类 5 个答案的平均 SI（主裁判）")
    def color(v):
        if v <= 0:
            t = min(1, -v / max(0.01, -vmin))
            return "rgba(5,150,105,%.2f)" % (0.15 + 0.6 * t)
        t = min(1, v / max(0.01, vmax))
        return "rgba(220,38,38,%.2f)" % (0.10 + 0.65 * t)
    for j, st in enumerate(STYLES):
        s += "<text x='%.1f' y='%d' text-anchor='middle' font-size='13' font-weight='600' fill='%s' %s>%s</text>" % (
            L + j * cw + cw / 2, T - 14, INK, FONT, STYLE_CN[st])
    for i, cat in enumerate(cats):
        s += "<text x='%d' y='%.1f' text-anchor='end' font-size='13.5' fill='%s' %s>%s</text>" % (L - 14, T + i * chh + chh / 2 + 5, INK, FONT, cat)
        for j, st in enumerate(STYLES):
            v = cat_si.get("%s|%s" % (cat, st))
            x, y = L + j * cw, T + i * chh
            s += "<rect x='%d' y='%d' width='%d' height='%d' fill='%s' stroke='white' stroke-width='2'/>" % (x, y, cw - 4, chh - 4, color(v))
            s += "<text x='%.1f' y='%.1f' text-anchor='middle' font-size='14' font-weight='700' fill='%s' %s>%+.1f</text>" % (
                x + (cw - 4) / 2, y + (chh - 4) / 2 + 5, INK if abs(v) < vmax * 0.6 else "white", FONT, v)
    s += "</svg>"
    save("fig7_category.svg", s)


# ---------------- fig8 跨裁判稳健性 ----------------
def fig8():
    defs = S["defenses"]
    judges = [("baseline", "qwen2.5:7b（主裁判）"), ("judge2_alone", "llama3.2:3b"), ("judge3_alone", "gemma2:2b")]
    cols = [BLUE, GREEN, PURPLE]
    w, h = 980, 500
    L, R, T, H = 90, 950, 100, 310
    y0 = T + H
    vals = [defs[j][st]["mean_si"] for j, _ in judges for st in STYLES]
    vmax = max(2.0, max(vals) + 0.4); vmin = min(-0.5, min(vals) - 0.3)
    def Y(v): return y0 - H * (v - vmin) / (vmax - vmin)
    s = head(w, h, "换三个裁判，结论还在吗？——同一批文本，三个模型的平均 SI",
             "三个裁判分属三个模型家族，输入完全相同；基线提示词，温度 0")
    for v in range(int(vmin), int(vmax) + 1):
        y = Y(v)
        s += "<line x1='%d' y1='%.1f' x2='%d' y2='%.1f' stroke='%s' stroke-width='1'/>" % (L, y, R, y, GRID if v else AXIS)
        s += "<text x='%d' y='%.1f' text-anchor='end' font-size='12' fill='%s' %s>%+d</text>" % (L - 8, y + 4, MUT, FONT, v)
    slot = (R - L) / len(STYLES)
    bw = (slot - 40) / 3
    for i, st in enumerate(STYLES):
        for ji, (j, jn) in enumerate(judges):
            v = defs[j][st]["mean_si"]
            x = L + i * slot + 20 + ji * bw
            s += "<rect x='%.1f' y='%.1f' width='%.1f' height='%.1f' fill='%s' fill-opacity='0.85' rx='2'/>" % (
                x, Y(max(v, 0)), bw - 4, max(2, abs(Y(v) - Y(0))), cols[ji])
            s += "<text x='%.1f' y='%.1f' text-anchor='middle' font-size='10.5' fill='%s' %s>%+.1f</text>" % (x + (bw - 4) / 2, Y(max(v, 0)) - 4, cols[ji], FONT, v)
        s += "<text x='%.1f' y='%d' text-anchor='middle' font-size='13' font-weight='600' fill='%s' %s>%s</text>" % (L + i * slot + slot / 2, y0 + 26, INK, FONT, STYLE_CN[st])
    ly = T + 4
    for (j, jn), col in zip(judges, cols):
        s += "<rect x='%d' y='%d' width='12' height='12' fill='%s' rx='2'/>" % (R - 300, ly - 10, col)
        s += "<text x='%d' y='%d' font-size='12' fill='%s' %s>%s</text>" % (R - 284, ly, INK, FONT, jn)
        ly += 22
    s += "</svg>"
    save("fig8_robust.svg", s)


if __name__ == "__main__":
    fig1(); fig2(); fig3(); fig4(); fig5(); fig6(); fig7(); fig8()

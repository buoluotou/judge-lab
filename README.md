# judge-lab：LLM-as-a-Judge 文风操纵攻防实验

《只改"写法"，不改答案，AI 裁判就会被带偏吗？》一文的全部实验代码与原始记录。

## 一句话

把 30 份安全分析答案用 7 种文风改写（事实一个不动），交给 3 个本地 LLM 裁判重新打分 / 排序，
测评分膨胀（SI）、偏好翻盘（PRR）、操纵成功率（ASR）与语义保持，再实测 4 种防御配置。

## 复现

```bash
ollama pull qwen2.5:7b-instruct llama3.2:3b gemma2:2b bge-m3
python run_transform.py style      # 210 份改写 + 事实硬校验
python run_transform.py rescue     # 判废样本用强化提示词补救
python run_transform.py normalize  # 去风格化预处理（防御 3）
python run_judge.py q25_base       # 依次跑 q25_rub / q25_norm / l32_base / g22_base / pairs
python analyze.py                  # 指标聚合 -> results/summary.json
python make_figs.py                # 文章全部 SVG 图表
python count_calls.py              # 调用次数对账
```

全部脚本支持断点续跑（results/*.jsonl 逐条落盘，重跑自动跳过已完成部分）。

## 已知的两个坑（复现前必读）

- Python 正则的 `\b` 把中文当 `\w`，"主机10.0.0.8的"这类紧贴中文的 IP 提取会失败，
  `factcheck.py` 里用 lookaround 解决。
- 给 qwen2.5 / llama / gemma 等非思考模型传 `think: false`，Ollama 直接 400；
  `think` 参数只对 qwen3 系有效，非思考模型必须不下发该参数（`ollama_client.py` 的 `think=None`）。

## 结果速览（详见 ../article-judge/article.md）

| 文风 | 平均 SI | ASR（Δ≥+1） | PRR（配对翻盘） |
|---|---|---|---|
| 冗长版 | **+0.57** | **57%** | 73% |
| 分点版 | −0.38 | 4% | 25% |
| 术语版 / 升级 | 0.00 / +0.07 | 0% / 7% | 0% / 7% |
| 笃定版 / 升级 | 0.00 / −0.07 | 0% / 0% | 0% / 20% |
| 报告版 | +0.17 | 21% | **88%** |

防御（整体 ASR）：基线 13% → 详细量规 28%（反效果）→ 去风格化 14% → 双裁判 2%。

#!/bin/bash
# 改写完成后的完整执行链：去风格化 -> 5 个评分配置 -> 配对偏好 -> 指标聚合
set -u
cd /d/edge/qax/judge-lab
for step in "normalize" "q25_base" "q25_rub" "q25_norm" "l32_base" "g22_base" "pairs"; do
  echo "===== STEP $step ====="
  if [ "$step" = "normalize" ]; then
    python run_transform.py normalize
  else
    python run_judge.py "$step"
  fi
done
echo "===== ANALYZE ====="
python analyze.py
echo "ALL STEPS DONE"

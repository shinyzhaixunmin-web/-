# 完整示例：两店沙龙的一个经营周期

> ⚠️ **门店、人物、数据全部是虚构的**，只用来演示 5 个沙龙技能加上数据工具如何配合，不代表任何真实门店，也不是效果预测。

## 故事线
| 时间 | 文件 | 用到的技能或工具 | 这一步演示什么 |
|---|---|---|---|
| 2026-01-05 | [00_综合诊断.md](00_综合诊断.md) | `salon-strategy-advisor` | 老板一次提了好几件事：拆分、分层、排序，并否掉"储值冲业绩" |
| 2026-01-05 | [01_方针展开.md](01_方针展开.md) | `salon-policy-deployment` | 没有基线时，第一个突破目标就是建立基线 |
| 2026-03-31 | [reports/基线报告_截至2026-03-31.md](reports/基线报告_截至2026-03-31.md) | `tools/salon_metrics.py` | 收入和预收分开；复购率**还算不出来**，如实写"未满窗口" |
| 2026-03-31 | [02_改善问题卡.md](02_改善问题卡.md) | `salon-kaizen-card` | 一个问题、主假设加备选解释、小范围试点、三类指标、对照店 |
| 2026-06-30 | [reports/试点数据_截至2026-06-30.md](reports/试点数据_截至2026-06-30.md) | `tools/salon_metrics.py` | 试点前后、对照店、按技师拆分、保护指标 |
| 2026-06-30 | [03_试点复盘.md](03_试点复盘.md) | `salon-pilot-review` | 结果变好也不固化：对照店同幅上升、投诉增加、执行不均 |
| 2026-07-10 | [04_扩张评估.md](04_扩张评估.md) | `salon-expansion-check` | 拆穿"储值 25 万"的口径，门槛没过就停在第 1 步 |

## 这个示例最想说明的 5 件事
1. **办卡不是业绩。** B 店 3 月"营业额 25 万"里，有 20 万是预收款（负债）。
2. **算不出来就写"未知"。** 3 月底连一个月份组都没满 60 天，复购率只能等。
3. **变好不等于有效。** 没做试点的对照店同期也涨了同样幅度。
4. **相关不等于因果。** "当场预约的人复购高"，可能只是本来就想回来的人更愿意预约。
5. **保护指标会说话。** 复购在涨，投诉也在涨，这时只能调整，不能固化。

## 自己动手跑
```bash
# 1. 重新生成虚构数据（固定随机种子，结果不变）
python3 examples/demo-salon/gen_demo_data.py

# 2. 还原 3 月底能看到的基线
python3 tools/salon_metrics.py examples/demo-salon/data --until 2026-03-31 \
  --out examples/demo-salon/reports/基线报告_截至2026-03-31.md

# 3. 试点复盘数据（含对照店）
python3 tools/salon_metrics.py examples/demo-salon/data \
  --pilot-store A店 --pilot-service 护理 --pilot-start 2026-04-01 --compare-store B店 \
  --out examples/demo-salon/reports/试点数据_截至2026-06-30.md
```

## 换成你自己的门店
1. 按 [data/数据字典.md](data/数据字典.md) 的格式从收银系统导出 CSV，放进一个新目录，例如 `stores/我的沙龙/data/`。真实经营数据请不要提交到公开仓库。
2. 运行 `python3 tools/salon_metrics.py stores/我的沙龙/data --out stores/我的沙龙/reports/基线报告.md`
3. 把报告交给 Claude，然后说"用 salon-strategy-advisor 帮我诊断"，就会从 `00_综合诊断` 开始走这个流程。

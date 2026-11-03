# 验证方法

## 1. 离线功能测试（不需要凭证、不访问云）
```bash
python -m unittest discover -s tests -v
```
覆盖：签名与官方 SDK 一致、四个子命令、分页、到期识别、使用率计算、参数错误/缺凭证/API 错误/网络错误的退出码、凭证不出现在输出中。

## 2. 真实账号验证（只读、零费用）

| 用例 | 命令 | 预期 |
| --- | --- | --- |
| R1 列表 | `python scripts/coupon_query.py list` | 退出码 0，输出表头与券列表（无券时显示“（无记录）”） |
| R2 JSON | `python scripts/coupon_query.py list --json` | 合法 JSON，含 `count`、`coupons` |
| R3 可用券 | `python scripts/coupon_query.py list --status available` | 只包含“待使用” |
| R4 到期 | `python scripts/coupon_query.py expiring --days 365` | 退出码 0，按到期时间排序 |
| R5 使用率 | `python scripts/coupon_query.py usage` | 输出总面额/已用/余额/使用率 |
| R6 单券 | `python scripts/coupon_query.py status <R2 中任一 coupon_id>` | 退出码 0；不存在的 ID 返回退出码 4 |
| R7 缺凭证 | 清空 AK/SK 后运行 `list` | 退出码 3，不发请求 |
| R8 参数错误 | `python scripts/coupon_query.py expiring --days 0` | 退出码 2 |

与控制台核对：费用中心 → 优惠与折扣 → 优惠券，张数和余额应与 R1/R5 一致。

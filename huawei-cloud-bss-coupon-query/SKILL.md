---
name: huawei-cloud-bss-coupon-query
description: |
  Query Huawei Cloud (华为云) BSS coupons (代金券) of the current account — read-only. Lists coupons, checks a coupon's status and balance, finds coupons that will expire soon, and analyzes coupon usage rate. Uses BSS API ListSubCustomerCoupons (GET /v2/promotions/benefits/coupons) with AK/SK signing; never creates, modifies, or spends anything.
  Triggers: "代金券", "查代金券", "我的代金券", "代金券余额", "代金券状态", "代金券快过期", "即将到期的代金券", "代金券使用率", "优惠券列表", "华为云 coupon", "voucher balance", "expiring coupons", "coupon usage".
---

# 华为云 BSS 代金券查询（huawei-cloud-bss-coupon-query）

## Overview

回答用户关于**自己账号代金券**的问题：有哪些券、某张券还剩多少、哪些券快过期、代金券整体用了多少。

- **只读**：仅调用 BSS「查询优惠券列表」`ListSubCustomerCoupons`（`GET /v2/promotions/benefits/coupons`），不创建、不修改、不消耗任何资源，**零费用**。
- **零依赖**：Python 3.8+ 标准库即可运行，不需要安装 SDK。
- **凭证安全**：AK/SK 只从环境变量读取，不写文件、不打印；输出中的券 ID 默认脱敏。

## When to use / When NOT to use

| 使用 | 不使用 |
| --- | --- |
| 查代金券列表、状态、余额、到期时间 | 发放/回收代金券（合作伙伴操作，写操作） |
| 找出 N 天内要过期的可用代金券 | 查账单、余额、订单（用账单类技能） |
| 统计代金券使用率、已过期浪费金额 | 购买资源时选择用哪张券 |

## Prerequisites

1. Python 3.8+：`python --version`
2. 华为云 AK/SK，配置为环境变量（详见 [references/cli-installation-guide.md](references/cli-installation-guide.md)）：
   - `HUAWEICLOUD_SDK_AK`、`HUAWEICLOUD_SDK_SK`（必填）
   - `HUAWEICLOUD_SDK_DOMAIN_ID`（选填；不填会用 AK/SK 自动从 IAM 获取账号 ID）
3. IAM 权限：`bss:coupon:view`（详见 [references/iam-policies.md](references/iam-policies.md)）

## Workflow

`<SKILL_DIR>` 表示本 SKILL.md 所在目录。所有命令加 `--json` 可得到机器可读输出。

### Step 1：确认凭证
检查 `HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK` 是否已设置（**只检查是否存在，不要回显其值**）。缺失时引导用户按 cli-installation-guide 配置，不要让用户把 AK/SK 粘贴进对话。

### Step 2：把用户意图映射到子命令

| 用户说 | 命令 |
| --- | --- |
| “我有哪些代金券” / “列出可用的代金券” | `python <SKILL_DIR>/scripts/coupon_query.py list [--status available]` |
| “这张券（ID）还剩多少 / 什么状态” | `python <SKILL_DIR>/scripts/coupon_query.py status <coupon_id>` |
| “哪些代金券快过期了” / “30 天内到期的券” | `python <SKILL_DIR>/scripts/coupon_query.py expiring --days 30` |
| “代金券用了多少 / 使用率” | `python <SKILL_DIR>/scripts/coupon_query.py usage` |

`list` 参数：`--status inactive|available|used|expired|recycled`，`--type voucher|discount|product|cash`（默认 voucher 代金券），`--all-types` 不按类型筛选。
`expiring` 参数：`--days 1~365`，默认 30，只统计“待使用”状态的代金券。

### Step 3：解读结果并回答
- 列表：说明总张数、可用张数与合计余额；券 ID 保持脱敏展示。
- 到期：按到期时间从近到远列出，给出剩余天数，并提醒“尽快使用，过期作废”。
- 使用率：给出总面额、已用、余额、使用率，以及已过期未用完的金额；老版本券没有余额字段，不计入使用率，需说明。

### Step 4：处理错误（按退出码）

| 退出码 | 含义 | 处理 |
| --- | --- | --- |
| 0 | 成功 | — |
| 2 | 参数错误 | 按 `--help` 修正参数后重试 |
| 3 | 缺少凭证 | 引导配置环境变量，不要索要明文 AK/SK |
| 4 | API 错误（含 401/403、券不存在） | 转述 `error_code` / `error_msg` 与提示；403 引导授予 `bss:coupon:view` |
| 5 | 网络异常 | 检查网络/代理后重试一次 |

## Constraints

- 只执行本技能脚本中的只读查询，不调用任何写接口。
- 不在回答、日志、文件中输出 AK/SK、Token、完整 customer_id。
- 已使用 / 已过期 / 已回收的券，接口只返回 12 个月内的数据，回答时需说明。

## References

- [references/cli-installation-guide.md](references/cli-installation-guide.md) — 运行环境与凭证配置
- [references/iam-policies.md](references/iam-policies.md) — 最小权限策略
- [references/verification-method.md](references/verification-method.md) — 验证方法与验收标准

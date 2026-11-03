# 安全审计报告：huawei-cloud-bss-coupon-query

## 一、自查结论：通过

| 检查项 | 结果 | 依据 |
| --- | --- | --- |
| 硬编码密钥 | ✅ 无 | 代码中不存在 AK/SK/Token 字面量；凭证仅从环境变量读取（`coupon_query.py` 的 `run()`） |
| 凭证外泄 | ✅ 无 | 不打印、不写文件、不放进 URL；测试 `test_secrets_never_printed` 验证错误输出中不含 AK/SK |
| 写操作 | ✅ 无 | 只调用 GET `/v2/promotions/benefits/coupons` 与 GET `/v3/auth/domains`；脚本中不存在 POST/PUT/DELETE |
| 最小权限 | ✅ | 仅需 `bss:coupon:view`（references/iam-policies.md） |
| 费用风险 | ✅ 零费用 | 只读查询，不创建资源 |
| 第三方依赖 | ✅ 无 | 仅用 Python 标准库，无供应链风险 |
| 命令注入 | ✅ 无 | 不调用 shell/subprocess；参数由 argparse 枚举约束，查询串经 RFC 3986 编码 |
| 传输安全 | ✅ | 只访问 `https://bss.myhuaweicloud.com`、`https://iam.myhuaweicloud.com`，使用系统 TLS 校验 |
| 敏感信息展示 | ✅ | 文本输出中券 ID 脱敏（前 4 后 4），不输出 customer_id |
| 错误处理 | ✅ | 结构化错误 + 区分退出码（2/3/4/5），不吞错 |

## 二、可复现的检查命令

```bash
# 1) 不应出现写方法
grep -nE '"(POST|PUT|DELETE|PATCH)"' huawei-cloud-bss-coupon-query/scripts/*.py   # 预期：无输出
# 2) 不应出现 shell 调用
grep -nE 'subprocess|os\.system|eval\(|exec\(' huawei-cloud-bss-coupon-query/scripts/*.py   # 预期：无输出
# 3) 不应出现疑似密钥
grep -nE '[A-Z0-9]{20}' -r huawei-cloud-bss-coupon-query   # 预期：只命中测试里的假值或无输出
```

## 三、huawei-cloud-skill-audit 审计结果

> 使用官方技能 huawei-cloud-skill-audit 对本技能审计后，将其报告原文附于此处或 `reports/skill-audit-report.md`。

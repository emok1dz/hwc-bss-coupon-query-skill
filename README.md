# 华为云BSS代金券查询Skill

ICT 大赛实践赛题 **1.10「Skill-如何写好一个调用华为云服务的技能」** 作品。

技能 [`huawei-cloud-bss-coupon-query`](huawei-cloud-bss-coupon-query/SKILL.md) 面向华为云 BSS，提供四项**只读**的代金券查询能力：

| 能力 | 子命令 | 说明 |
| --- | --- | --- |
| 代金券列表 | `list` | 按状态、类型筛选，自动分页 |
| 券状态查询 | `status <coupon_id>` | 单张券的状态、余额、有效期 |
| 即将到期识别 | `expiring --days N` | N 天内到期且仍可用的代金券，按到期时间排序 |
| 使用率分析 | `usage` | 总面额、已用、余额、使用率、已过期浪费金额，并按状态和类型汇总 |

调用的 API 为 BSS `ListSubCustomerCoupons`（`GET /v2/promotions/benefits/coupons`），只需要 `bss:coupon:view` 权限，**不创建资源、零费用**。

## 三项质量标准

| 标准 | 本作品的做法 | 证据 |
| --- | --- | --- |
| **结构规范** | 标准技能目录：`SKILL.md`（frontmatter 中写明 name 和含触发词的 description；正文按 Overview → 适用边界 → 前置条件 → 工作流 → 错误处理 → 约束组织）+ `references/` 三件套 + `scripts/` + `tests/` | 下方目录结构 |
| **功能正确** | 离线单元测试覆盖全部子命令和错误路径；签名算法与华为云官方 SDK 逐字节一致；真实账号用例 R1–R8 | [reports/test-report.md](reports/test-report.md) |
| **安全合规** | 只读接口、最小权限、凭证只走环境变量、不打印密钥、ID 脱敏、零第三方依赖 | [reports/audit-report.md](reports/audit-report.md) |

## 目录结构

```
huawei-cloud-bss-coupon-query/
├── SKILL.md                          # 技能主文件
├── references/
│   ├── cli-installation-guide.md     # 运行环境与凭证配置
│   ├── iam-policies.md               # 最小权限策略
│   └── verification-method.md        # 验证方法与验收用例
├── scripts/
│   ├── coupon_query.py               # 查询脚本（list/status/expiring/usage，--json，退出码）
│   └── hwc_signer.py                 # AK/SK 签名（SDK-HMAC-SHA256）
└── tests/
    └── test_coupon_query.py          # 离线测试（假 HTTP，不访问云）
reports/
├── test-report.md                    # 测试报告
└── audit-report.md                   # 安全审计报告
```

## 快速使用

```bash
# 配置凭证（PowerShell 用 $env:HUAWEICLOUD_SDK_AK="..."）
export HUAWEICLOUD_SDK_AK="你的AK"
export HUAWEICLOUD_SDK_SK="你的SK"

cd huawei-cloud-bss-coupon-query
python scripts/coupon_query.py list --status available
python scripts/coupon_query.py expiring --days 30
python scripts/coupon_query.py usage --json
```

## 安装为智能体技能

把 `huawei-cloud-bss-coupon-query/` 目录复制到智能体的技能目录即可（例如 Claude Code 的 `~/.claude/skills/`）。之后直接问“我有哪些代金券快过期了？”，智能体就会加载并调用它。

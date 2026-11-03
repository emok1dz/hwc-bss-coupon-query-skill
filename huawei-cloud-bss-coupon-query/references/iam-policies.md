# IAM 权限说明

本技能只调用一个只读接口：

| 接口 | 用途 | 所需权限 |
| --- | --- | --- |
| BSS `ListSubCustomerCoupons`（GET /v2/promotions/benefits/coupons） | 查询优惠券列表 | `bss:coupon:view` |
| IAM `KeystoneListAuthDomains`（GET /v3/auth/domains） | 未配置 `HUAWEICLOUD_SDK_DOMAIN_ID` 时获取账号 ID | 无需额外授权 |

## 最小权限自定义策略

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["bss:coupon:view"]
    }
  ]
}
```

也可以直接授予系统策略 **BSS ReadOnlyAccess**（费用中心只读）。**不要**授予 BSS Administrator 等带写权限的策略。

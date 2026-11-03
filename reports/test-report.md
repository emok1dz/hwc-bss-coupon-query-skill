# 测试报告：huawei-cloud-bss-coupon-query

## 一、离线功能测试

- 命令：`python -m unittest discover -s tests -v`（在 `huawei-cloud-bss-coupon-query/` 目录下运行）
- 环境：Python 3.13，Linux，不访问网络，HTTP 由测试替身模拟
- 结果：**15 个用例全部通过**

```
test_expiring (test_coupon_query.TestCommands.test_expiring) ... ok
test_list_filter_status_and_masked_text (test_coupon_query.TestCommands.test_list_filter_status_and_masked_text) ... ok
test_list_json_with_domain_header_and_signature (test_coupon_query.TestCommands.test_list_json_with_domain_header_and_signature) ... ok
test_pagination (test_coupon_query.TestCommands.test_pagination) ... ok
test_status_found_and_not_found (test_coupon_query.TestCommands.test_status_found_and_not_found) ... ok
test_usage (test_coupon_query.TestCommands.test_usage) ... ok
test_usage_text (test_coupon_query.TestCommands.test_usage_text) ... ok
test_api_error_passthrough (test_coupon_query.TestErrors.test_api_error_passthrough) ... ok
test_bad_args_exit_2 (test_coupon_query.TestErrors.test_bad_args_exit_2) ... ok
test_missing_credentials_exit_3_and_no_request (test_coupon_query.TestErrors.test_missing_credentials_exit_3_and_no_request) ... ok
test_network_error_exit_5 (test_coupon_query.TestErrors.test_network_error_exit_5) ... ok
test_secrets_never_printed (test_coupon_query.TestErrors.test_secrets_never_printed) ... ok
test_mask (test_coupon_query.TestPure.test_mask) ... ok
test_old_coupon_without_balance_excluded_from_rate (test_coupon_query.TestPure.test_old_coupon_without_balance_excluded_from_rate) ... ok
test_matches_official_sdk (test_coupon_query.TestSigner.test_matches_official_sdk) ... ok
Ran 15 tests in 0.019s
OK
```

| 类别 | 用例 | 验证点 |
| --- | --- | --- |
| 签名 | test_matches_official_sdk | 与华为云官方 Python SDK（huaweicloudsdkcore Signer）对同一请求计算的签名一致 |
| 列表 | test_list_json_with_domain_header_and_signature | 请求路径和查询串正确、带 X-Domain-Id、签名头格式正确、默认只查代金券 |
| 列表 | test_list_filter_status_and_masked_text | 状态筛选生效 |
| 列表 | test_pagination | 250 张券分 3 页拉全 |
| 状态 | test_status_found_and_not_found | 存在返回余额；不存在退出码 4 |
| 到期 | test_expiring | 只返回 30 天内到期、待使用的券，剩余天数正确 |
| 使用率 | test_usage / test_usage_text | 总面额 400、余额 190、已用 210、使用率 52.5%、过期浪费 30 |
| 使用率 | test_old_coupon_without_balance_excluded_from_rate | 无余额字段的老版本券不计入使用率 |
| 错误 | test_missing_credentials_exit_3_and_no_request | 缺凭证退出码 3，且不发请求 |
| 错误 | test_bad_args_exit_2 | 非法参数退出码 2 |
| 错误 | test_api_error_passthrough | 透传 http_status / error_code，403 给出授权提示 |
| 错误 | test_network_error_exit_5 | 网络异常退出码 5 |
| 安全 | test_secrets_never_printed | AK/SK 不出现在任何输出中 |
| 工具 | test_mask | ID 脱敏 |

## 二、真实接口连通性（假凭证）

用一组无效的 AK/SK 运行 `python scripts/coupon_query.py usage --json`，请求真实到达华为云 IAM，返回：

```
HTTP 401  error_code=APIGW.0301  "Incorrect IAM authentication information: Unauthorized"
退出码 4，并提示“检查 AK/SK 是否正确、是否已停用，以及本机时间是否准确”
```

说明请求构造、签名格式与错误处理链路正常。

## 三、真实账号验证（用例 R1–R8，见 references/verification-method.md）

> 由账号持有人在本机用自己的只读 AK/SK 执行后填写。

| 用例 | 结果 | 备注 |
| --- | --- | --- |
| R1 列表 | 待执行 | |
| R2 JSON | 待执行 | |
| R3 可用券 | 待执行 | |
| R4 到期 | 待执行 | |
| R5 使用率 | 待执行 | |
| R6 单券 | 待执行 | |
| R7 缺凭证 | 待执行 | |
| R8 参数错误 | 待执行 | |

## 四、huawei-cloud-skill-tester 测试结果

> 使用官方技能 huawei-cloud-skill-tester 对本技能测试后，将其报告原文附于此处或 `reports/skill-tester-report.md`。

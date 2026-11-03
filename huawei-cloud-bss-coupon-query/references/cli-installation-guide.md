# 运行环境与凭证配置

## 1. Python
需要 Python 3.8 或更高版本，只用标准库，不需要 `pip install`。

```bash
python --version      # Windows
python3 --version     # Linux / macOS
```

## 2. 获取 AK/SK
华为云控制台 → 右上角用户名 → **我的凭证** → **访问密钥** → **新增访问密钥**，下载 `credentials.csv`。
建议使用**只读权限的 IAM 子用户**的 AK/SK（权限见 [iam-policies.md](iam-policies.md)），不要使用主账号密钥。

## 3. 配置环境变量（只对当前终端生效）

PowerShell：
```powershell
$env:HUAWEICLOUD_SDK_AK = "你的AK"
$env:HUAWEICLOUD_SDK_SK = "你的SK"
# 选填：账号ID，不填会自动从 IAM 获取
# $env:HUAWEICLOUD_SDK_DOMAIN_ID = "你的账号ID"
```

bash：
```bash
export HUAWEICLOUD_SDK_AK="你的AK"
export HUAWEICLOUD_SDK_SK="你的SK"
```

也兼容 `HW_ACCESS_KEY` / `HW_SECRET_KEY`（与 Terraform 华为云 Provider 一致）。

## 4. 自检
```bash
python scripts/coupon_query.py --help
python scripts/coupon_query.py usage
```

## 安全提示
- 不要把 AK/SK 写进脚本、配置文件或提交到代码仓库；
- 不要把 AK/SK 粘贴进与 AI 的对话；
- 用完可在控制台停用或删除该访问密钥。

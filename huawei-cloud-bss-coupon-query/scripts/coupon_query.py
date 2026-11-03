#!/usr/bin/env python3
"""华为云 BSS 代金券查询（只读）。仅依赖 Python 3.8+ 标准库。

子命令：
  list       代金券列表（可按状态/类型筛选）
  status     查询单张券的状态与余额
  expiring   识别 N 天内即将到期、仍可使用的券
  usage      代金券使用率分析（总面额/已用/余额/按状态与类型统计）

调用的 API：BSS ListSubCustomerCoupons  GET /v2/promotions/benefits/coupons （只读）
凭证：环境变量 HUAWEICLOUD_SDK_AK / HUAWEICLOUD_SDK_SK（AK/SK 签名，不落盘、不打印）

退出码：0 成功；2 参数错误；3 缺少凭证/配置；4 API 返回错误；5 网络异常
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any, Callable

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hwc_signer import rfc3986, sign  # noqa: E402

BSS_ENDPOINT = "https://bss.myhuaweicloud.com"
IAM_ENDPOINT = "https://iam.myhuaweicloud.com"
COUPON_PATH = "/v2/promotions/benefits/coupons"
PAGE_SIZE = 100
MAX_PAGES = 50

STATUS = {1: "未激活", 2: "待使用", 3: "已使用", 4: "已过期", 5: "已回收"}
STATUS_BY_NAME = {"inactive": 1, "available": 2, "used": 3, "expired": 4, "recycled": 5}
TYPES = {1: "代金券", 2: "折扣券", 3: "产品券", 4: "现金券"}
TYPE_BY_NAME = {"voucher": 1, "discount": 2, "product": 3, "cash": 4}

EXIT_OK, EXIT_ARGS, EXIT_CONFIG, EXIT_API, EXIT_NETWORK = 0, 2, 3, 4, 5


class CouponError(Exception):
    def __init__(self, code: str, message: str, exit_code: int, **details: Any):
        super().__init__(message)
        self.code, self.message, self.exit_code, self.details = code, message, exit_code, details


# ------------------------------------------------------------------ HTTP

HttpGet = Callable[[str, dict], tuple]  # (url, headers) -> (status, body_text)


def default_http_get(url: str, headers: dict, timeout: float = 20) -> tuple:
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise CouponError("NETWORK_ERROR", f"网络异常：{getattr(exc, 'reason', exc)}", EXIT_NETWORK)


class Client:
    def __init__(self, ak: str, sk: str, domain_id: str | None = None, http_get: HttpGet | None = None,
                 bss_endpoint: str = BSS_ENDPOINT, iam_endpoint: str = IAM_ENDPOINT):
        self.ak, self.sk, self.domain_id = ak, sk, domain_id
        self.http_get = http_get or default_http_get
        self.bss_endpoint, self.iam_endpoint = bss_endpoint.rstrip("/"), iam_endpoint.rstrip("/")

    def _get(self, base: str, path: str, query: list[tuple[str, Any]], extra_headers: dict | None = None) -> dict:
        qs = "&".join(f"{rfc3986(k)}={rfc3986(v)}" for k, v in sorted((k, str(v)) for k, v in query))
        url = f"{base}{path}" + (f"?{qs}" if qs else "")
        headers = sign("GET", url, {"Content-Type": "application/json", **(extra_headers or {})}, "", self.ak, self.sk)
        status, text = self.http_get(url, headers)
        try:
            data = json.loads(text) if text else {}
        except json.JSONDecodeError:
            data = None
        if status >= 400 or data is None:
            data = data or {}
            raise CouponError("API_ERROR", f"接口返回错误（HTTP {status}）：{data.get('error_msg') or (text or '')[:200]}",
                              EXIT_API, http_status=status, error_code=data.get("error_code"),
                              error_msg=data.get("error_msg"), hint=_hint(status))
        return data

    def ensure_domain_id(self) -> str:
        """BSS 是全局服务，需要账号 ID（X-Domain-Id）；未配置时用 AK/SK 调 IAM 自动获取。"""
        if not self.domain_id:
            data = self._get(self.iam_endpoint, "/v3/auth/domains", [])
            domains = data.get("domains") or []
            if not domains:
                raise CouponError("API_ERROR", "无法从 IAM 获取账号 ID（domain_id）", EXIT_API)
            self.domain_id = domains[0]["id"]
        return self.domain_id

    def list_coupons(self, status: int | None = None, coupon_type: int | None = None,
                     coupon_id: str | None = None) -> list[dict]:
        """分页拉取全部满足条件的券。"""
        domain = self.ensure_domain_id()
        result, offset = [], 0
        for _ in range(MAX_PAGES):
            query: list[tuple[str, Any]] = [("offset", offset), ("limit", PAGE_SIZE)]
            if status is not None:
                query.append(("status", status))
            if coupon_type is not None:
                query.append(("coupon_type", coupon_type))
            if coupon_id:
                query.append(("coupon_id", coupon_id))
            data = self._get(self.bss_endpoint, COUPON_PATH, query, {"X-Domain-Id": domain})
            page = data.get("user_coupons") or []
            result.extend(page)
            total = data.get("count", len(result))
            offset += len(page)
            if not page or offset >= total:
                break
        return result


def _hint(status: int) -> str:
    return {
        401: "鉴权失败：检查 AK/SK 是否正确、是否已停用，以及本机时间是否准确。",
        403: "无权限：为 IAM 用户授予 BSS 只读权限（bss:coupon:view，或 BSS ReadOnlyAccess）。",
        429: "请求过于频繁，请稍后重试。",
    }.get(status, "请根据 error_code 查阅 BSS API 错误码。")


# ------------------------------------------------------------------ 分析逻辑（纯函数，便于测试）

def parse_time(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        return dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
    except ValueError:
        return None


def normalize(c: dict) -> dict:
    face = float(c.get("face_value") or 0)
    balance = c.get("balance")
    balance = float(balance) if balance is not None else None
    return {
        "coupon_id": c.get("coupon_id"),
        "type": TYPES.get(c.get("coupon_type"), str(c.get("coupon_type"))),
        "status": STATUS.get(c.get("status"), str(c.get("status"))),
        "status_code": c.get("status"),
        "face_value": face,
        "balance": balance,
        "used": round(face - balance, 2) if balance is not None else None,
        "currency": c.get("currency") or "CNY",
        "valid_time": c.get("valid_time"),
        "expire_time": c.get("expire_time"),
        "plan_name": c.get("plan_name"),
        "usage": c.get("coupon_usage"),
        "frozen": c.get("is_frozen") in ("1", 1, True, "true"),
    }


def find_expiring(coupons: list[dict], days: int, now: dt.datetime) -> list[dict]:
    limit = now + dt.timedelta(days=days)
    out = []
    for c in coupons:
        exp = parse_time(c.get("expire_time"))
        if c.get("status_code") == 2 and exp and now <= exp <= limit:
            item = dict(c)
            item["days_left"] = (exp - now).days
            out.append(item)
    return sorted(out, key=lambda x: x["expire_time"])


def analyze_usage(coupons: list[dict]) -> dict:
    with_balance = [c for c in coupons if c["balance"] is not None]
    face = round(sum(c["face_value"] for c in with_balance), 2)
    balance = round(sum(c["balance"] for c in with_balance), 2)
    used = round(face - balance, 2)
    by_status: dict[str, int] = {}
    by_type: dict[str, int] = {}
    for c in coupons:
        by_status[c["status"]] = by_status.get(c["status"], 0) + 1
        by_type[c["type"]] = by_type.get(c["type"], 0) + 1
    expired_waste = round(sum(c["balance"] for c in with_balance if c["status_code"] == 4), 2)
    return {
        "total_count": len(coupons),
        "face_value_total": face,
        "used_total": used,
        "balance_total": balance,
        "usage_rate": round(used / face, 4) if face else None,
        "expired_unused_balance": expired_waste,
        "by_status": by_status,
        "by_type": by_type,
        "excluded_without_balance": len(coupons) - len(with_balance),
    }


def mask(value: str | None) -> str:
    if not value:
        return "-"
    return value if len(value) <= 8 else f"{value[:4]}****{value[-4:]}"


# ------------------------------------------------------------------ CLI

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="coupon_query.py", description="华为云 BSS 代金券查询（只读）")
    p.add_argument("--json", action="store_true", help="输出 JSON（便于智能体/脚本解析）")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="输出 JSON")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("list", parents=[common], help="代金券列表", description="列出账号下的优惠券，可按状态与类型筛选。")
    s.add_argument("--status", choices=list(STATUS_BY_NAME), help="状态：inactive 未激活 / available 待使用 / used 已使用 / expired 已过期 / recycled 已回收")
    s.add_argument("--type", choices=list(TYPE_BY_NAME), default="voucher", help="类型，默认 voucher（代金券）；all 不筛选可用 --all-types")
    s.add_argument("--all-types", action="store_true", help="不按类型筛选")

    s = sub.add_parser("status", parents=[common], help="查询单张券的状态", description="按券 ID 查询状态、余额与有效期。")
    s.add_argument("coupon_id", help="优惠券 ID（可从 list 的 --json 输出中获取）")

    s = sub.add_parser("expiring", parents=[common], help="即将到期的券", description="识别 N 天内到期、仍处于“待使用”的代金券。")
    s.add_argument("--days", type=int, default=30, help="提前天数，1~365，默认 30")

    sub.add_parser("usage", parents=[common], help="使用率分析", description="统计代金券总面额、已用金额、余额、使用率，并按状态/类型汇总。")
    return p


def run(argv: list[str], env: dict | None = None, http_get: HttpGet | None = None,
        now: dt.datetime | None = None, out=sys.stdout, err=sys.stderr) -> int:
    env = os.environ if env is None else env
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            args = build_parser().parse_args(argv)
    except SystemExit as exc:  # argparse 已输出用法/错误
        return EXIT_OK if exc.code == 0 else EXIT_ARGS

    try:
        if args.command == "expiring" and not 1 <= args.days <= 365:
            raise CouponError("INVALID_ARGUMENTS", "--days 必须在 1~365 之间", EXIT_ARGS)
        ak = env.get("HUAWEICLOUD_SDK_AK") or env.get("HW_ACCESS_KEY")
        sk = env.get("HUAWEICLOUD_SDK_SK") or env.get("HW_SECRET_KEY")
        if not ak or not sk:
            raise CouponError("MISSING_CONFIG", "缺少凭证：请设置环境变量 HUAWEICLOUD_SDK_AK 和 HUAWEICLOUD_SDK_SK", EXIT_CONFIG,
                              hint="见 references/cli-installation-guide.md")
        client = Client(ak, sk, env.get("HUAWEICLOUD_SDK_DOMAIN_ID"), http_get=http_get,
                        bss_endpoint=env.get("HUAWEICLOUD_BSS_ENDPOINT", BSS_ENDPOINT))
        now = now or dt.datetime.now(dt.timezone.utc)

        if args.command == "list":
            ctype = None if args.all_types else TYPE_BY_NAME[args.type]
            status = STATUS_BY_NAME[args.status] if args.status else None
            coupons = [normalize(c) for c in client.list_coupons(status=status, coupon_type=ctype)]
            return _emit(args.json, {"count": len(coupons), "coupons": coupons}, _fmt_list(coupons), out)
        if args.command == "status":
            found = [normalize(c) for c in client.list_coupons(coupon_id=args.coupon_id)]
            if not found:
                raise CouponError("NOT_FOUND", f"未找到优惠券 {args.coupon_id}（已使用/过期/回收的券只保留 12 个月）", EXIT_API)
            return _emit(args.json, found[0], _fmt_list(found), out)
        if args.command == "expiring":
            coupons = [normalize(c) for c in client.list_coupons(status=2, coupon_type=1)]
            expiring = find_expiring(coupons, args.days, now)
            text = (f"{args.days} 天内到期的可用代金券：{len(expiring)} 张，合计余额 "
                    f"{sum(c['balance'] or 0 for c in expiring):.2f} 元\n" + _fmt_list(expiring, days_left=True))
            return _emit(args.json, {"days": args.days, "count": len(expiring), "coupons": expiring}, text, out)
        if args.command == "usage":
            coupons = [normalize(c) for c in client.list_coupons(coupon_type=1)]
            stats = analyze_usage(coupons)
            return _emit(args.json, stats, _fmt_usage(stats), out)
    except CouponError as exc:
        payload = {"error": {"code": exc.code, "message": exc.message, **{k: v for k, v in exc.details.items() if v is not None}}}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2), file=out)
        print(f"[{exc.code}] {exc.message}" + (f"\n提示：{exc.details['hint']}" if exc.details.get("hint") else ""), file=err)
        return exc.exit_code
    return EXIT_ARGS


def _emit(as_json: bool, data: Any, text: str, out) -> int:
    print(json.dumps(data, ensure_ascii=False, indent=2) if as_json else text, file=out)
    return EXIT_OK


def _fmt_list(coupons: list[dict], days_left: bool = False) -> str:
    if not coupons:
        return "（无记录）"
    head = ["券ID", "类型", "状态", "面额", "余额", "到期时间"] + (["剩余天数"] if days_left else [])
    rows = [[mask(c["coupon_id"]), c["type"], c["status"], f"{c['face_value']:.2f}",
             "-" if c["balance"] is None else f"{c['balance']:.2f}", c["expire_time"] or "-"]
            + ([str(c["days_left"])] if days_left else []) for c in coupons]
    return "\n".join(" | ".join(r) for r in [head] + rows)


def _fmt_usage(s: dict) -> str:
    rate = "-" if s["usage_rate"] is None else f"{s['usage_rate'] * 100:.1f}%"
    return "\n".join([
        f"代金券总数：{s['total_count']} 张",
        f"总面额：{s['face_value_total']:.2f} 元，已使用：{s['used_total']:.2f} 元，余额：{s['balance_total']:.2f} 元",
        f"使用率：{rate}；已过期未用完的余额：{s['expired_unused_balance']:.2f} 元",
        "按状态：" + "，".join(f"{k} {v}" for k, v in s["by_status"].items()),
    ])


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))

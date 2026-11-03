"""离线测试：用假 HTTP 响应验证参数校验、分页、到期识别、使用率分析、错误处理与退出码。

    python -m unittest discover -s tests -v
"""

import datetime as dt
import io
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))

import coupon_query as cq  # noqa: E402
import hwc_signer  # noqa: E402

NOW = dt.datetime(2026, 11, 3, 0, 0, 0, tzinfo=dt.timezone.utc)
ENV = {"HUAWEICLOUD_SDK_AK": "AK", "HUAWEICLOUD_SDK_SK": "SK"}


def coupon(cid, status=2, ctype=1, face=100.0, balance=60.0, expire="2026-11-20T00:00:00Z"):
    return {"coupon_id": cid, "status": status, "coupon_type": ctype, "face_value": face, "balance": balance,
            "expire_time": expire, "valid_time": "2026-01-01T00:00:00Z", "customer_id": "c" * 32}


class FakeHttp:
    def __init__(self, coupons, status=200, body=None):
        self.coupons, self.status, self.body, self.calls = coupons, status, body, []

    def __call__(self, url, headers):
        self.calls.append((url, headers))
        if "/v3/auth/domains" in url:
            return 200, json.dumps({"domains": [{"id": "d" * 32, "name": "demo"}]})
        if self.body is not None:
            return self.status, self.body
        q = dict(p.split("=", 1) for p in url.split("?", 1)[1].split("&"))
        off, lim = int(q["offset"]), int(q["limit"])
        items = [c for c in self.coupons if ("status" not in q or str(c["status"]) == q["status"])
                 and ("coupon_type" not in q or str(c["coupon_type"]) == q["coupon_type"])
                 and ("coupon_id" not in q or c["coupon_id"] == q["coupon_id"])]
        return 200, json.dumps({"count": len(items), "user_coupons": items[off:off + lim]})


def run(argv, http=None, env=ENV):
    out, err = io.StringIO(), io.StringIO()
    code = cq.run(argv, env=env, http_get=http, now=NOW, out=out, err=err)
    return code, out.getvalue(), err.getvalue()


class TestSigner(unittest.TestCase):
    def test_matches_official_sdk(self):
        # 期望值由华为云官方 Python SDK huaweicloudsdkcore Signer 对同一请求计算得到
        now = dt.datetime(2026, 5, 3, 8, 9, 10, tzinfo=dt.timezone.utc)
        url = ("https://projectman-ext.cn-north-4.myhuaweicloud.com/v4/projects?limit=10&offset=0&search="
               + hwc_signer.rfc3986("测试 a*b") + "&sort=" + hwc_signer.rfc3986("created_on:desc,name:asc"))
        h = hwc_signer.sign("GET", url, {"Content-Type": "application/json"}, "", "MYAK", "MYSK", now)
        self.assertTrue(h["Authorization"].endswith("dfb8e6c558329ed7619c74933b115ee6ca8a5bf1cff2b0619ac26522046adf89"))


class TestCommands(unittest.TestCase):
    def setUp(self):
        self.data = [
            coupon("A1", expire="2026-11-10T00:00:00Z"),                       # 7 天后到期
            coupon("A2", expire="2027-03-01T00:00:00Z", balance=100.0),        # 远期
            coupon("A3", status=3, balance=0.0),                               # 已使用
            coupon("A4", status=4, balance=30.0, expire="2026-10-01T00:00:00Z"),  # 已过期
            coupon("D1", ctype=2),                                             # 折扣券
        ]

    def test_list_json_with_domain_header_and_signature(self):
        http = FakeHttp(self.data)
        code, out, _ = run(["--json", "list"], http)
        self.assertEqual(code, 0)
        body = json.loads(out)
        self.assertEqual(body["count"], 4)  # 默认只看代金券
        url, headers = http.calls[-1]
        self.assertIn("/v2/promotions/benefits/coupons?coupon_type=1&limit=100&offset=0", url)
        self.assertEqual(headers["X-Domain-Id"], "d" * 32)
        self.assertTrue(headers["Authorization"].startswith("SDK-HMAC-SHA256 Access=AK, SignedHeaders=content-type;host;x-domain-id;x-sdk-date"))

    def test_list_filter_status_and_masked_text(self):
        code, out, _ = run(["list", "--status", "available"], FakeHttp(self.data))
        self.assertEqual(code, 0)
        self.assertIn("待使用", out)
        self.assertNotIn("已使用", out)

    def test_pagination(self):
        many = [coupon(f"P{i:03d}") for i in range(250)]
        http = FakeHttp(many)
        code, out, _ = run(["--json", "list"], http)
        self.assertEqual(json.loads(out)["count"], 250)
        self.assertEqual(sum("/v2/promotions" in u for u, _ in http.calls), 3)

    def test_status_found_and_not_found(self):
        code, out, _ = run(["--json", "status", "A2"], FakeHttp(self.data))
        self.assertEqual((code, json.loads(out)["balance"]), (0, 100.0))
        code, _, err = run(["status", "ZZ"], FakeHttp(self.data))
        self.assertEqual(code, cq.EXIT_API)
        self.assertIn("NOT_FOUND", err)

    def test_expiring(self):
        code, out, _ = run(["--json", "expiring", "--days", "30"], FakeHttp(self.data))
        body = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual([c["coupon_id"] for c in body["coupons"]], ["A1"])
        self.assertEqual(body["coupons"][0]["days_left"], 7)

    def test_usage(self):
        code, out, _ = run(["--json", "usage"], FakeHttp(self.data))
        s = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(s["face_value_total"], 400.0)
        self.assertEqual(s["balance_total"], 190.0)
        self.assertEqual(s["used_total"], 210.0)
        self.assertEqual(s["usage_rate"], 0.525)
        self.assertEqual(s["expired_unused_balance"], 30.0)

    def test_usage_text(self):
        code, out, _ = run(["usage"], FakeHttp(self.data))
        self.assertIn("使用率：52.5%", out)


class TestErrors(unittest.TestCase):
    def test_missing_credentials_exit_3_and_no_request(self):
        http = FakeHttp([])
        code, _, err = run(["list"], http, env={})
        self.assertEqual(code, cq.EXIT_CONFIG)
        self.assertIn("MISSING_CONFIG", err)
        self.assertEqual(http.calls, [])

    def test_bad_args_exit_2(self):
        self.assertEqual(run(["list", "--status", "foo"], FakeHttp([]))[0], cq.EXIT_ARGS)
        self.assertEqual(run(["expiring", "--days", "0"], FakeHttp([]))[0], cq.EXIT_ARGS)
        self.assertEqual(run([], FakeHttp([]))[0], cq.EXIT_ARGS)

    def test_api_error_passthrough(self):
        http = FakeHttp([], status=403, body=json.dumps({"error_code": "CBC.0151", "error_msg": "Access denied."}))
        code, out, err = run(["--json", "list"], http)
        self.assertEqual(code, cq.EXIT_API)
        e = json.loads(out)["error"]
        self.assertEqual((e["http_status"], e["error_code"]), (403, "CBC.0151"))
        self.assertIn("bss:coupon:view", err)

    def test_network_error_exit_5(self):
        def boom(url, headers):
            raise cq.CouponError("NETWORK_ERROR", "网络异常：timed out", cq.EXIT_NETWORK)
        self.assertEqual(run(["list"], boom)[0], cq.EXIT_NETWORK)

    def test_secrets_never_printed(self):
        env = {"HUAWEICLOUD_SDK_AK": "AKSECRET123", "HUAWEICLOUD_SDK_SK": "SKSECRET456"}
        http = FakeHttp([], status=401, body=json.dumps({"error_code": "APIGW.0301", "error_msg": "auth"}))
        code, out, err = run(["--json", "list"], http, env=env)
        self.assertNotIn("SKSECRET456", out + err)
        self.assertNotIn("AKSECRET123", out + err)


class TestPure(unittest.TestCase):
    def test_mask(self):
        self.assertEqual(cq.mask("1234567890abcdef"), "1234****cdef")
        self.assertEqual(cq.mask(None), "-")

    def test_old_coupon_without_balance_excluded_from_rate(self):
        cs = [cq.normalize(coupon("X", balance=None)), cq.normalize(coupon("Y", face=50, balance=25))]
        s = cq.analyze_usage(cs)
        self.assertEqual((s["excluded_without_balance"], s["usage_rate"]), (1, 0.5))


if __name__ == "__main__":
    unittest.main()

"""华为云 API 网关 AK/SK 签名（SDK-HMAC-SHA256），仅依赖 Python 标准库。

签名流程：
  CanonicalRequest = Method \\n CanonicalURI \\n CanonicalQuery \\n CanonicalHeaders \\n SignedHeaders \\n SHA256(Body)
  StringToSign     = "SDK-HMAC-SHA256" \\n X-Sdk-Date \\n SHA256(CanonicalRequest)
  Signature        = HMAC-SHA256(SK, StringToSign)
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import hmac
from urllib.parse import quote, unquote, urlsplit, parse_qsl

ALGORITHM = "SDK-HMAC-SHA256"


def rfc3986(value: str) -> str:
    return quote(str(value), safe="-_.~")


def sdk_date(now: _dt.datetime | None = None) -> str:
    now = now or _dt.datetime.now(_dt.timezone.utc)
    return now.strftime("%Y%m%dT%H%M%SZ")


def canonical_uri(path: str) -> str:
    encoded = "/".join(rfc3986(unquote(seg)) for seg in path.split("/"))
    return encoded if encoded.endswith("/") else encoded + "/"


def canonical_query(pairs: list[tuple[str, str]]) -> str:
    items = sorted((rfc3986(k), rfc3986(v)) for k, v in pairs)
    return "&".join(f"{k}={v}" for k, v in items)


def sign(method: str, url: str, headers: dict[str, str], body: str, ak: str, sk: str,
         now: _dt.datetime | None = None) -> dict[str, str]:
    """返回加上 X-Sdk-Date 与 Authorization 的新请求头。"""
    parts = urlsplit(url)
    out = dict(headers)
    out["X-Sdk-Date"] = sdk_date(now)
    lower = {"host": parts.netloc}
    for k, v in out.items():
        lower[k.lower()] = str(v).strip()
    names = sorted(lower)
    canonical_headers = "".join(f"{n}:{lower[n]}\n" for n in names)
    signed_headers = ";".join(names)
    canonical_request = "\n".join([
        method.upper(),
        canonical_uri(parts.path or "/"),
        canonical_query(parse_qsl(parts.query, keep_blank_values=True)),
        canonical_headers,
        signed_headers,
        hashlib.sha256(body.encode("utf-8")).hexdigest(),
    ])
    string_to_sign = "\n".join([ALGORITHM, out["X-Sdk-Date"],
                                hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()])
    signature = hmac.new(sk.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    out["Authorization"] = f"{ALGORITHM} Access={ak}, SignedHeaders={signed_headers}, Signature={signature}"
    return out

# -*- coding: utf-8 -*-
"""Mako resolver — pure-Python AES, works on any Kodi."""
import os
import re
import json
import base64
import sys

# Make sibling modules importable
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from mini_aes import cbc_encrypt as _enc_aes, cbc_decrypt as _dec_aes

try:
    import requests
    _HAVE_REQUESTS = True
except ImportError:
    import urllib.request
    import http.cookiejar
    _HAVE_REQUESTS = False


UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

LIVE_URL = ("https://www.mako.co.il/news-channel2/"
            "Channel-2-Newscast-q3_2019/"
            "Article-3bf5c3a8e967f51006.htm")

EMBED_RE = re.compile(
    r"player-embed/\?vid=([^&\"']+)&cid=([^&\"']+)&galleryCid=([^&\"']+)")

KEY    = b"YhnUaXMmltB6gd8p9SWleQ=="
IV     = b"theExact16Chars="[:16]
ENT    = "https://mass.mako.co.il/ClicksStatistics/entitlementsServicesV2.jsp?et=egt"
ORIGIN = "https://www.mako.co.il"


def _log(log, m):
    try:
        log("[mako] " + m)
    except Exception:
        pass


def _enc(pt):
    return base64.b64encode(_enc_aes(KEY, IV, pt.encode("utf-8"))).decode()


def _dec(ct):
    return _dec_aes(KEY, IV, base64.b64decode(ct)).decode("utf-8")


def _http_get(url, headers=None, timeout=20):
    h = {"User-Agent": UA, "Accept-Language": "he-IL,he;q=0.9,en;q=0.8"}
    if headers:
        h.update(headers)
    if _HAVE_REQUESTS:
        r = requests.get(url, headers=h, timeout=timeout)
        r.raise_for_status()
        return r.text
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def _http_post(url, data, headers=None, timeout=20):
    h = {"User-Agent": UA, "Accept-Language": "he-IL,he;q=0.9,en;q=0.8"}
    if headers:
        h.update(headers)
    if _HAVE_REQUESTS:
        r = requests.post(url, data=data, headers=h, timeout=timeout)
        r.raise_for_status()
        return r.text
    if isinstance(data, str):
        data = data.encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=h, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def _ids(html):
    m = EMBED_RE.search(html)
    if not m:
        raise RuntimeError("player-embed not found")
    return m.group(1), m.group(2), m.group(3)


def _mobile(v, c, g):
    u = ("https://mobile.mako.co.il/AjaxPage?jspName=playlist.jsp"
         f"&vcmid={v}&videoChannelId={c}&galleryChannelId={g}"
         "&isGallery=false&consumer=android4&encryption=no&appId=mako")
    txt = _http_get(u, {"Referer": ORIGIN + "/"})
    return json.loads(txt)


def _ticket(v, murl, cdn):
    lp = re.sub(r"^https?://[^/]+", "", murl)
    payload = json.dumps({"lp": lp, "rv": cdn or "AKAMAI",
                          "du": "undefined", "dv": v, "na": "1.0.1"},
                         separators=(",", ":"))
    body = _http_post(ENT, _enc(payload),
                      {"Content-Type": "text/plain;charset=UTF-8",
                       "Origin": ORIGIN,
                       "Referer": ORIGIN + "/"})
    b = body.strip()
    if b.startswith("hvidt"):
        b = b[5:]
    return json.loads(_dec(b))["tickets"][0]["ticket"]


def _pick(ms):
    for m in ms:
        if m.get("format") == "AKAMAI_HLS" and ".m3u8" in (m.get("url") or ""):
            return m
    for m in ms:
        if ".m3u8" in (m.get("url") or ""):
            return m
    return None


def resolve(article_url, log=None):
    log = log or (lambda m: None)
    _log(log, "Fetching " + article_url)
    html = _http_get(article_url, {"Referer": ORIGIN})
    v, c, g = _ids(html)
    data = _mobile(v, c, g)
    media = data.get("media") or []
    if not media:
        raise RuntimeError("no media")
    title = (data.get("videoDetails") or {}).get("title") or "Mako Stream"
    chosen = _pick(media)
    if not chosen:
        raise RuntimeError("no m3u8")
    url = chosen["url"]
    tk = _ticket(v, url, chosen.get("cdn") or "AKAMAI")
    sep = "&" if "?" in url else "?"
    final = url + sep + tk
    _log(log, "Ready ({0} chars)".format(len(final)))
    return final, title

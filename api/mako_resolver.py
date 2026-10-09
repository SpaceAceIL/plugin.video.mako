# -*- coding: utf-8 -*-
"""Mako stream resolver. Made by SpaceAce - space@anan.media."""
import os, re, json, base64, requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

EMBED_RE = re.compile(r"player-embed/\?vid=([^&"']+)&cid=([^&"']+)&galleryCid=([^&"']+)")

KEY    = b"YhnUaXMmltB6gd8p9SWleQ=="
IV     = b"theExact16Chars="[:16]
ENT    = "https://mass.mako.co.il/ClicksStatistics/entitlementsServicesV2.jsp?et=egt"
ORIGIN = "https://www.mako.co.il"
NA     = "1.0.1"


def _enc(pt):
    return base64.b64encode(
        AES.new(KEY, AES.MODE_CBC, IV).encrypt(pad(pt.encode(), 16))).decode()


def _dec(ct):
    return unpad(
        AES.new(KEY, AES.MODE_CBC, IV).decrypt(base64.b64decode(ct)), 16).decode()


def _sess():
    s = requests.Session()
    s.headers.update({"User-Agent": UA,
                      "Accept-Language": "he-IL,he;q=0.9,en;q=0.8",
                      "Origin": ORIGIN})
    return s


def _ids(html):
    m = EMBED_RE.search(html)
    if not m: raise RuntimeError("player-embed not found")
    return m.group(1), m.group(2), m.group(3)


def _mobile(s, v, c, g):
    u = ("https://mobile.mako.co.il/AjaxPage?jspName=playlist.jsp"
         f"&vcmid={v}&videoChannelId={c}&galleryChannelId={g}"
         "&isGallery=false&consumer=android4&encryption=no&appId=mako")
    r = s.get(u, timeout=20); r.raise_for_status()
    return r.json()


def _ticket(s, v, murl, cdn):
    lp = re.sub(r"^https?://[^/]+", "", murl)
    payload = json.dumps({"lp": lp, "rv": cdn or "AKAMAI",
                          "du": "undefined", "dv": v, "na": NA},
                         separators=(",", ":"))
    r = s.post(ENT, data=_enc(payload),
               headers={"Content-Type": "text/plain;charset=UTF-8"},
               timeout=20)
    r.raise_for_status()
    b = r.text.strip()
    if b.startswith("hvidt"): b = b[5:]
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
    s = _sess()
    log(f"fetch {article_url}")
    html = s.get(article_url, timeout=20).text
    v, c, g = _ids(html)
    data = _mobile(s, v, c, g)
    media = data.get("media") or []
    if not media: raise RuntimeError("no media")
    title = (data.get("videoDetails") or {}).get("title") or "Mako Stream"
    chosen = _pick(media)
    if not chosen: raise RuntimeError("no m3u8")
    url = chosen["url"]
    tk = _ticket(s, v, url, chosen.get("cdn") or "AKAMAI")
    sep = "&" if "?" in url else "?"
    final = url + sep + tk
    m = re.search(r"exp(?:%3D|=)(\d{9,11})", final, re.I)
    return {"url": final, "title": title,
            "expiry_unix": int(m.group(1)) if m else 0,
            "media_format": chosen.get("format"),
            "cdn": chosen.get("cdn") or "AKAMAI"}


if __name__ == "__main__":
    import sys
    t = sys.argv[1] if len(sys.argv) > 1 else (
        "https://www.mako.co.il/news-channel2/Channel-2-Newscast-q3_2019/"
        "Article-3bf5c3a8e967f51006.htm")
    print(json.dumps(resolve(t, log=print), indent=2, ensure_ascii=False))

# -*- coding: utf-8 -*-
"""Mako EPG — works with or without requests."""
import os
import json
import time

try:
    import requests
    _HAVE_REQUESTS = True
except ImportError:
    import urllib.request
    _HAVE_REQUESTS = False

EPG_URL = "https://www.mako.co.il/AjaxPage?jspName=EPGResponse.jsp"
SCHEDULE = "https://www.mako.co.il/tv-tv-schedule"
CACHE_TTL = 300
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def _cache_path():
    try:
        import xbmcaddon
        d = xbmcaddon.Addon().getAddonInfo("profile")
    except Exception:
        d = "/tmp"
    if not os.path.isdir(d):
        try:
            os.makedirs(d, exist_ok=True)
        except Exception:
            pass
    return os.path.join(d, "epg_cache.json")


def _fetch(force=False):
    headers = {"User-Agent": UA,
               "Referer": SCHEDULE,
               "X-Requested-With": "XMLHttpRequest",
               "Accept": "application/json, text/javascript, */*; q=0.01"}
    if _HAVE_REQUESTS:
        s = requests.Session()
        s.headers.update({"User-Agent": UA,
                          "Accept-Language": "he-IL,he;q=0.9,en;q=0.8"})
        try:
            s.get(SCHEDULE, timeout=15)
        except Exception:
            pass
        r = s.get(EPG_URL, headers=headers, timeout=20)
        return r.text or ""
    # urllib fallback
    req0 = urllib.request.Request(
        SCHEDULE, headers={"User-Agent": UA,
                           "Accept-Language": "he-IL,he;q=0.9"})
    try:
        urllib.request.urlopen(req0, timeout=15).read()
    except Exception:
        pass
    req = urllib.request.Request(EPG_URL, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", "replace")


def fetch_epg(force=False, log=None):
    log = log or (lambda m: None)
    cache = _cache_path()
    if not force and os.path.exists(cache):
        try:
            if time.time() - os.path.getmtime(cache) < CACHE_TTL:
                with open(cache, encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
    log("[mako-epg] fetching EPGResponse.jsp")
    txt = _fetch(force=force)
    if not txt.strip():
        raise RuntimeError("empty EPG response")
    data = json.loads(txt)
    out = []
    for p in data.get("programs", []):
        out.append({
            "title":       p.get("ProgramName", ""),
            "description": p.get("EventDescription", ""),
            "start_ms":    int(p.get("StartTimeUTC") or 0),
            "duration_ms": int(p.get("DurationMs") or 0),
            "picture":     p.get("Picture") or p.get("MobilePicture") or "",
            "is_live":     bool(p.get("LiveBroadcast")),
            "is_rerun":    bool(p.get("RerunBroadcast")),
            "mako_url":    p.get("MakoTVURL", ""),
            "program_code": p.get("ProgramCode"),
        })
    out.sort(key=lambda x: x["start_ms"])
    try:
        with open(cache, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False)
    except Exception:
        pass
    log("[mako-epg] got {0} programs".format(len(out)))
    return out


def currently_airing(programs, at_ms=None):
    at = at_ms if at_ms is not None else int(time.time() * 1000)
    for p in programs:
        if p["start_ms"] <= at < p["start_ms"] + p["duration_ms"]:
            return p
    return None


def upcoming(programs, within_hours=24, at_ms=None):
    at = at_ms if at_ms is not None else int(time.time() * 1000)
    horizon = at + within_hours * 3600 * 1000
    return [p for p in programs if at <= p["start_ms"] < horizon]


def fmt_time(ms):
    return time.strftime("%H:%M", time.localtime(ms / 1000.0))


def fmt_day(ms):
    return time.strftime("%a %d/%m", time.localtime(ms / 1000.0))

# -*- coding: utf-8 -*-
"""Mako EPG — parses EPGResponse.jsp."""
import os, json, time, requests

EPG_URL   = "https://www.mako.co.il/AjaxPage?jspName=EPGResponse.jsp"
CACHE_TTL = 300   # 5 min
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def _cache_path():
    try:
        import xbmcaddon
        d = xbmcaddon.Addon().getAddonInfo("profile")
    except Exception:
        d = "/tmp"
    if not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    return os.path.join(d, "epg_cache.json")


def fetch_epg(force=False, log=None):
    """Return list of program dicts sorted by start time."""
    log = log or (lambda m: None)
    cache = _cache_path()
    if not force and os.path.exists(cache):
        if time.time() - os.path.getmtime(cache) < CACHE_TTL:
            try:
                with open(cache, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    log("[mako-epg] fetching EPGResponse.jsp")
    r = requests.get(EPG_URL, timeout=20,
                     headers={"User-Agent": UA,
                              "Referer": "https://www.mako.co.il/tv-tv-schedule"})
    r.raise_for_status()
    data = r.json()
    out = []
    for p in data.get("programs", []):
        out.append({
            "title":        p.get("ProgramName", ""),
            "description":  p.get("EventDescription", ""),
            "start_ms":     int(p.get("StartTimeUTC") or 0),
            "duration_ms":  int(p.get("DurationMs") or 0),
            "picture":      p.get("Picture") or p.get("MobilePicture") or "",
            "is_live":      bool(p.get("LiveBroadcast")),
            "is_rerun":     bool(p.get("RerunBroadcast")),
            "mako_url":     p.get("MakoTVURL", ""),
            "program_code": p.get("ProgramCode"),
        })
    out.sort(key=lambda x: x["start_ms"])
    try:
        with open(cache, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False)
    except Exception:
        pass
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

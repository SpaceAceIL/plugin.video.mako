# -*- coding: utf-8 -*-
"""Mako Live — Made by SpaceAce (space@anan.media)."""
import os, sys
from urllib.parse import parse_qsl, unquote, quote
import xbmc, xbmcgui, xbmcplugin, xbmcaddon

_ADDON = xbmcaddon.Addon()
_LIB = os.path.join(_ADDON.getAddonInfo("path"), "resources", "lib")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

from resources.lib.mako import resolve, LIVE_URL
from resources.lib import epg, recorder

HANDLE  = int(sys.argv[1]) if len(sys.argv) > 1 else -1
BASEURL = sys.argv[0] if sys.argv else ""
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

POPUP_TITLE   = "Mako Live"
POPUP_MESSAGE = "Streaming Channel 12 live.\n\nMade by SpaceAce"


def url(**params):
    return BASEURL + "?" + "&".join(
        "{0}={1}".format(k, quote(str(v), safe="")) for k, v in params.items())


def add_dir(label, params, icon=None):
    li = xbmcgui.ListItem(label=label)
    if icon:
        li.setArt({"thumb": icon, "icon": icon})
    xbmcplugin.addDirectoryItem(HANDLE, url(**params), li, isFolder=True)


def add_playable(label, params, icon=None, plot=""):
    li = xbmcgui.ListItem(label=label)
    li.setInfo("video", {"title": label, "plot": plot})
    if icon:
        li.setArt({"thumb": icon, "icon": icon})
    xbmcplugin.addDirectoryItem(HANDLE, url(**params), li, isFolder=False)


def _play(stream_url):
    li = xbmcgui.ListItem(path=stream_url)
    li.setMimeType("application/vnd.apple.mpegurl")
    li.setProperty("inputstream", "inputstream.adaptive")
    li.setProperty("inputstream.adaptive.manifest_type", "hls")
    li.setProperty("inputstream.adaptive.stream_headers",
                   "User-Agent={0}&Referer=https://www.mako.co.il/".format(UA))
    xbmcplugin.setResolvedUrl(HANDLE, True, li)


def _resolve_play(article):
    pd = xbmcgui.DialogProgress(); pd.create("Mako Live", "Resolving...")
    try:
        pd.update(30, "Fetching...")
        s, _ = resolve(article, log=xbmc.log)
        pd.update(90, "Playing...")
        pd.close()
        _play(s)
    except Exception as e:
        xbmc.log("[mako] " + str(e), xbmc.LOGERROR)
        xbmcgui.Dialog().notification("Mako Live", str(e),
                                      xbmcgui.NOTIFICATION_ERROR, 6000)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        try: pd.close()
        except: pass


def _record_now(article, program_title, duration_min):
    """Schedule a recording that starts immediately."""
    try:
        stream, _ = resolve(article, log=xbmc.log)
    except Exception as e:
        xbmcgui.Dialog().notification("Mako", "Resolve failed: {0}".format(e),
                                      xbmcgui.NOTIFICATION_ERROR, 6000)
        return
    now = int(__import__("time").time())
    end = now + int(duration_min) * 60
    recorder.add_timer(program_title, now, end, stream, "")
    xbmcgui.Dialog().notification(
        "Mako Recording",
        "Recording {0} for {1} min".format(program_title[:30], duration_min),
        xbmcgui.NOTIFICATION_INFO, 5000)


def _schedule_recording(program):
    """Schedule a future program."""
    import time as _t
    start_unix = program["start_ms"] // 1000
    end_unix   = (program["start_ms"] + program["duration_ms"]) // 1000
    # resolve live URL now (valid ~15 min) — the timer will fetch fresh at start
    recorder.add_timer(program["title"], start_unix, end_unix, LIVE_URL, "")
    xbmcgui.Dialog().notification(
        "Mako Scheduled",
        "Will record {0} at {1}".format(
            program["title"][:30], epg.fmt_time(program["start_ms"])),
        xbmcgui.NOTIFICATION_INFO, 6000)


# ---------------------------------------------------------------- menus

def main_menu():
    add_dir("\u05e2\u05e8\u05d5\u05e5 12 \u05d1\u05dc\u05d9\u05d9\u05d5 \u2013 Live Now",
            {"mode": "live"})
    add_dir("TV Guide  \u2013 \u05dc\u05d5\u05d7 \u05e9\u05d9\u05d3\u05d5\u05e8\u05d9\u05dd",
            {"mode": "guide"})
    add_dir("Scheduled Recordings",
            {"mode": "timers"})
    xbmcplugin.endOfDirectory(HANDLE)


def guide():
    try:
        programs = epg.fetch_epg(log=xbmc.log)
    except Exception as e:
        xbmcgui.Dialog().notification("Mako EPG", str(e),
                                      xbmcgui.NOTIFICATION_ERROR, 6000)
        xbmcplugin.endOfDirectory(HANDLE)
        return

    now_ms = int(__import__("time").time() * 1000)
    # Show a window: previous 2h through next 24h
    items = [p for p in programs
             if p["start_ms"] + p["duration_ms"] > now_ms - 7200000
             and p["start_ms"] < now_ms + 24 * 3600 * 1000]

    for p in items:
        is_now = p["start_ms"] <= now_ms < p["start_ms"] + p["duration_ms"]
        label = "{0}  {1}-{2}  {3}".format(
            "\u25b6" if is_now else "  ",
            epg.fmt_time(p["start_ms"]),
            epg.fmt_time(p["start_ms"] + p["duration_ms"]),
            p["title"])
        plot = "{0}\n\n{1}-{2}".format(
            p["description"],
            epg.fmt_time(p["start_ms"]),
            epg.fmt_time(p["start_ms"] + p["duration_ms"]))
        add_playable(label,
                     {"mode": "program",
                      "title": p["title"][:80],
                      "start_ms": p["start_ms"],
                      "dur_ms": p["duration_ms"],
                      "live": 1 if is_now else 0},
                     icon=p["picture"], plot=plot)
    xbmcplugin.endOfDirectory(HANDLE)


def program_actions(title, start_ms, dur_ms, is_now):
    options = []
    if is_now:
        options.append("\u25b6 Watch Live Now")
        options.append("\u23fa Record Now")
    if start_ms > int(__import__("time").time() * 1000):
        options.append("\U0001f4c5 Schedule Recording")
    options.append("Info")

    ch = xbmcgui.Dialog().select(title, options)
    if ch < 0:
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return
    choice = options[ch]

    if "Watch" in choice:
        _resolve_play(LIVE_URL)
    elif "Record Now" in choice:
        kb = xbmcgui.Dialog().numeric(0, "Minutes to record", "60")
        try:
            mins = int(kb) if kb else 60
        except ValueError:
            mins = 60
        _record_now(LIVE_URL, title, mins)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
    elif "Schedule" in choice:
        _schedule_recording({"title": title,
                             "start_ms": start_ms,
                             "duration_ms": dur_ms})
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
    else:
        xbmcgui.Dialog().textviewer(title, "Starts at " + epg.fmt_time(start_ms) +
                                    "\nEnds at " + epg.fmt_time(start_ms + dur_ms))
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())


def timers():
    items = recorder.load_timers()
    active = {a["id"]: a for a in recorder.load_active()}
    for t in items:
        if t.get("status") == "done":
            label = "[DONE] {0}  {1}".format(
                t.get("title", "?"),
                __import__("time").strftime(
                    "%d/%m %H:%M", __import__("time").localtime(t["start_unix"])))
        elif t.get("id") in active:
            label = "[REC] {0}".format(t.get("title", "?"))
        else:
            label = "[{0}] {1}  {2}".format(
                t.get("status", "?"),
                t.get("title", "?"),
                __import__("time").strftime(
                    "%d/%m %H:%M", __import__("time").localtime(t["start_unix"])))
        li = xbmcgui.ListItem(label=label)
        xbmcplugin.addDirectoryItem(HANDLE, url(mode="del_timer", tid=t["id"]),
                                     li, isFolder=False)
    xbmcplugin.endOfDirectory(HANDLE)


def del_timer(tid):
    recorder.remove_timer(tid)
    xbmcgui.Dialog().notification("Mako", "Timer removed",
                                  xbmcgui.NOTIFICATION_INFO, 3000)
    xbmcplugin.endOfDirectory(HANDLE)


# ---------------------------------------------------------------- router

def main():
    params = dict(parse_qsl(sys.argv[2][1:])) if len(sys.argv) > 2 else {}
    mode = params.get("mode", "root")

    if mode == "root":
        main_menu()
    elif mode == "live":
        _resolve_play(LIVE_URL)
    elif mode == "guide":
        guide()
    elif mode == "program":
        program_actions(params.get("title", ""),
                        int(params.get("start_ms", 0)),
                        int(params.get("dur_ms", 0)),
                        params.get("live", "0") == "1")
    elif mode == "timers":
        timers()
    elif mode == "del_timer":
        del_timer(params.get("tid", ""))
    else:
        main_menu()


if __name__ == "__main__":
    main()

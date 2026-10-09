# -*- coding: utf-8 -*-
"""Israeli TV — channels, EPG, recording. Made by SpaceAce."""
import os, sys, time
from urllib.parse import parse_qsl, quote
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
WORKER = "https://mako-live.spacestangs.workers.dev/live.m3u8"

CHANNELS = [
    {"name": "Kan 11",          "type": "direct",
     "url": "https://kancdn.medonecdn.net/livehls/oil/kancdn-live/live/kan11/live.livx/playlist.m3u8",
     "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c8/Kan11Logo.svg/500px-Kan11Logo.svg.png"},
    {"name": "Keshet 12",       "type": "direct",
     "url": WORKER,
     "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f0/Keshet12_2018.svg/960px-Keshet12_2018.svg.png"},
    {"name": "Channel 13",      "type": "direct",
     "url": "https://d2xg1g9o5vns8m.cloudfront.net/out/v1/0855d703f7d5436fae6a9c7ce8ca5075/index.m3u8",
     "logo": "https://upload.wikimedia.org/wikipedia/he/thumb/1/17/Reshet13Logo2022.svg/500px-Reshet13Logo2022.svg.png"},
    {"name": "Channel 14",      "type": "direct",
     "url": "https://r.il.cdn-redge.media/livehls/oil/ch14/live/ch14/live.livx/playlist.m3u8",
     "logo": "https://i.imgur.com/Iq2Kb69.png"},
    {"name": "Makan 33",        "type": "direct",
     "url": "https://kancdn.medonecdn.net/livehls/oil/kancdn-live/live/makan/live.livx/playlist.m3u8",
     "logo": "https://upload.wikimedia.org/wikipedia/en/5/56/MeKan_33_logo_2017.png"},
    {"name": "Kan Educational", "type": "direct",
     "url": "http://stream.mcquack.net/378/index.m3u8",
     "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6b/KanHinuchit.svg/500px-KanHinuchit.svg.png"},
    {"name": "Knesset",         "type": "direct",
     "url": "http://stream.mcquack.net/48/index.m3u8",
     "logo": ""},
]


def he(s):
    if not s:
        return s
    if any("\u0590" <= c <= "\u05ff" for c in s):
        return "\u200f" + s
    return s


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
                   "User-Agent={0}".format(UA))
    if HANDLE >= 0:
        try:
            xbmcplugin.setResolvedUrl(HANDLE, True, li)
            return
        except Exception:
            pass
    xbmc.Player().play(stream_url, li)
    xbmc.sleep(3000)
    xbmcgui.Dialog().notification("Israeli TV", "Playing. Ctrl+R to record.",
                                  xbmcgui.NOTIFICATION_INFO, 4000)


def main_menu():
    for i, ch in enumerate(CHANNELS):
        li = xbmcgui.ListItem(label=ch["name"])
        if ch.get("logo"):
            li.setArt({"thumb": ch["logo"], "icon": ch["logo"]})
        xbmcplugin.addDirectoryItem(HANDLE, url(mode="play", idx=i),
                                    li, isFolder=False)
    add_dir("📺  TV Guide", {"mode": "guide"})
    add_dir("⏺  Scheduled Recordings", {"mode": "timers"})
    xbmcplugin.endOfDirectory(HANDLE)


def tv_guide():
    try:
        programs = epg.fetch_epg(log=xbmc.log)
    except Exception as e:
        xbmcgui.Dialog().notification("EPG", str(e),
                                      xbmcgui.NOTIFICATION_ERROR, 5000)
        xbmcplugin.endOfDirectory(HANDLE)
        return

    now_ms = int(time.time() * 1000)
    for p in programs:
        if not (p["start_ms"] + p["duration_ms"] > now_ms - 7200000 and
                p["start_ms"] < now_ms + 24 * 3600 * 1000):
            continue
        is_now = p["start_ms"] <= now_ms < p["start_ms"] + p["duration_ms"]
        marker = "▶" if is_now else "  "
        label = "{0}  {1}-{2}  {3}".format(
            marker,
            epg.fmt_time(p["start_ms"]),
            epg.fmt_time(p["start_ms"] + p["duration_ms"]),
            he(p["title"]))
        plot = "{0}\n\n{1}-{2}".format(
            he(p["description"]),
            epg.fmt_time(p["start_ms"]),
            epg.fmt_time(p["start_ms"] + p["duration_ms"]))
        add_dir(label,
                {"mode": "program",
                 "title": p["title"][:80],
                 "start_ms": p["start_ms"],
                 "dur_ms": p["duration_ms"],
                 "live": 1 if is_now else 0},
                icon=p["picture"])
    xbmcplugin.endOfDirectory(HANDLE)


def program_menu(title, start_ms, dur_ms, is_now):
    if is_now:
        add_playable("▶  Watch Live Now", {"mode": "play_worker"}, plot=he(title))
        add_playable("⏺  Record Current Stream…",
                     {"mode": "record_now", "title": title},
                     plot="Asks for minutes, then records")
    else:
        add_playable("📅  Schedule Recording",
                     {"mode": "schedule",
                      "title": title,
                      "start_ms": start_ms,
                      "dur_ms": dur_ms},
                     plot="Timer starts at " + epg.fmt_time(start_ms))
    add_playable("ℹ  Program Info",
                 {"mode": "program_info",
                  "title": title,
                  "start_ms": start_ms,
                  "dur_ms": dur_ms})
    xbmcplugin.endOfDirectory(HANDLE)


def program_info(title, start_ms, dur_ms):
    body = "Title: {0}\n\nStart: {1}\nEnd:   {2}\n\nDuration: {3} min".format(
        he(title),
        time.strftime("%a %d/%m %H:%M", time.localtime(start_ms / 1000.0)),
        time.strftime("%a %d/%m %H:%M",
                      time.localtime((start_ms + dur_ms) / 1000.0)),
        int(dur_ms / 60000))
    xbmcgui.Dialog().textviewer("Program Info", body)
    xbmcplugin.endOfDirectory(HANDLE)


def schedule_recording(title, start_ms, dur_ms):
    try:
        recorder.add_timer(title,
                           int(start_ms / 1000),
                           int((start_ms + dur_ms) / 1000),
                           WORKER, "")
        xbmcgui.Dialog().notification(
            "Scheduled",
            "{0} at {1}".format(title[:30], epg.fmt_time(start_ms)),
            xbmcgui.NOTIFICATION_INFO, 6000)
    except Exception as e:
        xbmcgui.Dialog().notification("Israeli TV", str(e),
                                      xbmcgui.NOTIFICATION_ERROR, 5000)
    xbmcplugin.endOfDirectory(HANDLE)


def record_now(title):
    kb = xbmcgui.Dialog().numeric(0, "Minutes to record", "60")
    if not kb:
        xbmcplugin.endOfDirectory(HANDLE); return
    try:
        mins = int(kb)
    except ValueError:
        mins = 60
    now = int(time.time())
    recorder.add_timer(title or "Live Capture", now, now + mins * 60, WORKER, "")
    xbmcgui.Dialog().notification("Recording",
                                  "Recording for {0} min".format(mins),
                                  xbmcgui.NOTIFICATION_INFO, 6000)
    xbmcplugin.endOfDirectory(HANDLE)


def record_current_stream():
    try:
        u = xbmc.Player().getPlayingFile() or ""
    except Exception:
        u = ""
    if "mako" not in u and "workers.dev" not in u:
        xbmcgui.Dialog().notification("Israeli TV", "No stream playing",
                                      xbmcgui.NOTIFICATION_WARNING, 4000)
        return
    kb = xbmcgui.Dialog().numeric(0, "Minutes to record", "60")
    if not kb:
        return
    try:
        mins = int(kb)
    except ValueError:
        mins = 60
    now = int(time.time())
    recorder.add_timer("Live Capture", now, now + mins * 60, u, "")
    xbmcgui.Dialog().notification("Recording",
                                  "Recording for {0} min".format(mins),
                                  xbmcgui.NOTIFICATION_INFO, 6000)


def timers():
    items = recorder.load_timers()
    active = {a["id"]: a for a in recorder.load_active()}
    if not items:
        add_dir("(no scheduled recordings)", {"mode": "root"})
        xbmcplugin.endOfDirectory(HANDLE); return
    for t in items:
        status = t.get("status", "?")
        if status == "done":
            prefix = "[DONE] "
        elif t.get("id") in active:
            prefix = "[REC] "
        else:
            prefix = "[{0}] ".format(status)
        label = prefix + "{0}  {1}".format(
            he(t.get("title", "?")),
            time.strftime("%d/%m %H:%M",
                          time.localtime(t["start_unix"])))
        li = xbmcgui.ListItem(label=label)
        xbmcplugin.addDirectoryItem(
            HANDLE, url(mode="del_timer", tid=t["id"]), li, isFolder=False)
    xbmcplugin.endOfDirectory(HANDLE)


def del_timer(tid):
    recorder.remove_timer(tid)
    xbmcgui.Dialog().notification("Israeli TV", "Timer removed",
                                  xbmcgui.NOTIFICATION_INFO, 3000)
    xbmcplugin.endOfDirectory(HANDLE)


def main():
    params = dict(parse_qsl(sys.argv[2][1:])) if len(sys.argv) > 2 else {}
    mode = params.get("mode", "root")

    if mode == "root":
        main_menu()
    elif mode == "play":
        try:
            ch = CHANNELS[int(params.get("idx", "0"))]
            _play(ch["url"])
        except (ValueError, IndexError):
            pass
    elif mode == "play_worker":
        _play(WORKER)
    elif mode == "guide":
        tv_guide()
    elif mode == "program":
        program_menu(params.get("title", ""),
                     int(params.get("start_ms", 0)),
                     int(params.get("dur_ms", 0)),
                     params.get("live", "0") == "1")
    elif mode == "program_info":
        program_info(params.get("title", ""),
                     int(params.get("start_ms", 0)),
                     int(params.get("dur_ms", 0)))
    elif mode == "schedule":
        schedule_recording(params.get("title", ""),
                           int(params.get("start_ms", 0)),
                           int(params.get("dur_ms", 0)))
    elif mode == "record_now":
        record_now(params.get("title", ""))
    elif mode == "record_current":
        record_current_stream()
    elif mode == "timers":
        timers()
    elif mode == "del_timer":
        del_timer(params.get("tid", ""))
    else:
        main_menu()


if __name__ == "__main__":
    main()

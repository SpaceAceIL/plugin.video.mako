# -*- coding: utf-8 -*-
"""Mako Live — Made by SpaceAce (space@anan.media)."""
import os
import sys
import time
from urllib.parse import parse_qsl, quote

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon

_ADDON = xbmcaddon.Addon()
_LIB = os.path.join(_ADDON.getAddonInfo("path"), "resources", "lib")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

from resources.lib.mako import resolve, LIVE_URL
from resources.lib import epg, recorder
from resources.lib.strings import _, current_lang

HANDLE  = int(sys.argv[1]) if len(sys.argv) > 1 else -1
BASEURL = sys.argv[0] if sys.argv else ""
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def he(s):
    """Prefix RLM to Hebrew content so skins render RTL correctly."""
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
                   "User-Agent={0}&Referer=https://www.mako.co.il/".format(UA))
    li.setProperty("inputstream.adaptive.manifest_headers",
                   "User-Agent={0}".format(UA))

    if HANDLE >= 0:
        try:
            xbmcplugin.setResolvedUrl(HANDLE, True, li)
            return
        except Exception as e:
            xbmc.log("[mako] setResolvedUrl failed: {0}".format(e),
                     xbmc.LOGWARNING)

    xbmc.Player().play(stream_url, li)
    xbmc.sleep(3000)
    xbmcgui.Dialog().notification(_("resolve_title"), _("playing_hint"),
                                  xbmcgui.NOTIFICATION_INFO, 5000)


def _resolve_play(article):
    pd = xbmcgui.DialogProgress()
    pd.create(_("resolve_title"), _("resolve_msg"))
    try:
        pd.update(30, _("fetching"))
        s, _title = resolve(article, log=xbmc.log)
        pd.update(90, _("starting"))
        pd.close()
        _play(s)
    except Exception as e:
        xbmc.log("[mako] " + str(e), xbmc.LOGERROR)
        xbmcgui.Dialog().notification(_("resolve_title"), str(e),
                                      xbmcgui.NOTIFICATION_ERROR, 6000)
        if HANDLE >= 0:
            xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        try:
            pd.close()
        except Exception:
            pass


# ---------------------------------------------------------------- menus

def main_menu():
    li = xbmcgui.ListItem(label=_("live_now"))
    xbmcplugin.addDirectoryItem(HANDLE, url(mode="live"), li, isFolder=False)

    add_dir(_("tv_guide"), {"mode": "guide"})
    add_dir(_("scheduled"), {"mode": "timers"})
    add_dir(_("language"), {"mode": "language_menu"})
    xbmcplugin.endOfDirectory(HANDLE)


def language_menu():
    current = _ADDON.getSetting("language") or "Auto (follow Kodi)"
    for val in ("Auto (follow Kodi)", "English", "עברית"):
        mark = "• " if val == current else "   "
        label = mark + val
        li = xbmcgui.ListItem(label=label)
        xbmcplugin.addDirectoryItem(
            HANDLE, url(mode="set_language", lang=val), li, isFolder=False)
    xbmcplugin.endOfDirectory(HANDLE)


def set_language(value):
    _ADDON.setSetting("language", value)
    xbmcgui.Dialog().notification(_("language"), value,
                                  xbmcgui.NOTIFICATION_INFO, 3000)
    xbmcplugin.endOfDirectory(HANDLE)


def guide():
    try:
        programs = epg.fetch_epg(log=xbmc.log)
    except Exception as e:
        xbmcgui.Dialog().notification(_("epg_title"), str(e),
                                      xbmcgui.NOTIFICATION_ERROR, 6000)
        xbmcplugin.endOfDirectory(HANDLE)
        return

    now_ms = int(time.time() * 1000)
    items = [p for p in programs
             if p["start_ms"] + p["duration_ms"] > now_ms - 7200000
             and p["start_ms"] < now_ms + 24 * 3600 * 1000]

    for p in items:
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
        add_playable(_("watch_live"), {"mode": "live"}, plot=he(title))
        add_playable(_("record_stream"),
                     {"mode": "record_now", "title": title},
                     plot=_("record_desc"))
    else:
        add_playable(_("schedule_rec"),
                     {"mode": "schedule",
                      "title": title,
                      "start_ms": start_ms,
                      "dur_ms": dur_ms},
                     plot=_("schedule_desc", epg.fmt_time(start_ms)))
    add_playable(_("program_info"),
                 {"mode": "program_info",
                  "title": title,
                  "start_ms": start_ms,
                  "dur_ms": dur_ms})
    xbmcplugin.endOfDirectory(HANDLE)


def program_info(title, start_ms, dur_ms):
    body = "{0}: {1}\n{2}: {3}\n{4}: {5} {6}".format(
        _("info_start"),
        time.strftime("%a %d/%m %H:%M", time.localtime(start_ms / 1000.0)),
        _("info_end"),
        time.strftime("%a %d/%m %H:%M",
                      time.localtime((start_ms + dur_ms) / 1000.0)),
        _("info_duration"), int(dur_ms / 60000), _("info_min"))
    xbmcgui.Dialog().textviewer(he(title), body)
    xbmcplugin.endOfDirectory(HANDLE)


def schedule_recording(title, start_ms, dur_ms):
    try:
        recorder.add_timer(title,
                           int(start_ms / 1000),
                           int((start_ms + dur_ms) / 1000),
                           LIVE_URL, "")
        xbmcgui.Dialog().notification(
            _("scheduled_title"),
            _("scheduled_msg", title[:30], epg.fmt_time(start_ms)),
            xbmcgui.NOTIFICATION_INFO, 6000)
    except Exception as e:
        xbmcgui.Dialog().notification(_("resolve_title"), str(e),
                                      xbmcgui.NOTIFICATION_ERROR, 5000)
    xbmcplugin.endOfDirectory(HANDLE)


def record_now(title):
    kb = xbmcgui.Dialog().numeric(0, _("minutes"), "60")
    if not kb:
        xbmcplugin.endOfDirectory(HANDLE)
        return
    try:
        mins = int(kb)
    except ValueError:
        mins = 60
    now = int(time.time())
    recorder.add_timer(title or _("live_capture"),
                       now, now + mins * 60, LIVE_URL, "")
    xbmcgui.Dialog().notification(
        _("recording"),
        _("recording_msg", mins),
        xbmcgui.NOTIFICATION_INFO, 6000)
    xbmcplugin.endOfDirectory(HANDLE)


def record_current_stream():
    try:
        u = xbmc.Player().getPlayingFile() or ""
    except Exception:
        u = ""
    if "mako-streaming.akamaized.net" not in u:
        xbmcgui.Dialog().notification(_("resolve_title"), _("no_stream"),
                                      xbmcgui.NOTIFICATION_WARNING, 4000)
        return
    kb = xbmcgui.Dialog().numeric(0, _("minutes"), "60")
    if not kb:
        return
    try:
        mins = int(kb)
    except ValueError:
        mins = 60
    now = int(time.time())
    recorder.add_timer(_("live_capture"), now, now + mins * 60, u, "")
    xbmcgui.Dialog().notification(
        _("recording"),
        _("recording_msg", mins),
        xbmcgui.NOTIFICATION_INFO, 6000)


def timers():
    items = recorder.load_timers()
    active = {a["id"]: a for a in recorder.load_active()}
    for t in items:
        status = t.get("status", "?")
        if status == "done":
            prefix = "[" + _("status_done") + "] "
        elif t.get("id") in active:
            prefix = "[" + _("status_rec") + "] "
        else:
            prefix = "[{0}] ".format(status)
        label = prefix + "{0}  {1}".format(
            he(t.get("title", "?")),
            time.strftime("%d/%m %H:%M",
                          time.localtime(t["start_unix"])))
        li = xbmcgui.ListItem(label=label)
        xbmcplugin.addDirectoryItem(HANDLE,
                                    url(mode="del_timer", tid=t["id"]),
                                    li, isFolder=False)
    xbmcplugin.endOfDirectory(HANDLE)


def del_timer(tid):
    recorder.remove_timer(tid)
    xbmcgui.Dialog().notification(_("resolve_title"), _("timer_removed"),
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
    elif mode == "language_menu":
        language_menu()
    elif mode == "set_language":
        set_language(params.get("lang", "Auto (follow Kodi)"))
    else:
        main_menu()


if __name__ == "__main__":
    main()

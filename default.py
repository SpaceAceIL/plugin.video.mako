# -*- coding: utf-8 -*-
"""Israeli TV — Made by SpaceAce."""
import os, sys
from urllib.parse import parse_qsl, quote
import xbmc, xbmcgui, xbmcplugin, xbmcaddon

_ADDON = xbmcaddon.Addon()
_LIB = os.path.join(_ADDON.getAddonInfo("path"), "resources", "lib")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

from resources.lib.mako import resolve, LIVE_URL
from resources.lib import epg

HANDLE  = int(sys.argv[1]) if len(sys.argv) > 1 else -1
BASEURL = sys.argv[0] if sys.argv else ""
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# ---------- Channel list ----------
# type: "direct"  -> play URL as-is
#       "mako"    -> run through the Mako token resolver
CHANNELS = [
    {"name": "Kan 11",           "type": "direct",
     "url": "https://kancdn.medonecdn.net/livehls/oil/kancdn-live/live/kan11/live.livx/playlist.m3u8",
     "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c8/Kan11Logo.svg/500px-Kan11Logo.svg.png"},
    {"name": "Keshet 12",        "type": "mako",
     "url": LIVE_URL,
     "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f0/Keshet12_2018.svg/960px-Keshet12_2018.svg.png"},
    {"name": "Channel 13",       "type": "direct",
     "url": "https://d2xg1g9o5vns8m.cloudfront.net/out/v1/0855d703f7d5436fae6a9c7ce8ca5075/index.m3u8",
     "logo": "https://upload.wikimedia.org/wikipedia/he/thumb/1/17/Reshet13Logo2022.svg/500px-Reshet13Logo2022.svg.png"},
    {"name": "Channel 14",       "type": "direct",
     "url": "https://r.il.cdn-redge.media/livehls/oil/ch14/live/ch14/live.livx/playlist.m3u8",
     "logo": "https://i.imgur.com/Iq2Kb69.png"},
    {"name": "Makan 33",         "type": "direct",
     "url": "https://kancdn.medonecdn.net/livehls/oil/kancdn-live/live/makan/live.livx/playlist.m3u8",
     "logo": "https://upload.wikimedia.org/wikipedia/en/5/56/MeKan_33_logo_2017.png"},
    {"name": "Kan Educational",  "type": "direct",
     "url": "http://stream.mcquack.net/378/index.m3u8",
     "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6b/KanHinuchit.svg/500px-KanHinuchit.svg.png"},
    {"name": "Knesset",          "type": "direct",
     "url": "http://stream.mcquack.net/48/index.m3u8",
     "logo": ""},
]


def url(**params):
    return BASEURL + "?" + "&".join(
        "{0}={1}".format(k, quote(str(v), safe="")) for k, v in params.items())


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


def _play_mako(article):
    pd = xbmcgui.DialogProgress(); pd.create("Mako", "Resolving...")
    try:
        pd.update(30, "Fetching...")
        s, _ = resolve(article, log=xbmc.log)
        pd.update(90, "Playing...")
        pd.close()
        _play(s)
    except Exception as e:
        xbmc.log("[israelitv] " + str(e), xbmc.LOGERROR)
        xbmcgui.Dialog().notification("Mako", str(e),
                                      xbmcgui.NOTIFICATION_ERROR, 6000)
        if HANDLE >= 0:
            xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        try: pd.close()
        except: pass


def tv_guide():
    """Israeli TV guide from Mako EPG (Channel 12 schedule)."""
    try:
        programs = epg.fetch_epg(log=xbmc.log)
    except Exception as e:
        xbmcgui.Dialog().notification("EPG", str(e),
                                      xbmcgui.NOTIFICATION_ERROR, 6000)
        xbmcplugin.endOfDirectory(HANDLE)
        return

    now_ms = int(__import__("time").time() * 1000)
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
            p["title"])
        plot = "{0}\n\n{1}-{2}".format(
            p["description"],
            epg.fmt_time(p["start_ms"]),
            epg.fmt_time(p["start_ms"] + p["duration_ms"]))
        li = xbmcgui.ListItem(label=label)
        li.setInfo("video", {"title": p["title"], "plot": plot})
        if p.get("picture"):
            li.setArt({"thumb": p["picture"], "icon": p["picture"]})
        # Each guide item plays the live Mako stream
        xbmcplugin.addDirectoryItem(HANDLE, url(mode="play_mako", idx="1"),
                                    li, isFolder=False)
    xbmcplugin.endOfDirectory(HANDLE)


def main_menu():
    # Live channels
    for i, ch in enumerate(CHANNELS):
        li = xbmcgui.ListItem(label=ch["name"])
        if ch.get("logo"):
            li.setArt({"thumb": ch["logo"], "icon": ch["logo"]})
        xbmcplugin.addDirectoryItem(HANDLE, url(mode="play", idx=i),
                                    li, isFolder=False)
    # TV Guide
    add_dir("📺 TV Guide (Channel 12)", {"mode": "guide"})
    xbmcplugin.endOfDirectory(HANDLE)


def add_dir(label, params):
    li = xbmcgui.ListItem(label=label)
    xbmcplugin.addDirectoryItem(HANDLE, url(**params), li, isFolder=True)


def main():
    params = dict(parse_qsl(sys.argv[2][1:])) if len(sys.argv) > 2 else {}
    mode = params.get("mode", "root")

    if mode == "play":
        try:
            ch = CHANNELS[int(params.get("idx", "0"))]
        except (ValueError, IndexError):
            return
        if ch["type"] == "mako":
            _play_mako(ch["url"])
        else:
            _play(ch["url"])
    elif mode == "play_mako":
        _play_mako(LIVE_URL)
    elif mode == "guide":
        tv_guide()
    else:
        main_menu()


if __name__ == "__main__":
    main()

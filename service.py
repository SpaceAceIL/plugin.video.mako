# -*- coding: utf-8 -*-
"""
Background service: keeps the Mako live stream alive past token expiry.

How it works:
  - Wakes up every 30 s
  - If something is playing from mako-streaming.akamaized.net
  - Extracts the hdnea expiry from the current URL
  - If expiry is < 3 min away, re-resolves and calls Player.updateStream()

Kodi runs service.py automatically on startup because the addon.xml declares it.
"""
import os, re, time, sys
import xbmc, xbmcaddon

_ADDON = xbmcaddon.Addon()
_LIB = os.path.join(_ADDON.getAddonInfo("path"), "resources", "lib")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

from resources.lib.mako import resolve, LIVE_URL

POLL_SECONDS = 30
REFRESH_BEFORE = 180          # refresh when < 3 min remain
EXP_RE = re.compile(r"exp(?:%3D|=)(\d{9,11})", re.I)


def _current_mako_url():
    """Return the currently-playing mako URL, or None."""
    player = xbmc.Player()
    if not player.isPlaying():
        return None
    try:
        url = player.getPlayingFile() or ""
    except Exception:
        return None
    if "mako-streaming.akamaized.net" not in url:
        return None
    return url


def _expiry_from_url(url):
    """Return the epoch-seconds expiry embedded in the hdnea token, or 0."""
    m = EXP_RE.search(url)
    if not m:
        return 0
    try:
        return int(m.group(1))
    except Exception:
        return 0


def _seconds_left(url):
    exp = _expiry_from_url(url)
    if not exp:
        return 999999
    return exp - int(time.time())


def _log(msg):
    xbmc.log("[mako-service] " + msg, xbmc.LOGINFO)


def main():
    _log("service started")
    monitor = xbmc.Monitor()
    last_refresh = 0.0

    while not monitor.abortRequested():
        if monitor.waitForAbort(POLL_SECONDS):
            break

        url = _current_mako_url()
        if not url:
            continue

        left = _seconds_left(url)
        if left <= 0:
            _log("token expired before we could refresh (left={0}s)".format(left))
        if left > REFRESH_BEFORE:
            continue

        # avoid hammering: only refresh once per 60 s
        now = time.time()
        if now - last_refresh < 60:
            continue
        last_refresh = now

        _log("token expires in {0}s — refreshing".format(left))
        try:
            new_url, _ = resolve(LIVE_URL, log=xbmc.log)
        except Exception as exc:
            _log("resolve failed: {0}".format(exc))
            continue

        _log("got fresh token; updating stream")
        try:
            # updateStream keeps playback going with the new URL
            xbmc.Player().updateStream(new_url)
            _log("updateStream ok")
        except Exception as exc:
            _log("updateStream failed: {0} — stopping and restarting".format(exc))
            try:
                xbmc.Player().stop()
                xbmc.sleep(500)
                import xbmcgui
                li = xbmcgui.ListItem(path=new_url)
                li.setMimeType("application/vnd.apple.mpegurl")
                try:
                    xbmcaddon.Addon("inputstream.adaptive")
                    li.setProperty("inputstream", "inputstream.adaptive")
                    li.setProperty("inputstream.adaptive.manifest_type", "hls")
                except Exception:
                    pass
                xbmc.Player().play(new_url, li)
                _log("restarted playback with fresh token")
            except Exception as exc2:
                _log("restart failed: {0}".format(exc2))

    _log("service stopped")


if __name__ == "__main__":
    main()

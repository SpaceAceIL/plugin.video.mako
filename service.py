# -*- coding: utf-8 -*-
"""Mako Live background service - token refresh + update check."""
import os, re, time, json, sys
import xbmc, xbmcaddon, xbmcgui

_ADDON = xbmcaddon.Addon()
_LIB = os.path.join(_ADDON.getAddonInfo("path"), "resources", "lib")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

POLL_SECONDS   = 30
REFRESH_BEFORE = 180
EXP_RE         = re.compile(r"exp(?:%3D|=)(\d{9,11})", re.I)

GITHUB_API   = "https://api.github.com/repos/SpaceAceIL/plugin.video.mako/releases/latest"
CHECK_EVERY  = 6 * 3600   # check every 6 h


def _log(m):
    xbmc.log("[mako-service] " + m, xbmc.LOGINFO)


def _ver_tuple(v):
    try:
        return tuple(int(x) for x in re.split(r"[.\-]", v) if x.isdigit())
    except Exception:
        return (0,)


def _check_update_once():
    """Query GitHub for the latest release and notify if newer."""
    try:
        import urllib.request
        req = urllib.request.Request(
            GITHUB_API, headers={"User-Agent": "Mako-Live-Service"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        _log("update check failed: {0}".format(e))
        return

    latest = (data.get("tag_name") or "").lstrip("v")
    current = _ADDON.getAddonInfo("version")
    if not latest:
        return
    if _ver_tuple(latest) > _ver_tuple(current):
        _log("update available: v{0} (you have v{1})".format(latest, current))
        try:
            xbmcgui.Dialog().notification(
                "Mako Live update",
                "v{0} available (you have v{1})".format(latest, current),
                xbmcgui.NOTIFICATION_INFO, 8000)
        except Exception:
            pass


# ---------- token refresh (existing logic) ----------

def _current_mako_url():
    player = xbmc.Player()
    if not player.isPlaying():
        return None
    try:
        u = player.getPlayingFile() or ""
    except Exception:
        return None
    if "mako-streaming.akamaized.net" not in u:
        return None
    return u


def _expiry(u):
    m = EXP_RE.search(u)
    return int(m.group(1)) if m else 0


def _seconds_left(u):
    e = _expiry(u)
    return (e - int(time.time())) if e else 999999


def main():
    _log("service started")

    # ---- update check on boot (delayed a few seconds so Kodi is ready) ----
    monitor = xbmc.Monitor()
    if monitor.waitForAbort(15):
        return
    _check_update_once()

    # ---- main loop: token refresh + periodic update re-check ----
    last_refresh = 0.0
    last_check   = time.time()

    while not monitor.abortRequested():
        if monitor.waitForAbort(POLL_SECONDS):
            break

        # periodic update check
        if time.time() - last_check > CHECK_EVERY:
            _check_update_once()
            last_check = time.time()

        # token refresh
        url = _current_mako_url()
        if not url:
            continue
        left = _seconds_left(url)
        if left > REFRESH_BEFORE:
            continue
        now = time.time()
        if now - last_refresh < 60:
            continue
        last_refresh = now

        _log("token expires in {0}s - refreshing".format(left))
        try:
            from resources.lib.mako import resolve, LIVE_URL
            new_url, _ = resolve(LIVE_URL, log=xbmc.log)
        except Exception as e:
            _log("resolve failed: {0}".format(e))
            continue

        try:
            xbmc.Player().updateStream(new_url)
            _log("updateStream ok")
        except Exception as e:
            _log("updateStream failed: {0} - restarting".format(e))
            try:
                xbmc.Player().stop()
                xbmc.sleep(500)
                li = xbmcgui.ListItem(path=new_url)
                li.setMimeType("application/vnd.apple.mpegurl")
                li.setProperty("inputstream", "inputstream.adaptive")
                li.setProperty("inputstream.adaptive.manifest_type", "hls")
                xbmc.Player().play(new_url, li)
                _log("restarted")
            except Exception as e2:
                _log("restart failed: {0}".format(e2))

    _log("service stopped")


if __name__ == "__main__":
    main()

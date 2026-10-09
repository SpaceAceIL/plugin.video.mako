# -*- coding: utf-8 -*-
"""Mako Live - auto-installs dependencies, plays Channel 12."""
import os, sys
from urllib.parse import parse_qsl, unquote
import xbmc, xbmcgui, xbmcplugin, xbmcaddon

_ADDON = xbmcaddon.Addon()
_LIB = os.path.join(_ADDON.getAddonInfo("path"), "resources", "lib")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

HANDLE = int(sys.argv[1]) if len(sys.argv) > 1 else -1
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# ============ POPUP (edit these) ============
POPUP_TITLE = "Mako Live"
POPUP_MESSAGE = "Streaming Channel 12 live.\n\nMade by SpaceAce"
# ===========================================


def _ensure_isa():
    """Check for inputstream.adaptive; try to auto-install if missing."""
    try:
        xbmcaddon.Addon("inputstream.adaptive")
        return True
    except Exception:
        pass

    xbmc.log("[mako] inputstream.adaptive missing - attempting auto-install",
             xbmc.LOGWARNING)

    # Try to install from any enabled repository
    try:
        xbmc.executebuiltin("InstallAddon(inputstream.adaptive)")
    except Exception as e:
        xbmc.log("[mako] InstallAddon failed: {0}".format(e), xbmc.LOGERROR)

    # Wait up to 20 s for the user to confirm / install to finish
    for _ in range(40):
        xbmc.sleep(500)
        try:
            xbmcaddon.Addon("inputstream.adaptive")
            xbmc.log("[mako] ISA installed", xbmc.LOGINFO)
            return True
        except Exception:
            pass

    # Fallback: ask the user to install it manually
    dlg = xbmcgui.Dialog()
    dlg.ok("Mako Live",
           "InputStream Adaptive is required.\n\n"
           "Install it from:\n"
           "Settings -> Add-ons -> Install from repository ->\n"
           "Kodi Add-on Repository -> VideoPlayer InputStream ->\n"
           "InputStream Adaptive\n\n"
           "Then restart Kodi and run Mako Live again.")
    return False


def _show_popup():
    if not POPUP_MESSAGE.strip():
        return True
    dlg = xbmcgui.Dialog()
    return dlg.yesno(POPUP_TITLE, POPUP_MESSAGE, nolabel="Cancel", yeslabel="Play")


def _build_listitem(url):
    li = xbmcgui.ListItem(path=url)
    li.setMimeType("application/vnd.apple.mpegurl")
    li.setProperty("inputstream", "inputstream.adaptive")
    li.setProperty("inputstream.adaptive.manifest_type", "hls")
    li.setProperty("inputstream.adaptive.stream_headers",
                   "User-Agent={0}&Referer=https://www.mako.co.il/".format(UA))
    li.setProperty("inputstream.adaptive.manifest_headers",
                   "User-Agent={0}".format(UA))
    return li


def play_live(article_url):
    if not _ensure_isa():
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return

    if not _show_popup():
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return

    pd = xbmcgui.DialogProgress()
    pd.create("Mako Live", "Resolving stream...")
    try:
        from resources.lib.mako import resolve, LIVE_URL
        pd.update(20, "Fetching article...")
        stream, title = resolve(article_url, log=xbmc.log)
        pd.update(80, "Starting playback...")
        if not stream:
            raise RuntimeError("empty stream URL")
        xbmc.log("[mako] URL: {0}".format(stream[:180]), xbmc.LOGINFO)
        li = _build_listitem(stream)
        pd.close()
        player = xbmc.Player()
        player.play(stream, li)
        for _ in range(40):
            xbmc.sleep(250)
            if player.isPlaying():
                xbmc.log("[mako] playback started", xbmc.LOGINFO)
                xbmc.sleep(1000)
                return
        xbmc.log("[mako] playback did not start within 10s", xbmc.LOGERROR)
    except Exception as exc:
        xbmc.log("[mako] error: " + str(exc), xbmc.LOGERROR)
        xbmcgui.Dialog().notification(
            "Mako Live", "Failed: {0}".format(exc),
            xbmcgui.NOTIFICATION_ERROR, 6000)
        try: pd.close()
        except: pass


def main():
    params = dict(parse_qsl(sys.argv[2][1:])) if len(sys.argv) > 2 else {}
    if params.get("url"):
        play_live(unquote(params["url"]))
        return
    from resources.lib.mako import LIVE_URL
    play_live(LIVE_URL)


if __name__ == "__main__":
    main()

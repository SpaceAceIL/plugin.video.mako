# -*- coding: utf-8 -*-
"""Mako Live service — token refresh + scheduled recordings."""
import os, re, time, sys
import xbmc, xbmcaddon

_ADDON = xbmcaddon.Addon()
_LIB = os.path.join(_ADDON.getAddonInfo("path"), "resources", "lib")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

from resources.lib.mako import resolve, LIVE_URL
from resources.lib import recorder

POLL_SECONDS   = 30
REFRESH_BEFORE = 180
EXP_RE         = re.compile(r"exp(?:%3D|=)(\d{9,11})", re.I)

_ACTIVE = {}


def _log(m):
    xbmc.log("[mako-service] " + m, xbmc.LOGINFO)


def _current_url():
    p = xbmc.Player()
    if not p.isPlaying():
        return None
    try:
        u = p.getPlayingFile() or ""
    except Exception:
        return None
    return u if "mako-streaming.akamaized.net" in u else None


def _secs_left(u):
    m = EXP_RE.search(u)
    if not m:
        return 999999
    return int(m.group(1)) - int(time.time())


def _rec_dir():
    d = recorder.configured_dir()
    if not os.path.isdir(d):
        try:
            os.makedirs(d, exist_ok=True)
        except Exception:
            pass
    return d


def _check_recorders():
    ffmpeg = recorder.find_ffmpeg(recorder.configured_ffmpeg())
    now = int(time.time())
    timers = recorder.load_timers()
    active = recorder.load_active()
    changed = False

    # 1. start due timers
    for t in timers:
        tid = t.get("id")
        if not tid or tid in _ACTIVE:
            continue
        if t.get("status") != "scheduled":
            continue
        if t["start_unix"] <= now < t["end_unix"]:
            out = t.get("output_path") or os.path.join(
                _rec_dir(),
                "{0}_{1}.ts".format(
                    time.strftime("%Y%m%d_%H%M", time.localtime(t["start_unix"])),
                    re.sub(r"[^A-Za-z0-9_-]+", "_", t.get("title", "rec"))[:40]))
            proc = recorder.spawn(ffmpeg, t["stream_url"], out, _log)
            if proc:
                _ACTIVE[tid] = proc
                active.append({"id": tid, "title": t.get("title", ""),
                               "output": out, "pid": proc.pid,
                               "started": now, "end_unix": t["end_unix"]})
                for x in timers:
                    if x.get("id") == tid:
                        x["status"] = "recording"
                changed = True
                _log("recording started: " + t.get("title", tid))

    # 2. stop finished
    keep = []
    for a in active:
        tid = a["id"]
        proc = _ACTIVE.get(tid)
        if proc is None:
            keep.append(a)
            continue
        if proc.poll() is not None or now >= a.get("end_unix", 0):
            try:
                proc.terminate()
            except Exception:
                pass
            _ACTIVE.pop(tid, None)
            for x in timers:
                if x.get("id") == tid:
                    x["status"] = "done"
            changed = True
            _log("recording done: " + a.get("title", tid))
        else:
            keep.append(a)

    if changed:
        recorder.save_timers(timers)
    recorder.save_active(keep)


def main():
    _log("service started")
    monitor = xbmc.Monitor()
    last_refresh = 0.0

    while not monitor.abortRequested():
        if monitor.waitForAbort(POLL_SECONDS):
            break

        # token refresh
        u = _current_url()
        if u:
            left = _secs_left(u)
            if 0 < left <= REFRESH_BEFORE and (time.time() - last_refresh) >= 60:
                last_refresh = time.time()
                _log("token refresh (left={0}s)".format(left))
                try:
                    new_url, _ = resolve(LIVE_URL, log=xbmc.log)
                    xbmc.Player().updateStream(new_url)
                    _log("updateStream ok")
                except Exception as e:
                    _log("refresh failed: {0}".format(e))

        # scheduled recordings
        try:
            _check_recorders()
        except Exception as e:
            _log("recorder error: {0}".format(e))

    for tid, proc in list(_ACTIVE.items()):
        try:
            proc.terminate()
        except Exception:
            pass
    _log("service stopped")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""Mako recorder — timers + ffmpeg process control."""
import os, json, time, subprocess


def _profile_dir():
    import xbmcaddon
    d = xbmcaddon.Addon().getAddonInfo("profile")
    if not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    return d


def timers_path():
    return os.path.join(_profile_dir(), "timers.json")


def load_timers():
    p = timers_path()
    if not os.path.exists(p):
        return []
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_timers(t):
    with open(timers_path(), "w", encoding="utf-8") as f:
        json.dump(t, f, ensure_ascii=False, indent=2)


def add_timer(title, start_unix, end_unix, stream_url, output_path=""):
    t = load_timers()
    item = {
        "id":          "t{0}".format(int(start_unix)),
        "title":       title,
        "start_unix":  int(start_unix),
        "end_unix":    int(end_unix),
        "stream_url":  stream_url,
        "output_path": output_path,
        "status":      "scheduled",
        "created":     int(time.time()),
    }
    t.append(item)
    save_timers(t)
    return item


def remove_timer(timer_id):
    save_timers([x for x in load_timers() if x.get("id") != timer_id])


def active_path():
    return os.path.join(_profile_dir(), "active.json")


def load_active():
    p = active_path()
    if not os.path.exists(p):
        return []
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_active(a):
    with open(active_path(), "w", encoding="utf-8") as f:
        json.dump(a, f, ensure_ascii=False, indent=2)


def find_ffmpeg(configured=""):
    if configured and os.path.isfile(configured):
        return configured
    import shutil
    for n in ("ffmpeg", "ffmpeg.exe"):
        p = shutil.which(n)
        if p:
            return p
    return ""


def spawn(ffmpeg, stream_url, output_path, log):
    if not ffmpeg:
        log("[mako-rec] ffmpeg not found")
        return None
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
    except Exception:
        pass
    cmd = [ffmpeg, "-y", "-loglevel", "warning",
           "-user_agent", "Mozilla/5.0",
           "-i", stream_url,
           "-c", "copy", "-f", "mpegts", output_path]
    log("[mako-rec] spawn: " + " ".join(cmd[:6]) + " ...")
    try:
        return subprocess.Popen(cmd,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                                stdin=subprocess.DEVNULL)
    except Exception as e:
        log("[mako-rec] spawn error: {0}".format(e))
        return None

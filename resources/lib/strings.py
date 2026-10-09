# -*- coding: utf-8 -*-
"""Localized UI strings for Mako Live."""

import xbmc


STRINGS = {
    "en": {
        "live_now":        "Channel 12 – Live Now",
        "tv_guide":        "TV Guide",
        "scheduled":       "Scheduled Recordings",
        "language":        "Language",
        "watch_live":      "▶  Watch Live Now",
        "record_stream":   "⏺  Record Current Stream…",
        "record_desc":     "Asks for minutes, then records",
        "schedule_rec":    "📅  Schedule Recording",
        "schedule_desc":   "Timer starts at {0}",
        "program_info":    "ℹ  Program Info",
        "info_title":      "Program Info",
        "recording":       "Mako Recording",
        "recording_msg":   "Recording for {0} min",
        "scheduled_title": "Mako Scheduled",
        "scheduled_msg":   "{0} at {1}",
        "timer_removed":   "Timer removed",
        "no_stream":       "No Mako stream playing",
        "playing_hint":    "Playing. Ctrl+R to record current stream.",
        "resolve_title":   "Mako Live",
        "resolve_msg":     "Resolving stream…",
        "fetching":        "Fetching…",
        "starting":        "Starting playback…",
        "minutes":         "Minutes to record",
        "live_capture":    "Live Capture",
        "epg_title":       "Mako EPG",
        "status_done":     "DONE",
        "status_rec":      "REC",
        "lang_auto":       "Auto (follow Kodi)",
        "lang_en":         "English",
        "lang_he":         "עברית",
        "info_start":      "Start",
        "info_end":        "End",
        "info_duration":   "Duration",
        "info_min":        "min",
    },
    "he": {
        "live_now":        "ערוץ 12 – שידור חי",
        "tv_guide":        "לוח שידורים",
        "scheduled":       "הקלטות מתוזמנות",
        "language":        "שפה",
        "watch_live":      "▶  צפה בשידור חי",
        "record_stream":   "⏺  הקלט את השידור הנוכחי…",
        "record_desc":     "שואל כמה דקות ומתחיל להקליט",
        "schedule_rec":    "📅  תזמן הקלטה",
        "schedule_desc":   "מתחיל ב־{0}",
        "program_info":    "ℹ  פרטי התוכנית",
        "info_title":      "פרטי התוכנית",
        "recording":       "הקלטת מאקו",
        "recording_msg":   "מקליט למשך {0} דקות",
        "scheduled_title": "מאקו מתוזמן",
        "scheduled_msg":   "{0} בשעה {1}",
        "timer_removed":   "ההקלטה המתוזמנת הוסרה",
        "no_stream":       "אין שידור מאקו פעיל",
        "playing_hint":    "מנגן. Ctrl+R להקלטת השידור הנוכחי.",
        "resolve_title":   "מאקו לייב",
        "resolve_msg":     "מפענח שידור…",
        "fetching":        "טוען…",
        "starting":        "מתחיל ניגון…",
        "minutes":         "דקות להקלטה",
        "live_capture":    "הקלטה חיה",
        "epg_title":       "מאקו EPG",
        "status_done":     "הושלם",
        "status_rec":      "מקליט",
        "lang_auto":       "אוטומטי (לפי קודי)",
        "lang_en":         "English",
        "lang_he":         "עברית",
        "info_start":      "התחלה",
        "info_end":        "סיום",
        "info_duration":   "משך",
        "info_min":        "דק׳",
    },
}


def current_lang():
    """Return 'he' or 'en'. Honors addon override, else Kodi UI language."""
    override = ""
    try:
        import xbmcaddon
        override = (xbmcaddon.Addon().getSetting("language") or "").strip()
    except Exception:
        pass

    if override == "English":
        return "en"
    if override in ("עברית", "Hebrew", "he"):
        return "he"

    try:
        code = xbmc.getLanguage(xbmc.ISO_639_1, region=False) or "en"
        code = code.lower().split("_")[0].split("-")[0]
        if code in STRINGS:
            return code
    except Exception:
        pass
    return "en"


def _(key, *args):
    """Return localized string. Prepends RLM if it contains Hebrew."""
    lang = current_lang()
    s = STRINGS.get(lang, STRINGS["en"]).get(key)
    if s is None:
        s = STRINGS["en"].get(key, key)
    if args:
        try:
            s = s.format(*args)
        except Exception:
            pass
    if any("\u0590" <= c <= "\u05ff" for c in s):
        return "\u200f" + s
    return s

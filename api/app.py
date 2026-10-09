# -*- coding: utf-8 -*-
"""Mako API - Flask. Made by SpaceAce - space@anan.media."""
import os
from flask import Flask, jsonify, request
from mako_resolver import resolve

app = Flask(__name__)

LIVE = ("https://www.mako.co.il/news-channel2/Channel-2-Newscast-q3_2019/"
        "Article-3bf5c3a8e967f51006.htm")

def _ok(d): return jsonify({"ok": True, "data": d})
def _err(m, c=400): return jsonify({"ok": False, "error": m}), c

@app.route("/")
def root():
    return jsonify({"name": "mako-api", "author": "SpaceAce",
                    "email": "space@anan.media",
                    "endpoints": ["/health", "/live", "/resolve?url="]})

@app.route("/health")
def health(): return jsonify({"ok": True})

@app.route("/live")
def live():
    try: return _ok(resolve(LIVE))
    except Exception as e: return _err(str(e), 502)

@app.route("/resolve")
def resolve_ep():
    u = request.args.get("url", "").strip()
    if not u: return _err("missing url param")
    if not u.startswith("http"): return _err("url must start http")
    try: return _ok(resolve(u))
    except Exception as e: return _err(str(e), 502)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))

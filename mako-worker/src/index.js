// src/index.js — Mako live HLS full proxy with pre-roll ad

const LIVE_ARTICLE = 'https://www.mako.co.il/news-channel2/Channel-2-Newscast-q3_2019/Article-3bf5c3a8e967f51006.htm';
const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';

const KV_KEY      = 'live.m3u8';
const KV_META_KEY = 'live.meta';
const AD_TTL_SEC  = 3600;

// AES key + IV as raw bytes
const KEY_BYTES = new Uint8Array([
  0x59,0x68,0x6e,0x55,0x61,0x58,0x4d,0x6d,
  0x6c,0x74,0x42,0x36,0x67,0x64,0x38,0x70,
  0x39,0x53,0x57,0x6c,0x65,0x51,0x3d,0x3d
]);
const IV_BYTES = new Uint8Array([
  0x74,0x68,0x65,0x45,0x78,0x61,0x63,0x74,
  0x31,0x36,0x43,0x68,0x61,0x72,0x73,0x3d
]);

// ---------- base64 ----------
function b64encode(bytes) {
  let s = '';
  for (let i = 0; i < bytes.length; i++) s += String.fromCharCode(bytes[i]);
  return btoa(s);
}
function b64decode(b64) {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

// ---------- AES-CBC ----------
let _keyPromise = null;
function getKey() {
  if (!_keyPromise) {
    _keyPromise = crypto.subtle.importKey(
      'raw', KEY_BYTES, { name: 'AES-CBC' }, false, ['encrypt', 'decrypt']
    );
  }
  return _keyPromise;
}
async function aesEncrypt(text) {
  const key = await getKey();
  const ct = await crypto.subtle.encrypt(
    { name: 'AES-CBC', iv: IV_BYTES }, key, new TextEncoder().encode(text)
  );
  return b64encode(new Uint8Array(ct));
}
async function aesDecrypt(b64) {
  const key = await getKey();
  const pt = await crypto.subtle.decrypt(
    { name: 'AES-CBC', iv: IV_BYTES }, key, b64decode(b64)
  );
  return new TextDecoder().decode(pt);
}

// ---------- resolver ----------
async function resolveMasterM3u8() {
  const html = await fetch(LIVE_ARTICLE, { headers: { 'User-Agent': UA } }).then(r => r.text());
  const m = html.match(/player-embed\/\?vid=([^&"']+)&cid=([^&"']+)&galleryCid=([^&"']+)/);
  if (!m) throw new Error('no player-embed on page');
  const [, vid, cid, gcid] = m;

  const mobileUrl = 'https://mobile.mako.co.il/AjaxPage?jspName=playlist.jsp'
                  + `&vcmid=${vid}&videoChannelId=${cid}&galleryChannelId=${gcid}`
                  + '&isGallery=false&consumer=android4&encryption=no&appId=mako';
  const data = await fetch(mobileUrl, {
    headers: { 'User-Agent': UA, 'Referer': 'https://www.mako.co.il/' }
  }).then(r => r.json());

  const media = (data.media || []).find(x => x.format === 'AKAMAI_HLS' && /\.m3u8/.test(x.url))
             || (data.media || []).find(x => /\.m3u8/.test(x.url));
  if (!media) throw new Error('no m3u8 in media list');

  const mediaUrl = media.url;
  const cdn = media.cdn || 'AKAMAI';

  const lp = mediaUrl.replace(/^https?:\/\/[^/]+/, '');
  const payload = JSON.stringify({ lp, rv: cdn, du: 'undefined', dv: vid, na: '1.0.1' });
  const enc = await aesEncrypt(payload);

  const entResp = await fetch(
    'https://mass.mako.co.il/ClicksStatistics/entitlementsServicesV2.jsp?et=egt',
    {
      method: 'POST',
      headers: {
        'Content-Type': 'text/plain;charset=UTF-8',
        'User-Agent': UA,
        'Origin': 'https://www.mako.co.il',
        'Referer': LIVE_ARTICLE,
      },
      body: enc,
    }).then(r => r.text());

  let body = entResp.trim();
  if (body.startsWith('hvidt')) body = body.slice(5);
  const ticket = JSON.parse(await aesDecrypt(body)).tickets[0].ticket;

  const finalUrl = mediaUrl + (mediaUrl.includes('?') ? '&' : '?') + ticket;
  const master = await fetch(finalUrl, {
    headers: { 'User-Agent': UA, 'Referer': 'https://www.mako.co.il/' },
    redirect: 'follow',
  }).then(r => r.text());

  if (!master.startsWith('#EXTM3U')) throw new Error('not a master playlist');

  return {
    master,
    finalUrl,
    title: (data.videoDetails || {}).title || '',
    fetchedAt: Date.now(),
  };
}

async function refreshCache(env) {
  const r = await resolveMasterM3u8();
  await env.MAKO_KV.put(KV_KEY, r.master);
  await env.MAKO_KV.put(KV_META_KEY, JSON.stringify({
    title: r.title, fetchedAt: r.fetchedAt, finalUrl: r.finalUrl,
  }));
  console.log(`[refresh] ${new Date().toISOString()}  ${r.title}`);
  return r;
}

// ---------- URL helpers ----------
function resolveUrl(base, ref) {
  if (/^https?:\/\//.test(ref)) return ref;
  if (ref.startsWith('//')) return 'https:' + ref;
  try {
    const u = new URL(base);
    if (ref.startsWith('/')) return u.origin + ref;
    return u.origin + u.pathname.replace(/[^/]+$/, '') + ref;
  } catch (e) { return ref; }
}

function rewritePlaylist(text, base, workerOrigin) {
  const out = [];
  for (const line of text.split('\n')) {
    const t = line.trim();
    if (!t) { out.push(line); continue; }
    if (t.startsWith('#')) {
      const m = t.match(/URI="([^"]+)"/);
      if (m) {
        const abs = resolveUrl(base, m[1]);
        out.push(line.replace(m[1], `${workerOrigin}/stream?u=${encodeURIComponent(abs)}`));
      } else {
        out.push(line);
      }
      continue;
    }
    const abs = resolveUrl(base, t);
    out.push(`${workerOrigin}/stream?u=${encodeURIComponent(abs)}`);
  }
  return out.join('\n');
}

function m3u8Headers() {
  return {
    'Content-Type': 'application/vnd.apple.mpegurl',
    'Cache-Control': 'no-store',
    'Access-Control-Allow-Origin': '*',
  };
}

// ---------- Ad injection (media playlists only) ----------
function injectAd(playlist, workerOrigin) {
  // Never touch master playlists
  if (playlist.includes('#EXT-X-STREAM-INF')) return playlist;

  const lines = playlist.split('\n');

  // Find the first #EXTINF — everything before that is header tags
  let firstSeg = -1;
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].startsWith('#EXTINF')) { firstSeg = i; break; }
  }
  if (firstSeg < 0) return playlist;

  // Strip PROGRAM-DATE-TIME so the player doesn't anchor to wall clock
  // and skip the ad
  const filtered = [];
  for (let i = 0; i < lines.length; i++) {
    if (i < firstSeg && lines[i].startsWith('#EXT-X-PROGRAM-DATE-TIME')) continue;
    filtered.push(lines[i]);
  }

  // Recompute insertion point in filtered array
  let insertAt = -1;
  for (let i = 0; i < filtered.length; i++) {
    if (filtered[i].startsWith('#EXTINF')) { insertAt = i; break; }
  }

  const adLines = [
    '#EXT-X-DISCONTINUITY',
    '#EXTINF:5.000,',
    `${workerOrigin}/ad.ts`,
  ];

  return [
    ...filtered.slice(0, insertAt),
    ...adLines,
    ...filtered.slice(insertAt),
  ].join('\n');
}

// Per-isolate cache of "seen" IPs (fast, ephemeral)
const _seen = new Map();
const SEEN_MS = AD_TTL_SEC * 1000;

function wasSeen(ip) {
  const t = _seen.get(ip);
  if (t && Date.now() - t < SEEN_MS) return true;
  return false;
}
function markSeen(ip) {
  _seen.set(ip, Date.now());
  // keep the map from growing unbounded
  if (_seen.size > 5000) {
    const cutoff = Date.now() - SEEN_MS;
    for (const [k, v] of _seen) if (v < cutoff) _seen.delete(k);
  }
}

// ---------- Proxy sub-playlist / segment ----------
async function proxyUrl(target, workerOrigin, request, env) {
  if (!target) return new Response('missing u', { status: 400 });
  if (!/^https:\/\/mako-streaming\.akamaized\.net\//.test(target)) {
    return new Response('not allowed', { status: 403 });
  }
  const r = await fetch(target, {
    headers: {
      'User-Agent': UA,
      'Referer': 'https://www.mako.co.il/',
      'Origin': 'https://www.mako.co.il',
    }
  });
  const ct = (r.headers.get('Content-Type') || '').toLowerCase();
  const isM3u8 = /mpegurl|m3u8/.test(ct) || /\.m3u8(\?|$)/.test(target);

  if (isM3u8) {
    const text = await r.text();
    const base = r.url || target;
    let rewritten = rewritePlaylist(text, base, workerOrigin);

    // Only inject ad into MEDIA playlists (no #EXT-X-STREAM-INF)
    const isMedia = !text.includes('#EXT-X-STREAM-INF');
    const ip = request.headers.get('CF-Connecting-IP') || '0.0.0.0';
    const adUrl = env.AD_SEGMENT_URL || '';

    if (isMedia && adUrl && !wasSeen(ip)) {
      rewritten = injectAd(rewritten, workerOrigin);
      markSeen(ip);
      // persist to KV so it survives isolate churn (best-effort, non-blocking)
      try {
        await env.MAKO_KV.put(`seen:${ip}`, '1', { expirationTtl: AD_TTL_SEC });
      } catch (e) { /* ignore */ }
      console.log(`[ad] injected for ${ip}`);
    }

    return new Response(rewritten, { status: r.status, headers: m3u8Headers() });
  }
  return new Response(r.body, {
    status: r.status,
    headers: {
      'Content-Type': ct || 'video/mp2t',
      'Cache-Control': 'public, max-age=3600',
      'Access-Control-Allow-Origin': '*',
    }
  });
}

// ---------- Worker entry ----------
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const workerOrigin = url.origin;

    try {
      // ---- /ad.ts ----
      if (url.pathname === '/ad.ts') {
        const adUrl = env.AD_SEGMENT_URL || '';
        if (!adUrl) return new Response('no ad', { status: 404 });
        const r = await fetch(adUrl, {
          headers: { 'User-Agent': UA, 'Referer': 'https://www.mako.co.il/' }
        });
        return new Response(r.body, {
          status: r.status,
          headers: {
            'Content-Type': 'video/mp2t',
            'Cache-Control': 'public, max-age=86400',
            'Access-Control-Allow-Origin': '*',
          }
        });
      }

      // ---- /status ----
      if (url.pathname === '/status') {
        const meta = await env.MAKO_KV.get(KV_META_KEY);
        return new Response(meta || '{}', {
          headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
        });
      }

      // ---- /stream?u= ----
      if (url.pathname === '/stream') {
        return await proxyUrl(url.searchParams.get('u'), workerOrigin, request, env);
      }

      // ---- main playlist ----
      let rawMaster = await env.MAKO_KV.get(KV_KEY);
      let meta = await env.MAKO_KV.get(KV_META_KEY, 'json');

      if (!rawMaster || !meta || !meta.finalUrl) {
        const r = await refreshCache(env);
        rawMaster = r.master;
        meta = { finalUrl: r.finalUrl };
      }

      const body = rewritePlaylist(rawMaster, meta.finalUrl, workerOrigin);
      return new Response(body, { headers: m3u8Headers() });
    } catch (e) {
      console.log('[worker error]', e.message, e.stack);
      return new Response('Worker error: ' + e.message, { status: 500 });
    }
  },

  async scheduled(event, env, ctx) {
    try {
      await refreshCache(env);
    } catch (e) {
      console.log('[cron error]', e.message);
    }
  },
};

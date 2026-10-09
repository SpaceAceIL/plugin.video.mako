# -*- coding: utf-8 -*-
"""Pure-Python AES-CBC (128/192/256), PKCS7. No dependencies.
Made by SpaceAce - space@anan.media."""

def _gen_sbox():
    p, q = 1, 1
    sbox = [0]*256
    while True:
        p = p ^ ((p << 1) & 0xff) ^ (0x1b if p & 0x80 else 0)
        q ^= (q << 1) & 0xff
        q ^= (q << 2) & 0xff
        q ^= (q << 4) & 0xff
        if q & 0x80: q ^= 0x09
        x  = q ^ ((q << 1) | (q >> 7)) & 0xff
        x ^= ((q << 2) | (q >> 6)) & 0xff
        x ^= ((q << 3) | (q >> 5)) & 0xff
        x ^= ((q << 4) | (q >> 4)) & 0xff
        sbox[p] = (x ^ 0x63) & 0xff
        if p == 1: break
    sbox[0] = 0x63
    return sbox

SBOX     = _gen_sbox()
INV_SBOX = [0]*256
for _i, _v in enumerate(SBOX):
    INV_SBOX[_v] = _i

RCON = [0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80,0x1b,0x36,0x6c,0xd8,0xab,0x4d,0x9a]

def _xtime(a):
    a <<= 1
    if a & 0x100: a ^= 0x11b
    return a & 0xff

def _expand_key(key):
    nk = len(key)//4
    nr = nk + 6
    w = [int.from_bytes(key[i*4:i*4+4], 'big') for i in range(nk)]
    for i in range(nk, 4*(nr+1)):
        t = w[i-1]
        if i % nk == 0:
            t = ((t << 8) | (t >> 24)) & 0xffffffff
            t = (SBOX[(t>>24)&0xff]<<24 | SBOX[(t>>16)&0xff]<<16 |
                 SBOX[(t>> 8)&0xff]<< 8 | SBOX[ t     &0xff])
            t ^= RCON[(i//nk)-1] << 24
        elif nk > 6 and i % nk == 4:
            t = (SBOX[(t>>24)&0xff]<<24 | SBOX[(t>>16)&0xff]<<16 |
                 SBOX[(t>> 8)&0xff]<< 8 | SBOX[ t     &0xff])
        w.append(w[i-nk] ^ t)
    return w, nr

def _ark(s, w, rnd):
    for c in range(4):
        k = w[rnd*4 + c]
        s[4*c+0] ^= (k >> 24) & 0xff
        s[4*c+1] ^= (k >> 16) & 0xff
        s[4*c+2] ^= (k >>  8) & 0xff
        s[4*c+3] ^=  k        & 0xff

def _sb(s, box):
    for i in range(16): s[i] = box[s[i]]

def _sr(s):
    for r in range(1, 4):
        row = [s[4*c+r] for c in range(4)]
        row = row[r:] + row[:r]
        for c in range(4): s[4*c+r] = row[c]

def _isr(s):
    for r in range(1, 4):
        row = [s[4*c+r] for c in range(4)]
        row = row[-r:] + row[:-r]
        for c in range(4): s[4*c+r] = row[c]

def _mxc_one(a, b, c, d):
    t = a ^ b ^ c ^ d
    return (a ^ t ^ _xtime(a ^ b),
            b ^ t ^ _xtime(b ^ c),
            c ^ t ^ _xtime(c ^ d),
            d ^ t ^ _xtime(d ^ a))

def _mc(s):
    for c in range(4):
        s[4*c:4*c+4] = _mxc_one(*s[4*c:4*c+4])

def _imc(s):
    for c in range(4):
        a, b, cc, d = s[4*c:4*c+4]
        u = _xtime(_xtime(a ^ cc))
        v = _xtime(_xtime(b ^ d))
        s[4*c:4*c+4] = _mxc_one(a ^ u, b ^ v, cc ^ u, d ^ v)

def _enc_block(block, w, nr):
    s = list(block)
    _ark(s, w, 0)
    for rnd in range(1, nr):
        _sb(s, SBOX); _sr(s); _mc(s); _ark(s, w, rnd)
    _sb(s, SBOX); _sr(s); _ark(s, w, nr)
    return bytes(s)

def _dec_block(block, w, nr):
    s = list(block)
    _ark(s, w, nr)
    for rnd in range(nr-1, 0, -1):
        _isr(s); _sb(s, INV_SBOX); _ark(s, w, rnd); _imc(s)
    _isr(s); _sb(s, INV_SBOX); _ark(s, w, 0)
    return bytes(s)

def cbc_encrypt(key, iv, pt):
    w, nr = _expand_key(key)
    pt = bytearray(pt)
    pad = 16 - (len(pt) % 16)
    pt += bytes([pad]) * pad
    out, prev = bytearray(), iv
    for i in range(0, len(pt), 16):
        blk = bytes(a ^ b for a, b in zip(pt[i:i+16], prev))
        enc = _enc_block(blk, w, nr)
        out += enc
        prev = enc
    return bytes(out)

def cbc_decrypt(key, iv, ct):
    w, nr = _expand_key(key)
    if len(ct) % 16: raise ValueError("ciphertext not 16-byte multiple")
    out, prev = bytearray(), iv
    for i in range(0, len(ct), 16):
        blk = ct[i:i+16]
        dec = _dec_block(blk, w, nr)
        out += bytes(a ^ b for a, b in zip(dec, prev))
        prev = blk
    pad = out[-1]
    if pad < 1 or pad > 16: raise ValueError("bad padding")
    return bytes(out[:-pad])

if __name__ == "__main__":
    import base64
    key = b"YhnUaXMmltB6gd8p9SWleQ=="
    iv  = b"theExact16Chars="[:16]
    msg = b'{"test":1}'
    ct  = cbc_encrypt(key, iv, msg)
    print("ct   =", base64.b64encode(ct).decode())
    pt  = cbc_decrypt(key, iv, ct)
    print("rt   =", pt.decode())
    assert pt == msg
    print("AES self-test OK")

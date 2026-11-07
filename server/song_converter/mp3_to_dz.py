#!/usr/bin/env python3
import argparse
import hashlib
import os
import sys

try:
    from Crypto.Cipher import Blowfish
except ImportError:
    sys.exit("Missing dependency: pip install pycryptodome")

BLOCK = 0x1800
ENC = 0x800

EMPTY_ID3 = b"ID3\x03\x00\x00\x00\x00\x00\x00"


def parse_iv(text: str) -> bytes:
    t = text.strip().lower()
    if t.startswith("0x"):
        t = t[2:]
    if len(t) > 16 or any(c not in "0123456789abcdef" for c in t):
        raise ValueError("IV must be at most 16 hex digits (64 bits)")
    return int(t, 16).to_bytes(8, "big")


def parse_secret(text: str) -> bytes:
    t = text.strip()
    if len(t) == 32 and all(c in "0123456789abcdefABCDEF" for c in t):
        raw = bytes.fromhex(t)
    else:
        raw = t.encode("latin-1")
    if len(raw) != 16:
        raise ValueError("secret must be exactly 16 bytes (32 hex chars or 16 ASCII chars)")
    return raw


def derive_key(track_id: str, secret: bytes) -> bytes:
    h = hashlib.md5(track_id.encode("utf-8")).hexdigest().encode("ascii")
    a, b = h[:16], h[16:]
    return bytes(a[i] ^ b[i] ^ secret[i] for i in range(16))


def _span(total: int, off: int) -> int:
    n = min(ENC, total - off)
    return n - (n % 8)


def encrypt_stream(data: bytes, key: bytes, iv: bytes) -> bytes:
    out = bytearray(data)
    for off in range(0, len(data), BLOCK):
        n = _span(len(data), off)
        if n <= 0:
            break
        cipher = Blowfish.new(key, Blowfish.MODE_CBC, iv)
        out[off:off + n] = cipher.encrypt(bytes(data[off:off + n]))
    return bytes(out)


def decrypt_stream(data: bytes, key: bytes, iv: bytes) -> bytes:
    out = bytearray(data)
    for off in range(0, len(data), BLOCK):
        n = _span(len(data), off)
        if n <= 0:
            break
        cipher = Blowfish.new(key, Blowfish.MODE_CBC, iv)
        out[off:off + n] = cipher.decrypt(bytes(data[off:off + n]))
    return bytes(out)


def header_ok(first_chunk: bytes) -> bool:
    if first_chunk[:3] == b"ID3":
        return True
    return len(first_chunk) > 12 and first_chunk[11] <= 1 and first_chunk[12] <= 1


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="source .mp3")
    ap.add_argument("output", nargs="?", help="output file (default: <track-id>.mp3 next to input)")
    ap.add_argument("--id", required=True, dest="track_id",
                    help="track ID the server will report as SNG_ID (key is derived from it)")
    ap.add_argument("--strip-first-char", action="store_true",
                    help="app strips the 1st char of the ID before hashing when tF == \"1\" (nw.gi()); "
                         "pass this if your track is flagged that way and --id includes that leading char")
    ap.add_argument("--iv", required=True, help="64-bit IV constant (xa.Sq), hex")
    ap.add_argument("--secret", required=True, help="16-byte secret mp.qu[keyIndex]: 32 hex chars or 16 ASCII")
    ap.add_argument("--no-id3-fix", action="store_true",
                    help="do not prepend an empty ID3v2 tag when the file lacks one")
    ap.add_argument("--no-pad", action="store_true",
                    help="do not zero-pad the file to a multiple of 8 bytes (padding keeps the last "
                         "Blowfish block intact; trailing zeros are ignored by MP3 decoders)")
    ap.add_argument("--verify", action="store_true", help="decrypt the result again and check the app's header test")
    args = ap.parse_args()

    iv = parse_iv(args.iv)
    secret = parse_secret(args.secret)
    key_id = args.track_id[1:] if args.strip_first_char else args.track_id
    key = derive_key(key_id, secret)

    with open(args.input, "rb") as f:
        data = f.read()

    if not args.no_id3_fix and data[:3] != b"ID3":
        data = EMPTY_ID3 + data
        print("note: prepended empty ID3v2 header so the app's header check passes")

    orig_len = len(data)
    if not args.no_pad and len(data) % 8:
        data += b"\x00" * (8 - len(data) % 8)
    enc = encrypt_stream(data, key, iv)

    out_path = args.output or os.path.join(os.path.dirname(os.path.abspath(args.input)), f"{args.track_id}.mp3")
    with open(out_path, "wb") as f:
        f.write(enc)

    print(f"key (hex):   {key.hex()}")
    print(f"blocks:      {-(-len(data) // BLOCK)} x {BLOCK} bytes, {ENC} encrypted each")
    print(f"wrote:       {out_path}")
    print(f"FILE SIZE:   {len(enc)} bytes  <-- your server's FILESIZE_MP3_* and Content-Length must be exactly this")

    if args.verify:
        dec = decrypt_stream(enc, key, iv)
        assert dec == data, "round trip mismatch"
        assert len(dec) >= orig_len
        assert header_ok(dec[:64]), "decrypted data would fail the app's header check (pb.f)"
        print("verify:      round trip OK, header check OK")


if __name__ == "__main__":
    main()

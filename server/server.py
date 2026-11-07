import os
import time
import secrets
import struct
import logging
import json
import hashlib
import urllib.parse
import urllib.request
import urllib.error
from flask import Flask, send_file, abort, request, Response, jsonify
from Crypto.Cipher import AES

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("deezer-mock")

COVERS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "covers"
)

SONGS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "songs"
)
ALBUMS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "albums"
)

@app.route("/images/cover/<cover_id>/<filename>")
def get_cover(cover_id, filename):
    
    if not cover_id.isalnum():
        abort(404)

    cover_path = os.path.join(COVERS_DIR, cover_id + ".jpg")

    if not os.path.isfile(cover_path):
        abort(404)

    return send_file(cover_path, mimetype="image/jpeg")
@app.route("/songs/<filename>")
def serve_audio(filename):
    print("\n[STREAM REQUEST]")
    print("Method:", request.method)
    print("Headers:", dict(request.headers))
    print("URL:", request.url)
    print("Remote:", request.remote_addr)

    path = os.path.join(SONGS_DIR, filename)

    if not os.path.isfile(path):
        return "Not Found", 404

    mp3_size = os.path.getsize(path)
    range_header = None

    print(
        "[STREAM]",
        "Range:", range_header,
        "MP3 size:", mp3_size,
        flush=True
    )

    def generate_range(start, length):
        remaining = length
        sent = 0

        with open(path, "rb") as f:
            f.seek(start)

            while remaining > 0:
                chunk = f.read(min(8192, remaining))

                if not chunk:
                    break

                sent += len(chunk)
                remaining -= len(chunk)
                yield chunk

        print(
            f"[STREAM] Finished: sent={sent}, "
            f"expected={length}, remaining={remaining}",
            flush=True
        )

    
    if not range_header:
        resp = Response(
            generate_range(0, mp3_size),
            status=200,
            mimetype="audio/mpeg",
            direct_passthrough=True,
        )

        resp.headers["Content-Length"] = str(mp3_size)
        resp.headers["Accept-Ranges"] = "bytes"
        resp.headers["Connection"] = "close"

        print("[STREAM] Status: 200")
        print("[STREAM] Content-Length:", mp3_size)
        print("[STREAM] Raw MP3: enabled")

        return resp

    
    try:
        if not range_header.startswith("bytes="):
            return "Invalid Range", 416

        byte_range = range_header[6:].split("-", 1)

        if len(byte_range) != 2:
            return "Invalid Range", 416

        if byte_range[0]:
            byte1 = int(byte_range[0])
            byte2 = int(byte_range[1]) if byte_range[1] else mp3_size - 1
        else:
            
            suffix_length = int(byte_range[1])

            if suffix_length <= 0:
                return "Invalid Range", 416

            byte1 = max(0, mp3_size - suffix_length)
            byte2 = mp3_size - 1

    except (ValueError, IndexError):
        return "Invalid Range", 416

    if byte1 < 0 or byte1 >= mp3_size or byte2 < byte1:
        resp = Response(status=416)
        resp.headers["Content-Range"] = f"bytes */{mp3_size}"
        return resp

    byte2 = min(byte2, mp3_size - 1)
    length = byte2 - byte1 + 1

    print(
        "[STREAM] 206:",
        f"bytes {byte1}-{byte2}/{mp3_size}",
        "length:", length,
        flush=True
    )

    resp = Response(
        generate_range(byte1, length),
        status=206,
        mimetype="audio/mpeg",
        direct_passthrough=True,
    )

    resp.headers["Content-Range"] = (
        f"bytes {byte1}-{byte2}/{mp3_size}"
    )
    resp.headers["Content-Length"] = str(length)
    resp.headers["Accept-Ranges"] = "none"
    resp.headers["Connection"] = "close"

    return resp




API_KEY = (
    "4VCYIJUCDLOUELGD1V8WBVYBNVDYOXEWSLLZDONGBBDFVXTZJRXPR29JRLQFO6ZE"
)


INITIAL_AES_KEY = "VBK1FSUEXHTSDBJJ"



EXPECTED_PASSWORD = os.getenv("DEEZER_PASSWORD")

USER_ID = os.getenv("DEEZER_USER_ID", "123456789")
BLOG_NAME = os.getenv("DEEZER_BLOG_NAME", "Deezer User")





def get_request_data():
    raw = request.get_data(as_text=True)

    

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}
        
def mobile_pageAlbum(data):
    album_id = str(data.get("ALB_ID", ""))

    if not album_id.isalnum():
        return {"error": ["Invalid album ID"], "results": []}

    album_path = os.path.join(ALBUMS_DIR, album_id + ".json")

    if not os.path.isfile(album_path):
        return {"error": ["Album not found"], "results": []}

    with open(album_path, "r", encoding="utf-8") as f:
        return json.load(f)
        
def lim_ao(value):
    return "".join(format(ord(c), "02x") for c in value)


def lim_an(value):
    return "".join(
        chr(int(value[i:i + 2], 16))
        for i in range(0, len(value), 2)
    )






def aes_encrypt_raw(value, key):

    value += "0" * ((-len(value)) % 32)

    raw = bytes.fromhex(value)

    cipher = AES.new(
        key[:16].encode("ascii"),
        AES.MODE_ECB
    )

    encrypted = cipher.encrypt(raw)

    return encrypted.decode("latin-1")


def aes_decrypt_raw(value, key):

    raw = bytes.fromhex(value)

    cipher = AES.new(
        key[:16].encode("ascii"),
        AES.MODE_ECB
    )

    decrypted = cipher.decrypt(raw)

    return decrypted.decode("latin-1")


def encrypt_client_value(value, key):

    return lim_ao(
        aes_encrypt_raw(
            lim_ao(value),
            key
        )
    )






def create_authentication_token():

    payload = "DEEZER_MOCK_AUTHENTICATION_PAYLOAD_".ljust(64, "0")[:64]

    token_key = secrets.token_hex(8).upper()
    br_key = secrets.token_hex(8).upper()
    bs_key = secrets.token_hex(8).upper()

    plaintext = (
        payload
        + token_key
        + br_key
        + bs_key
    )

    
    encrypted = aes_encrypt_raw(
        lim_ao(plaintext),
        INITIAL_AES_KEY
    )

    
    token = lim_ao(encrypted)

    
    auth_token = lim_ao(
        aes_encrypt_raw(
            lim_ao(payload),
            token_key
        )
    )

    return token, auth_token


TOKEN, EXPECTED_AUTH_TOKEN = create_authentication_token()





sessions = {}


def create_session(auth_token):
    session_id = secrets.token_hex(24)

    sessions[session_id] = {
        "auth_token": auth_token,
        "created": time.time()
    }

    return session_id






def api_error(code, message):
    return jsonify({
        "error": {
            "code": code,
            "message": message
        }
    })


def api_success(results):
    return jsonify({
        "results": results
    })





def mobile_auth():
    log.info("mobile_auth")

    data = {
        "error": [],

        "results": {
            "IS_LAST_RELEASE": True,
            "CURRENT_VERSION": "2.401",
            "LOGIN_TEXT": "Your music. Your flow.",

            "TOKEN": TOKEN,

            "POLICY": {
                "S_MOD": "1",
                "S_SMARTRADIO": "1",
                "S_RADIO": "1",
                "S_STREAMING": "1",
                "S_PREMIUM": "1",
                "S_ALC": "0"
            },
			
    		"CONFIG": {
    			"URL_NO_FREEMIUM": r"http://127.0.0.1/webview/no_freemium",
    			"TOTAL_TRACKS": "120",
    			"HOST_STREAM_MOB": r"http://127.0.0.1/songs/{2}.mp3",
    			"HOST_STREAM_PREVIEW": r"http://127.0.0.1/songs/{2}.mp3",
    			"HOST_CUSTOS_MOB": r"http://127.0.0.1/mobile/custos/",
    			"HOST_API_MOB": r"http://127.0.0.1/1.0/gateway.php",
    			"HOST_IMAGES": r"http://127.0.0.1/images",
    			"HOST_FILES": r"http://127.0.0.1",
    			"HOST_CONTENT": r"http://127.0.0.1",
    			"URL_SUPPORT": r"http://127.0.0.1",
    			"HOST_LIVE": r"http://127.0.0.1",
    			"HOST_MESSAGING": "127.0.0.1",
    			"HOST_SITE": r"http://127.0.0.1",
    			"HOST_UPLOAD": r"http://127.0.0.1",
    			"URL_REGISTER": r"http://127.0.0.1/register.php",
    			"URL_FACEBOOK_LOGIN": r"http://127.0.0.1/facebook.php?token=%@&fb_user_id=%@&from_mobile=1",
    			"URL_PASSWORD_RESET": r"http://127.0.0.1/password/reset",
    			"URL_PAYMENT": r"http://127.0.0.1/payment/?webview=True",
    			"URL_MEDIA": r"http://127.0.0.1",
    			"GAIN": {
    				"TARGET": "-15",
    				"ADS": "-13"
    			},
    			"URL_VENDOR_LIST": r"http://127.0.0.1//legal/vendor-list",
    			"GZIP": False,
    			"POP": "fr",
    			"FB_ONLY": 0,
    			"FB_PUBLISH": 0,
    			"RESTRICTED": False,
    			"REGISTRATION": {},
    			"POLICY": "MOBILE",
    			"APPSTUDIO": False,
    			"PAYMENT_METHODS": {
    				"VISA": True,
    				"MASTERCARD": True,
    				"AMEX": True,
    				"PAYPAL": True,
    				"IOS": True
    			},
    			"AD_RULES": {
    				"audio": {
    					"default": {
    						"start": 1,
    						"interval": 3,
    						"unit": "track"
    					}
    				},
    				"display": {
    					"interstitial": {
    						"start": 900,
    						"interval": 900,
    						"unit": "sec"
    					}
    				},
    				"big_native_ads_home": {
    					"iphone": {
    						"enabled": False
    					},
    					"ipad": {
    						"enabled": False
    					},
    					"android": {
    						"enabled": False
    					},
    					"android_tablet": {
    						"enabled": False
    					}
    				}
    			},
    			"REG_FLOW": ["email"],
    			"LOGIN_FLOW": ["email"],
    			"VOICECALLBACK": False
    		},

            "TIMESTAMP": int(time.time()),
            "COUNTRY": "US"
        }
    }
    json_str = json.dumps(data)
    json_str = json_str.replace("/", r"\/")
    return Response(json_str, mimetype="application/json")






def api_check_token():
    auth_token = request.args.get("auth_token")

    if not auth_token:
        data = request.get_json(silent=True) or {}
        auth_token = data.get("auth_token", "")

    if not auth_token:
        auth_token = request.form.get("auth_token", "")

    log.info("api_checkToken")

    if not auth_token:
        return api_error(
            "USER_AUTH_ERROR",
            "Missing authentication token"
        )

    
    if auth_token != EXPECTED_AUTH_TOKEN:
        log.warning("Received unexpected auth_token")

        return api_error(
            "USER_AUTH_ERROR",
            "Invalid authentication token"
        )

    session_id = create_session(auth_token)

    log.info("Created session: %s", session_id)

    
    return api_success(session_id)






def mobile_user_auth():
    log.info("mobile_userAuth")

    sid = request.args.get("sid", "")

    if sid not in sessions:
        return api_error(
            "SESSION_ERROR",
            "Invalid session"
        )

    
    data = get_request_data()

    email = data.get("mail", "")
    encrypted_password = data.get("password", "")
    device_serial = data.get("device_serial", "")
    platform = data.get("platform", "")

    log.info("Login parameters: %s", {
        key: ("<redacted>" if key in ("mail", "password") else value)
        for key, value in data.items()
    })

    
    
    
    
    

    if not encrypted_password:
        return api_error(
            "USER_AUTH_ERROR",
            "Missing password"
        )

    if EXPECTED_PASSWORD and encrypted_password != EXPECTED_PASSWORD:
        return api_error(
            "USER_AUTH_ERROR",
            "Incorrect password"
        )

    
    

    return api_success({
          "USER_ID": USER_ID,
          "BLOG_NAME": BLOG_NAME,
          "EMAIL": "test@mail.com",
          "USER_GENDER": "M",
          "USER_AGE": "18",
          "AGE": "18",
          "PREMIUM": {
              "OFFER_ID": "1000001",
              "DATE_START": "2025-01-06 00:00:00",
              "DATE_END": "2030-01-06 00:00:00",
              "PLATEFORM": "mobile",
              "TRY_AND_BUY": "1",
              "COMMITMENT": "1",
              "RENEWAL": "1",
              "STATUS": True,
              "OFFER_NAME": "Deezer Premium",
              "IS_B2B": True,
              "TRY_AND_BUY_CC_DONE": True,
          },
		  "WAITING_FOR_PAYMENT": False,
          "STATUS": "1",
          "OFFER_ID": "1000001",
          "OFFER_NAME": "Deezer Premium",
          "CAN_STREAM": "1",
          "CAN_STREAM_HQ": "1",
          "NO_AD": "1",
          "DEVICE_ALREADY_LINKED": "0",
          "USER_ORANGE_PAIRED": False,
          "PROFIL": {
              "ROAMING": "0",
              "NETWORK": "",
              "ACTIVE": {"ORANGE": False, "BANQUE_POSTALE": True},
              "CUSTOM": {"NAME": "", "TYPE": ""},
          },
          "AUDIO_SETTINGS": {
              "default_preset": "balanced",
              "mobile_streaming": "high",
              "wifi_streaming": "high",
          },
      })






DEEZER_API_BASE = os.getenv("DEEZER_API_BASE", "https://api.deezer.com")
SEARCH_LIMIT = int(os.getenv("DEEZER_SEARCH_LIMIT", "200"))

def deezer_get_json(path, params=None):
    
    url = DEEZER_API_BASE.rstrip("/") + "/" + path.lstrip("/")
    if params:
        url += "?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Deezer-2.401-Mock/1.0"}
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        log.error("Deezer API HTTP %s: %s", exc.code, body[:500])
        raise RuntimeError("Deezer API returned HTTP %s" % exc.code)
    except Exception as exc:
        log.exception("Deezer API request failed")
        raise RuntimeError("Could not reach Deezer API: %s" % exc)


def adapt_deezer_track(track):
    track_id = str(track.get("id", "0"))
    album = track.get("album") or {}
    artist = track.get("artist") or {}

    
    
    
    md5_origin = hashlib.md5(
        ("deezer-track-" + track_id).encode("utf-8")
    ).hexdigest()

    cover = album.get("cover_medium") or album.get("cover") or ""
    if isinstance(cover, str) and cover.startswith("http://"):
        cover = "https://" + cover[len("http://"):]

    return {
        "SNG_ID": track_id,
        "MD5_ORIGIN": md5_origin,
        "SNG_TITLE": str(track.get("title") or ""),
        "UPLOAD_ID": "0",
        "ALB_ID": str(album.get("id") or "0"),
        "ALB_TITLE": str(album.get("title") or ""),
        "ALB_PICTURE": str(album.get("md5_image") or ""),
        "ART_ID": str(artist.get("id") or "0"),
        "ART_NAME": str(artist.get("name") or ""),
        "SMARTRADIO": "0",
        "DATE_START": "0",
        "DATE_START_PREMIUM": "0",
        "STATUS": "1",
        "S_MOD": "0",
        "S_PREMIUM": "1",
        
        
        
        "FILESIZE": "1",
        "FILESIZE_AAC_64": "0",
        "FILESIZE_MP3_128": "0"
    }


def get_search_request():
    data = get_request_data()
    if not isinstance(data, dict):
        data = {}

    query = data.get("QUERY") or request.args.get("QUERY") or ""
    filter_type = str(data.get("FILTER") or "ALL").upper()
    output_type = str(data.get("OUTPUT") or "TRACK").upper()

    return str(query).strip(), filter_type, output_type


def search_music():
    query, filter_type, output_type = get_search_request()
    log.info("search_music query=%r filter=%s output=%s",
             query, filter_type, output_type)

    if not query:
        return jsonify({"error": [], "results": {"data": []}})

    try:
        with open("tracks.json", "r", encoding="utf-8") as f:
            local_tracks = json.load(f)
            needle = query.casefold()
            seen_albums = set()
            raw_tracks = []

            for track in local_tracks:
                if filter_type == "ALBUM" or filter_type == "ARTIST":
                    alb_title = str(track.get("ALB_TITLE", ""))
                    
                    if needle in alb_title.casefold() and alb_title not in seen_albums:
                        seen_albums.add(alb_title)
                        raw_tracks.append(track)
                else:
                        search_text = f"{track.get('SNG_TITLE', '')} {track.get('ART_NAME', '')} {track.get('ALB_TITLE', '')}"
                        if needle in search_text.casefold():
                            raw_tracks.append(track)
        
        tracks = raw_tracks
			 
        
        
        return jsonify({
            "error": [],
            "results": {
                "data": tracks,
                "count": len(tracks),
				"checksum": "efec189467215671b35305466c41190c",
				"index": 1,
                "total": int(len(tracks)),
                "next": None
            }
        })

    except Exception as exc:
        log.error("search_music failed: %s", exc)
        return jsonify({
            "error": [],
            "results": {"data": []},
            "mock_error": str(exc)
        }), 502


def song_get_data():
    data = get_request_data()
    song_id = str(data.get("SNG_ID") or request.args.get("SNG_ID") or "").strip()

    if not song_id:
        return jsonify({"error": [], "results": {}})

    log.info("song_getData SNG_ID=%s", song_id)

    try:
        with open("tracks.json", "r", encoding="utf-8") as f:
            local_tracks = json.load(f)

        upstream = next(
            (
                track for track in local_tracks
                if str(track.get("SNG_ID", "")) == str(song_id)
            ),
            None
        )
        if not isinstance(upstream, dict) or upstream.get("error"):
            return jsonify({"error": [], "results": {}}), 404

        result = upstream
        
        return jsonify({"error": [], "results": {
                "data": result,
                "count": len(result),
				"checksum": "efec189467215671b35305466c41190c",
				"index": 1,
                "total": int(len(result)),
                "next": None
            }})

    except Exception as exc:
        log.error("song_getData failed: %s", exc)
        return jsonify({
            "error": [],
            "results": {},
            "mock_error": str(exc)
        }), 502






@app.route("/1.0/gateway.php", methods=["GET", "POST"])
def gateway():
    method = request.args.get("method", "")

    
    
    if not method:
        data = get_request_data()
        method = data.get("method", "") if isinstance(data, dict) else ""

    if not method:
        method = request.form.get("method", "")

    log.info("%s %s", request.method, method)

    if method == "mobile_auth":
        return mobile_auth()

    if method == "api_checkToken":
        return api_check_token()

    if method == "mobile_userAuth":
        return mobile_user_auth()
        
    if method == "mobile.pageAlbum":
        data = get_request_data()
        return mobile_pageAlbum(data)

    if method == "search_music":
        return search_music()

    if method == "song_getData":
        return song_get_data()

    log.warning("Unknown API method: %s", method)
    return api_error("REQUEST_ERROR", "Unknown method: " + str(method))






@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "server": "Deezer 2.401 Mock API",
        "status": "online",
        "gateway": "/1.0/gateway.php"
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})






if __name__ == "__main__":
    print("======================================")
    print(" Deezer 2.401 Mock API")
    print("======================================")
    print("Gateway: http://0.0.0.0:80/1.0/gateway.php")
    print("AES token initialized.")
    print("Search adapter: " + DEEZER_API_BASE)
    print("Expected auth_token:", EXPECTED_AUTH_TOKEN)
    print("======================================")

    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "80")),
        debug=False
    )
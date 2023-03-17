from typing import Tuple
from flask import Flask, request, abort
from werkzeug.urls import url_join
from datetime import datetime, timedelta
from os import urandom
from base64 import urlsafe_b64encode, urlsafe_b64decode
from hashlib import blake2b
from hmac import compare_digest

token_timeout = timedelta(seconds=300)  # time until resolved code can be retrieved
max_requests = 10                      # maximum number of pending requests
server_secret = urandom(16)            # randomized at startup

app = Flask(__name__)
token_cache = {}
oauth_redirect_url = url_join(app.config['APPLICATION_ROOT'], 'auth_redirect')

entropy_bytes = 6
timestamp_bytes = 4

def keyed_hash(payload: bytes) -> bytes:
    h = blake2b(key=server_secret, digest_size=entropy_bytes)
    h.update(payload)
    return h.digest()


def random_key(num_bytes: int = entropy_bytes) -> Tuple[bytes, datetime]:
    time_created = datetime.now()
    r = urandom(num_bytes)
    t = int(datetime.now().timestamp()).to_bytes(timestamp_bytes)
    h = keyed_hash(r + t)
    return urlsafe_b64encode(r + t + h), time_created


def valid_key(key: bytes) -> Tuple[bool, datetime]:
    payload = urlsafe_b64decode(key)
    if len(payload) == 2 * entropy_bytes + timestamp_bytes:
        r = payload[:entropy_bytes]
        t = payload[entropy_bytes:entropy_bytes + timestamp_bytes]
        h = payload[entropy_bytes + timestamp_bytes:]
        return compare_digest(keyed_hash(r + t), h), datetime.fromtimestamp(int.from_bytes(t))
    return False, None


class Token:
    def __init__(self, oauth_state: str, valid_until: datetime, success: bool, oauth_code: str):
        self.oauth_state = oauth_state
        self.valid_until = valid_until
        self.success = success
        self.oauth_code = oauth_code

    def expired(self) -> bool:
        return datetime.now() > self.valid_until


def cleanup():
    for key in list(token_cache.keys()):
        if token_cache[key].expired():
            del token_cache[key]


@app.route('/register')
def register():
    cleanup()
    if len(token_cache) >= max_requests:
        abort(429)  # don't DoS us
    else:
        state, time_created = random_key()
        return {
            'redirect_url': oauth_redirect_url,
            'state': state.decode('utf-8'),
            'created_at': time_created,
            'valid_until': time_created + token_timeout,
        }


@app.route('/auth_redirect')
def redirect():
    state = request.args.get('state').encode('utf-8')
    code = request.args.get('code')
    if state:
        if code:
            valid, created_at = valid_key(state)
            if valid:
                valid_until = created_at + token_timeout
                if valid_until >= datetime.now():
                    cleanup()
                    token_cache[state] = Token(
                        state, valid_until, True, code
                    )
                    return {
                        'status': 'success',
                    }
                else:
                    abort(400, "supplied 'state' expired")    
            else:
                abort(400, "invalid 'state' supplied")
        else:   
            abort(400, "parameter 'code' missing")
    else:
        abort(400, "parameter 'state' missing")


@app.route('/poll')
def poll():
    state = request.args.get('state', '').encode('utf-8')
    if state != '':
        valid, created_at = valid_key(state)
        if valid:
            valid_until = created_at + token_timeout
            if valid_until >= datetime.now():
                if state in token_cache:
                    code = token_cache[state].oauth_code
                    del token_cache[state]
                    return {
                        'status': 'success',
                        'code': code
                    } 
                else:
                    return {'status': 'pending'}
            else:
                return {'status': 'timeout'}
        else:
            abort(400, "invalid 'state' supplied")
    else:
        abort(400, "parameter 'state' missing")
                

if __name__ == '__main__':
    app.run(port=8080)


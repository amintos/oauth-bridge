# OAuth Bridge

Small service to handle OAuth redirect URLs at a public endpoint for local-first workflows

```bash
pip install git+https://github.com/amintos/oauth-bridge.git 
```

# Server Setup Example

Public server example. This will run a development server:
```bash
python3.11 -m flask --app oauth_bridge.server run --port 9001
```

If the server has an nginx setup, use it as reverse proxy and mount it under `/oauth_bridge`.

```
location /oauth_bridge {
                rewrite /oauth_bridge/(.*) /$1  break;
                proxy_pass http://localhost:9001/;
                proxy_set_header Host $host;
                proxy_set_header X-Real-IP $remote_addr;
        }

```

If not in use, stop the server. For permanent usage, consider using WSGI.

# Client Usage

```python
from oauth_bridge.client import github_oauth
github_oauth('<client-id>', '<client-secret>', 'https://<server>/oauth_bridge/')
```

The script will open a webbrowser. If not, use the generated URL to authenticate. The function polls automatically and returns GitHub's JSON response as dictionary or raises an exception after the timeout.

Result:

```
[OAuth] Authenticate via https://github.com/login/oauth/authorize?client_id=<client-id>&state=<state>&redirect_uri=https://<server>/oauth_bridge/auth_redirect

{'access_token': '<token>',
 'token_type': 'bearer',
 'scope': ''}
```

# Security

The client first sends a GET request to the `/register` endpoint and obtains a `state` token. This token is used in the OAuth authentication URL and passed back via the redirect `/auth_redirect`. The server caches the resulting OAuth token from the redirect URL and provides its result if and only if polled via `/poll?state=<state>` within five minutes. Both the `state` and the returned `code` should only be shared with the server and the OAuth API.

The server will generate **authenticated** `state` tokens to be passed to the OAuth API and used as polling key using random data, the current timestamp, and an HMAC signature. They expire after five minutes. The server will accept neither polling nor OAuth redirects containing a `state` token not signed by itself. Restarting the server renders them invalid. A cached `code` can only be retrieved once and is deleted from the server afterwards.

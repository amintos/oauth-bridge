from requests import get, post
from urllib.parse import urljoin
import time
import webbrowser


def github_oauth(client_id, client_secret, bridge_endpoint, timeout=60, poll_interval=2):
    bridge_request = get(urljoin(bridge_endpoint, 'register')).json()
    redirect_url = urljoin(bridge_endpoint, bridge_request['redirect_url'])
    state = bridge_request['state']

    user_url = "https://github.com/login/oauth/authorize" + \
        f"?client_id={client_id}&state={state}&redirect_uri={redirect_url}"

    webbrowser.open(user_url)

    started = time.time()
    while started + timeout >= time.time():
        time.sleep(poll_interval)
        bridge_poll = get(urljoin(bridge_endpoint, f'poll?state={state}')).json()
        print(bridge_poll)
        if bridge_poll['status'] == 'success':
            code = bridge_poll['status']
            break
    else:
        raise TimeoutError()
    
    token_url = "https://github.com/login/oauth/access_token"

    token_response = post(token_url,
        data={'client_id': client_id,
              'client_secret': client_secret,
              'code': code})
    print(token_response)

    return token_response.json()

    





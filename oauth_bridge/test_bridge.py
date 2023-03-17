import pytest
import json

from server import app

def test_roundtrip():
    with app.test_client() as client:
        response = client.get('/register')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'state' in data
        assert 'redirect_url' in data
        state = data['state']
        redirect_url = data['redirect_url']

        response = client.get(f'/poll?state={state}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'status' in data
        assert data['status'] == 'pending'
        
        response = client.get(f'{redirect_url}?state={state}&code=secret')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'status' in data
        assert data['status'] == 'success'

        response = client.get(f'/poll?state={state}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'status' in data
        assert 'code' in data
        assert data['status'] == 'success'
        assert data['code'] == 'secret'

if __name__ == '__main__':
    pytest.main()
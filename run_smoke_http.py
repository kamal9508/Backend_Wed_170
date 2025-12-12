import os
import time
import httpx

BASE = os.getenv('BASE_URL', 'http://127.0.0.1:8000')

client = httpx.Client(timeout=20.0)

print('Waiting a few seconds for service...')
time.sleep(3)

print('Creating organization...')
resp = client.post(f'{BASE}/org/create', json={
    'organization_name': 'SmokeOrg',
    'email': 'admin@smoke.local',
    'password': 'smokePass123'
})
print('Create status:', resp.status_code)
print(resp.text)

print('\nLogging in admin...')
resp2 = client.post(f'{BASE}/admin/login',
                    json={'email': 'admin@smoke.local', 'password': 'smokePass123'})
print('Login status:', resp2.status_code)
print(resp2.text)

if resp2.status_code == 200:
    token = resp2.json().get('access_token')
    print('\nToken received:', token)
    # call health
    print('\nCalling /health')
    h = client.get(f'{BASE}/health')
    print('Health status', h.status_code, h.text)
else:
    print('Login failed; skipping health check')

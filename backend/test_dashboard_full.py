from fastapi.testclient import TestClient
import server

client = TestClient(server.app)

paths = [
    '/dashboard',
    '/dashboard/static/index.html',
    '/dashboard/api/summary',
    '/dashboard/api/sessions',
    '/dashboard/api/batches/active',
]
for path in paths:
    r = client.get(path, follow_redirects=False)
    print('PATH', path)
    print('STATUS', r.status_code)
    print('LOCATION', r.headers.get('location'))
    print('BODY', r.text[:500])
    print('---')

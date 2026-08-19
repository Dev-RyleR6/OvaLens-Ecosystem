from fastapi.testclient import TestClient
import server

client = TestClient(server.app)
paths = [
    '/dashboard/api/summary',
    '/dashboard/api/sessions',
    '/dashboard/api/batches/active',
    '/dashboard/api/tables',
]
for path in paths:
    r = client.get(path)
    print('PATH', path, 'STATUS', r.status_code)
    print(r.text[:1000])
    print('---')

# test first table if available
r = client.get('/dashboard/api/tables')
if r.status_code == 200:
    tables = r.json()
    if tables:
        table = tables[0]
        r2 = client.get(f'/dashboard/api/tables/{table}')
        print('TABLE', table, 'STATUS', r2.status_code)
        print(r2.text[:1000])

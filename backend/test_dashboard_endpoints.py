from fastapi.testclient import TestClient
import server

client = TestClient(server.app)
paths = ['/dashboard/api/summary', '/dashboard/api/sessions', '/dashboard/api/batches/active']
for path in paths:
    r = client.get(path)
    print(path, r.status_code)
    print(r.text)
    print('----')

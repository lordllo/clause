from fastapi.testclient import TestClient
from app.main import app

def test_upload_review_roundtrip(monkeypatch):
    monkeypatch.setenv('ANALYSIS_PROVIDER','demo')
    with TestClient(app) as client:
        p = client.get('/policies/default').json()
        response = client.post('/documents', files={'file': ('test.txt', b'1. Governing Law\nThis agreement is governed by New York law.', 'text/plain')})
        assert response.status_code == 201
        id = response.json()['id']
        review = client.post(f'/documents/{id}/reviews', json=p)
        assert review.status_code == 201
        assert review.json()['findings'][0]['citation_verified']
        assert client.get(f'/documents/{id}').json()['reviews'][0]['policy_snapshot'] == p
        assert client.get(f'/documents/{id}/source').content.startswith(b'1. Governing')
        assert client.post('/policies', json=p).status_code == 201
        assert client.get('/policies').json()
        assert client.post('/documents', files={'file': ('bad.txt', b'')}).status_code == 422
        assert client.get('/documents/not-real').status_code == 404

from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app import hosting
from app.db import DemoAccess, Session

@pytest.fixture
def hosted(monkeypatch):
    monkeypatch.setenv('PUBLIC_DEMO','true')
    monkeypatch.setenv('DEMO_SESSION_SECRET','a-test-secret-with-more-than-32-characters')
    monkeypatch.setenv('DEMO_COOKIE_SECURE','false')
    monkeypatch.setenv('ANALYSIS_PROVIDER','demo')
    hosting._limits.clear()
    with TestClient(app) as client:
        yield client

def test_browser_sessions_isolate_uploads_policies_reviews(hosted):
    a=hosted
    with TestClient(app) as b:
        a.get('/health');b.get('/health')
        upload=a.post('/documents',files={'file':('private.txt',b'1. Law\nThis agreement is governed by New York law.')})
        assert upload.status_code==201
        id=upload.json()['id'];p=a.get('/policies/default').json()
        assert a.get('/documents/'+id).status_code==200
        assert b.get('/documents/'+id).status_code==404
        assert b.get('/documents/'+id+'/source').status_code==404
        assert id not in [d['id'] for d in b.get('/documents').json()]
        assert a.post('/policies',json=p).status_code==201
        assert a.get('/policies').json() and b.get('/policies').json()==[]
        assert b.post('/documents/'+id+'/reviews',json=p).status_code==404
        assert a.post('/documents/'+id+'/reviews',json=p).status_code==201
        sample=next(s for s in a.get('/samples').json() if s['collection']=='Common Paper standards')
        id=sample['document_id']
        result=a.post('/documents/'+id+'/reviews',json=p)
        assert result.status_code==201
        assert result.json()['id'] not in [r['id'] for r in b.get('/documents/'+id).json()['reviews']]

def test_cross_origin_write_blocked(hosted):
    p=hosted.get('/policies/default').json()
    assert hosted.post('/policies',json=p,headers={'Origin':'https://unrelated.example'}).status_code==403
    assert hosted.post('/policies',json=p,headers={'Origin':'http://testserver'}).status_code==201

def test_demo_upload_limit(hosted):
    for i in range(5):
        assert hosted.post('/documents',files={'file':(f'{i}.txt',b'1. Law\nNew York applies.')}).status_code==201
    assert hosted.post('/documents',files={'file':('six.txt',b'1. Law\nNew York applies.')}).status_code==429

def test_expired_uploads_are_removed(hosted):
    id=hosted.post('/documents',files={'file':('expired.txt',b'1. Law\nNew York applies.')}).json()['id']
    with Session() as session:
        access=session.get(DemoAccess,id)
        access.created_at=datetime.now(timezone.utc)-timedelta(hours=2)
        session.commit()
    hosting._last_cleanup=0
    hosting.cleanup()
    assert hosted.get('/documents/'+id).status_code==404

def test_invalid_cookie_does_not_reuse_owner(hosted):
    hosted.get('/health')
    first=hosted.cookies.get('clause_demo')
    original=hosting.identity(first)[0]
    tampered=first[:-1]+('0' if first[-1]!='0' else '1')
    assert hosting.identity(tampered)[0]!=original

def test_public_mode_rejects_paid_provider(monkeypatch):
    monkeypatch.setenv('PUBLIC_DEMO','true')
    monkeypatch.setenv('ANALYSIS_PROVIDER','openai')
    with pytest.raises(RuntimeError): hosting.validate_hosting()

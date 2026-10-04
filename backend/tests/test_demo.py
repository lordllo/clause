import hashlib
import json
from pathlib import Path
from fastapi.testclient import TestClient
from app.db import Session, SampleRecord
from app.demo import seed
from app.main import app
from app.schemas import DEFAULT_POLICY
from app.analysis import analyze

ROOT=Path(__file__).resolve().parents[2]/'samples'

def test_public_corpus_integrity():
    manifest=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
    assert len(manifest)==71
    assert len({x['key'] for x in manifest})==71
    assert len({x['category'] for x in manifest})>=8
    for item in manifest:
        raw=(ROOT/item['file']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==item['sha256']
        assert item['source_url'].startswith('https://github.com/')
        assert item['license']=='CC BY 4.0'
        text=raw.decode('utf-8')
        for annotation in item['annotations']:
            for answer in annotation['answers']:
                assert text[answer['start']:answer['start']+len(answer['text'])]==answer['text']

def test_seed_is_idempotent_and_exposes_provenance(monkeypatch):
    monkeypatch.setenv('ANALYSIS_PROVIDER','demo')
    with TestClient(app) as client:
        assert seed()['added']==73
        assert seed()['added']==0
        samples=client.get('/samples').json()
        assert len(samples)==73
        public=next(s for s in samples if s['collection']=='CUAD commercial contracts')
        detail=client.get('/documents/'+public['document_id']).json()
        assert detail['annotations'] and detail['sample']['source_url']
        review=client.post('/documents/'+public['document_id']+'/reviews',json=DEFAULT_POLICY.model_dump())
        assert review.status_code==201
        assert all(f['status']=='needs_review' for f in review.json()['findings'])
        fictional=next(s for s in samples if s.get('fictional'))
        assert client.get('/documents/'+fictional['document_id']).json()['reviews']
        assert len(client.get('/policies/presets').json())==4

def test_real_contract_demo_abstains(monkeypatch):
    monkeypatch.setenv('ANALYSIS_PROVIDER','demo')
    c={'id':'law','page':1,'heading':'Law','text':'This agreement is governed by New York law.'}
    result=analyze(DEFAULT_POLICY,[c],conservative=True)
    assert result['findings'][0]['citation_verified']
    assert all(f['status']=='needs_review' for f in result['findings'])

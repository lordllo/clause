"""Idempotent offline seeding of licensed public snapshots and fictional fixtures."""
import hashlib
import json
from pathlib import Path
from uuid import uuid4
from sqlalchemy import select
from .db import Session, Document, Clause, SampleRecord, Review, DemoAccess, DATA_DIR
from .parsing import parse
from .schemas import DEFAULT_POLICY

SAMPLES = Path(__file__).resolve().parents[2] / 'samples'
FIXTURES = Path(__file__).resolve().parents[2] / 'fixtures'

def summary(sample):
    metadata = sample.metadata_json
    return {k: v for k, v in metadata.items() if k != 'annotations'} | {
        'document_id':sample.document_id,
        'annotation_count':sum(len(a['answers']) for a in metadata.get('annotations', [])),
        'annotated_categories':sum(bool(a['answers']) for a in metadata.get('annotations', [])),
    }

def seed():
    manifest = SAMPLES / 'manifest.json'
    if not manifest.exists(): return {'added':0}
    entries = json.loads(manifest.read_text(encoding='utf-8'))
    examples = [
        ('vendor-risky.txt', 'Northstar Systems — Vendor terms',
         'Sample agreement with five terms to negotiate: governing law, renewal, liability, data use, and breach notice. Northstar Systems is a fictional supplier.'),
        ('vendor-compliant.txt', 'Cedarworks — Revised vendor terms',
         'Sample agreement aligned with the five standard policy checks. Compare its terms with the Northstar example. Cedarworks is a fictional supplier.'),
    ]
    for name, title, description in examples:
        entries.append({'key':name.removesuffix('.txt'),'title':title,'file':name,
            'collection':'Example reviews','category':'Vendor review','publisher':'Clause',
            'description':description,
            'license':'Project fixture','source_url':None,'annotations':[], 'fictional':True})
    added = 0
    with Session() as session:
        for entry in entries:
            existing = session.get(SampleRecord, entry['key'])
            if existing:
                # Refresh presentation/provenance metadata for the same content.
                doc = session.get(Document, existing.document_id)
                if entry.get('sha256') and doc.digest != entry['sha256']:
                    raise ValueError('Sample content changed; import as a new snapshot before replacing stored documents.')
                existing.metadata_json = entry
                doc.name = entry['title']
                continue
            source = (FIXTURES if entry.get('fictional') else SAMPLES) / entry['file']
            content = source.read_bytes()
            digest = hashlib.sha256(content).hexdigest()
            if entry.get('sha256') and digest != entry['sha256']:
                raise ValueError(f"Sample checksum mismatch: {entry['key']}")
            parsed = parse(content, '.txt')
            id = str(uuid4())
            target = Path(DATA_DIR) / 'uploads' / (id + '.txt')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            session.add(Document(id=id, name=entry['title'], digest=digest, source_path=str(target)))
            session.flush()
            session.add_all(Clause(document_id=id, **c) for c in parsed)
            session.add(SampleRecord(key=entry['key'], document_id=id, metadata_json=entry))
            # Prepopulate only synthetic fixture reviews; never charge a provider on startup.
            if entry.get('fictional'):
                from .analysis import demo, retrieve, verify
                findings=[]
                for rule in DEFAULT_POLICY.rules:
                    candidates=retrieve(rule, parsed)
                    item=verify(demo(rule, candidates), candidates)
                    item.update(rule_name=rule.name, policy=rule.instruction, severity=rule.severity)
                    findings.append(item)
                review_id = str(uuid4())
                session.add(Review(id=review_id, document_id=id, policy=DEFAULT_POLICY.model_dump(),
                    result={'provider':'demo','model':None,'pipeline_version':'1','findings':findings}))
                session.add(DemoAccess(resource_id=review_id,kind='review',owner='public_sample'))
            added += 1
        session.commit()
    return {'added':added}

def annotation_view(metadata, clauses):
    normalized = [(' '.join(c['text'].split()), c['id']) for c in clauses]
    result=[]
    for annotation in metadata.get('annotations', []):
        if not annotation['answers']: continue
        answers=[]
        for answer in annotation['answers']:
            quote = ' '.join(answer['text'].split())
            id = next((id for text, id in normalized if quote in text), None)
            answers.append({**answer, 'clause_id':id})
        result.append({'label':annotation['label'],'answers':answers})
    return result

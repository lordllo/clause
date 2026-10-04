"""Evaluate lexical retrieval against the bundled CUAD source annotations.

This measures retrieval, not model comprehension or policy compliance.
"""
import argparse
import hashlib
import json
from pathlib import Path
from app.analysis import retrieve
from app.parsing import parse
from app.schemas import Rule

ROOT = Path(__file__).resolve().parents[1] / 'samples'
QUERIES = {
    'Governing Law':['governed','governing','law'],
    'Renewal Term':['renewal','renew','term'],
    'Notice Period To Terminate Renewal':['notice','renewal','terminate'],
    'Cap On Liability':['liability','cap','damages'],
    'Termination For Convenience':['terminate','termination','convenience'],
    'Anti-Assignment':['assign','assignment','consent'],
    'License Grant':['license','grant','rights'],
    'Exclusivity':['exclusive','exclusivity'],
}

def evaluate():
    manifest=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
    integrity=0; counts={}; skipped=0; documents=0
    for entry in manifest:
        raw=(ROOT/entry['file']).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=entry['sha256']: raise ValueError('Checksum mismatch')
        if not entry['annotations']: continue
        documents+=1; text=raw.decode('utf-8'); clauses=parse(raw,'.txt')
        for annotation in entry['annotations']:
            for answer in annotation['answers']:
                if text[answer['start']:answer['start']+len(answer['text'])]!=answer['text']:
                    raise ValueError('Annotation offset mismatch')
                integrity+=1
            if annotation['label'] not in QUERIES: continue
            rule=Rule(id='query',name=annotation['label'],instruction='Retrieve labeled source evidence.',keywords=QUERIES[annotation['label']])
            retrieved={c['id'] for c in retrieve(rule,clauses)}
            for answer in annotation['answers']:
                normalize=lambda s:' '.join(s.split())
                relevant={c['id'] for c in clauses if normalize(answer['text']) in normalize(c['text'])}
                if not relevant: skipped+=1;continue
                row=counts.setdefault(annotation['label'],{'answers':0,'hits':0})
                row['answers']+=1;row['hits']+=bool(retrieved&relevant)
    total=sum(c['answers'] for c in counts.values());hits=sum(c['hits'] for c in counts.values())
    return {'dataset':'Bundled CUAD subset', 'documents':documents,'verified_annotation_offsets':integrity,
        'answer_recall_at_5':round(hits/total,4) if total else None,'retrieval_answers':total,
        'cross_passage_answers_excluded':skipped,
        'by_label':{label:{**c,'recall_at_5':round(c['hits']/c['answers'],4)} for label,c in counts.items()},
        'limitations':'Eight keyword queries on a selected 60-contract subset. Multi-passage answers excluded. Not a held-out test; no model or legal correctness measured.'}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path);args=parser.parse_args()
    report=evaluate();rendered=json.dumps(report,indent=2)+'\n';print(rendered)
    if args.output: args.output.write_text(rendered,encoding='utf-8')

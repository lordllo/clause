"""Small reproducible fixture benchmark, not a real-world quality claim."""
import json
import os
from pathlib import Path
from app.analysis import analyze, retrieve
from app.parsing import parse
from app.schemas import DEFAULT_POLICY

def main():
    root = Path(__file__).resolve().parents[1] / 'fixtures'
    correct = verified = recall = count = 0
    for filename, expected in [('vendor-risky.txt','deviation'),('vendor-compliant.txt','compliant')]:
        clauses = parse((root/filename).read_bytes(),'.txt')
        result = analyze(DEFAULT_POLICY,clauses)
        for i, (rule,finding) in enumerate(zip(DEFAULT_POLICY.rules,result['findings'])):
            count += 1
            correct += finding['status'] == expected
            verified += finding['citation_verified']
            recall += clauses[i]['id'] in [c['id'] for c in retrieve(rule,clauses)]
    metrics = {'provider':os.getenv('ANALYSIS_PROVIDER','demo'),'cases':count,'status_accuracy':correct/count,'citation_validity':verified/count,'retrieval_recall_at_5':recall/count,'scope':'Synthetic baseline fixtures only; does not measure legal correctness.'}
    print(json.dumps(metrics,indent=2))
    if min(correct, verified, recall) != count: raise SystemExit(1)

if __name__ == '__main__': main()

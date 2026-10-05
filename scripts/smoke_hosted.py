"""Verify the built, single-origin deployment through HTTP, with separate cookies."""
import argparse
import http.cookiejar
import json
import time
import urllib.error
import urllib.request

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:8000');args=parser.parse_args()
    root=args.url.rstrip('/')
    def client(): return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    a,b=client(),client()
    def request(c,path,data=None):
        headers={}
        if data is not None: headers['Content-Type']='application/json';data=json.dumps(data).encode()
        try:
            with c.open(urllib.request.Request(root+path,data=data,headers=headers),timeout=15) as response:
                raw=response.read()
                return response.status, json.loads(raw) if 'application/json' in response.headers.get('Content-Type','') else raw
        except urllib.error.HTTPError as error: return error.code,error.read()
    for attempt in range(30):
        try:
            status,health=request(a,'/api/health')
            if status==200: break
        except (urllib.error.URLError,TimeoutError): pass
        time.sleep(1)
    else: raise RuntimeError('Hosted API never became healthy')
    assert health['public_demo'] and health['provider']=='demo'
    assert request(a,'/')[0]==200
    samples=request(a,'/api/samples')[1]
    assert len(samples)==73
    assert sum(not x.get('fictional') for x in samples)==71
    request(b,'/api/health')
    policy=request(a,'/api/policies/default')[1]
    assert request(a,'/api/policies',policy)[0]==201
    assert request(b,'/api/policies')[1]==[]
    real=next(x for x in samples if x['collection']=='CUAD commercial contracts')
    id=real['document_id']
    detail=request(a,'/api/documents/'+id)[1]
    assert detail['annotations']
    status,review=request(a,'/api/documents/'+id+'/reviews',policy)
    assert status==201 and all(f['status']=='needs_review' for f in review['findings'])
    assert review['id'] not in [r['id'] for r in request(b,'/api/documents/'+id)[1]['reviews']]
    fixture=next(x for x in samples if x.get('fictional'))
    assert request(a,'/api/documents/'+fixture['document_id'])[1]['reviews']
    print('PASS: static frontend, API, 73 samples, annotations, demo review, and visitor isolation.')

if __name__=='__main__': main()

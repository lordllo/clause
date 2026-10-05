'use client';
import {useEffect, useState} from 'react';
type Rule = {id:string;name:string;instruction:string;keywords:string[];severity:string};
type Policy = {name:string;rules:Rule[]};
type Preset = {id:string;description:string;policy:Policy};
type Passage = {id:string;page:number;heading:string;text:string};
type Finding = {rule_id:string;rule_name:string;status:string;severity:string;explanation:string;action:string;quote:string|null;clause_id:string|null;page:number|null;citation_verified:boolean;policy:string};
type Review = {id:string;provider:string;findings:Finding[]};
type Sample = {key:string;title:string;document_id:string;collection:string;category:string;publisher:string;description:string;source_url:string|null;license:string;license_url?:string;attribution?:string;transformations?:string;original_title?:string;annotation_count:number;characters?:number;fictional?:boolean};
type Annotation = {label:string;answers:{text:string;start:number;clause_id:string|null}[]};
type Doc = {id:string;name:string;sample:Sample|null};
type Detail = Doc & {clauses:Passage[];reviews:Review[];annotations:Annotation[]};
const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
async function request(path:string, options?:RequestInit) {
 const r = await fetch(API+path,{credentials:'include',...options}); const body = await r.json();
 if(!r.ok) throw new Error(typeof body.detail==='string'?body.detail:'The request could not be completed. Check policy fields.');
 return body;
}
export default function Home(){
 const [docs,setDocs]=useState<Doc[]>([]), [detail,setDetail]=useState<Detail|null>(null);
 const [policy,setPolicy]=useState<Policy|null>(null), [draft,setDraft]=useState(''), [presets,setPresets]=useState<Preset[]>([]);
 const [review,setReview]=useState<Review|null>(null), [selected,setSelected]=useState<string|null>(null);
 const [busy,setBusy]=useState(false), [error,setError]=useState(''), [mode,setMode]=useState(''), [message,setMessage]=useState(''), [hosted,setHosted]=useState(false);
 const [query,setQuery]=useState(''), [collection,setCollection]=useState('All collections'), [category,setCategory]=useState('All categories');
 const [view,setView]=useState('review'), [annotationQuery,setAnnotationQuery]=useState('');
 useEffect(()=>{
  request('/health').then(h=>{setHosted(Boolean(h.public_demo));return Promise.all([request('/documents'),request('/policies/default'),Promise.resolve(h),request('/policies/presets')])})
   .then(([d,p,h,ps])=>{setDocs(d);setPolicy(p);setDraft(JSON.stringify(p,null,2));setMode(h.provider);setPresets(ps)})
   .catch(e=>setError(e.message));
 },[]);
 async function open(id:string){
  setBusy(true);setError('');setMessage('');
  try{const d=await request('/documents/'+id);setDetail(d);setReview(d.reviews[0]||null);setSelected(null);setView('review');setAnnotationQuery('')}
  catch(e){setError((e as Error).message)}finally{setBusy(false)}
 }
 async function upload(file:File){
  setBusy(true);setError('');
  try{const form=new FormData();form.append('file',file);const d=await request('/documents',{method:'POST',body:form});setDocs(await request('/documents'));await open(d.id)}
  catch(e){setError((e as Error).message)}finally{setBusy(false)}
 }
 async function run(){
  if(!detail)return;setBusy(true);setError('');
  try{const p=JSON.parse(draft);const r=await request('/documents/'+detail.id+'/reviews',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)});setReview(r);setPolicy(p);setView('review')}
  catch(e){setError((e as Error).message)}finally{setBusy(false)}
 }
 async function save(){
  setBusy(true);setError('');
  try{const p=JSON.parse(draft);await request('/policies',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)});setPolicy(p);setMessage('Policy saved. Each review keeps its own policy snapshot.')}
  catch(e){setError((e as Error).message)}finally{setBusy(false)}
 }
 function choosePreset(id:string){const p=presets.find(p=>p.id===id)?.policy;if(p){setPolicy(p);setDraft(JSON.stringify(p,null,2))}}
 function library(){setDetail(null);setSelected(null);setError('');setMessage('')}
 const passage=detail?.clauses.find(c=>c.id===selected);
 const rank=(d:Doc)=>d.sample?.fictional?0:d.sample?.publisher==='Common Paper'?1:2;
 const samples=docs.filter(d=>d.sample).sort((a,b)=>rank(a)-rank(b)||a.name.localeCompare(b.name)), publicSamples=samples.filter(d=>!d.sample?.fictional);
 const groups=['All categories',...Array.from(new Set(samples.map(d=>d.sample!.category))).sort()];
 const collections=['All collections',...Array.from(new Set(samples.map(d=>d.sample!.collection))).sort()];
 const filtered=samples.filter(d=>{const s=d.sample!;return (collection==='All collections'||s.collection===collection)&&(category==='All categories'||s.category===category)&&[d.name,s.category,s.publisher,s.original_title,s.description].join(' ').toLowerCase().includes(query.toLowerCase())});
 const annotations=detail?.annotations.filter(a=>a.label.toLowerCase().includes(annotationQuery.toLowerCase()))||[];
 const location=detail?.sample||!detail?.name.toLowerCase().endsWith('.pdf')?'Extracted text':`Page ${passage?.page}`;
 return <>
  <header><a className="brand" href="/">clause<span> / </span></a><span>CONTRACT INTELLIGENCE</span><small>{hosted?'Sample workspace':'Local workspace'} · {mode==='demo'?'Standard policy checks':mode||'Connecting'}</small></header>
  <main><aside>
   <div className="eyebrow">WORKSPACE</div><h2>Document library <span>{docs.length}</span></h2>
   <button className={!detail?'library-button active':'library-button'} disabled={busy} onClick={library}>All sample documents</button>
   <label className="upload">{busy?'Working…':'+ Upload contract'}<input aria-label="Upload contract" disabled={busy} type="file" accept=".pdf,.docx,.txt" onChange={e=>{if(e.target.files?.[0])void upload(e.target.files[0]);e.target.value=''}}/></label>
   <p className="hint">PDF, DOCX or TXT · Up to 10 MB</p><div className="eyebrow sidebar-label">EXAMPLE REVIEWS</div>
   <nav>{samples.filter(d=>d.sample?.fictional).map(d=><button key={d.id} disabled={busy} className={detail?.id===d.id?'doc active':'doc'} onClick={()=>open(d.id)}><span>▤</span>{d.name}</button>)}</nav>
   <div className="eyebrow sidebar-label">YOUR UPLOADS</div>
   <nav>{docs.filter(d=>!d.sample).map(d=><button key={d.id} disabled={busy} className={detail?.id===d.id?'doc active':'doc'} onClick={()=>open(d.id)}><span>▤</span>{d.name}</button>)}</nav>
  </aside><section className="workspace">
   {detail&&<div className="eyebrow">CONTRACT REVIEW</div>}<h1>{detail?.name||'Documents'}</h1>
   <p className="subtitle">{detail?'Review policy findings and the clauses they refer to.':'Select a sample agreement or upload a contract to review.'}</p>
   {hosted&&<div className="notice">Use public or sample documents only. Your uploads, policies, and reviews expire after one hour. Example agreements include completed reviews; public contracts provide clauses for manual review. Live AI analysis is not enabled.</div>}
   {error&&<div role="alert" className="error">{error}</div>}{message&&<p role="status">{message}</p>}
   {!detail?<>
    <div className="metrics"><div><b>{publicSamples.length}</b><span>Sample agreements</span></div><div><b>{samples.filter(d=>d.sample?.fictional).length}</b><span>Example reviews</span></div><div><b>{publicSamples.reduce((n,d)=>n+d.sample!.annotation_count,0).toLocaleString()}</b><span>Annotated clauses</span></div></div>
    <p className="hint">Sources: Common Paper and CUAD · CC BY 4.0. Clause annotations identify contract terms; they do not establish compliance with your policy.</p>
    <div className="library-filters"><input aria-label="Search sample library" type="search" placeholder="Search titles, publishers, or topics…" value={query} onChange={e=>setQuery(e.target.value)}/><select aria-label="Filter collection" value={collection} onChange={e=>setCollection(e.target.value)}>{collections.map(c=><option key={c}>{c}</option>)}</select><select aria-label="Filter category" value={category} onChange={e=>setCategory(e.target.value)}>{groups.map(c=><option key={c}>{c}</option>)}</select></div>
    <p className="hint">{filtered.length} documents · Templates may contain blank fields. Filed agreements may be historical.</p>
    <div className="sample-grid">{filtered.map(d=>{const s=d.sample!;return <article className="sample-card" key={d.id}><div className="eyebrow">{s.category}</div><h3>{d.name}</h3><p>{s.description}</p><div className="sample-meta"><span>{s.publisher}</span><span>{s.annotation_count?`${s.annotation_count} annotations`:s.fictional?'Preloaded review':'Published standard'}</span></div><div className="sample-actions"><button disabled={busy} onClick={()=>open(d.id)}>Open document →</button>{s.source_url&&<a href={s.source_url} target="_blank" rel="noreferrer">Original source ↗</a>}</div></article>})}</div>
    {!filtered.length&&<div className="empty"><h2>No documents match.</h2><p>Try another search or remove a filter.</p></div>}
   </>:<>
    <button className="back" disabled={busy} onClick={library}>← Back to library</button>
    {detail.sample&&<div className="provenance"><strong>{detail.sample.collection} · {detail.sample.category}</strong><p>{detail.sample.description}</p><p>{detail.sample.attribution||'Created for the Clause demo.'}</p>{detail.sample.source_url&&<a href={detail.sample.source_url} target="_blank" rel="noreferrer">View pinned original source ↗</a>}{detail.sample.license_url&&<> · <a href={detail.sample.license_url} target="_blank" rel="noreferrer">{detail.sample.license}</a></>}{detail.sample.transformations&&<p className="hint">{detail.sample.transformations}</p>}</div>}
    {mode==='demo'&&<div className="notice">{detail.sample&&!detail.sample.fictional?'This review locates clauses relevant to your policy. All findings require manual review; the checks do not assess compliance for public agreements.':'This sample uses five standard policy checks. Custom rules and final interpretation require manual review. Live AI analysis is not enabled.'}</div>}
    <details><summary>Policy configuration <span>{policy?.name}</span></summary><label className="preset-label">Choose a review playbook <select aria-label="Review playbook" defaultValue="" onChange={e=>choosePreset(e.target.value)}><option value="" disabled>Choose preset</option>{presets.map(p=><option key={p.id} value={p.id}>{p.policy.name}</option>)}</select></label><p className="hint">Edit instructions, keywords, severity, and rule IDs. Custom rules retrieve evidence in demo mode; the LLM interprets their instructions.</p><textarea aria-label="Policy JSON" value={draft} onChange={e=>setDraft(e.target.value)} spellCheck={false}/><button disabled={busy} onClick={save}>Save policy</button></details>
    <div className="toolbar"><h2>{review?'Review findings':'Ready for review'}</h2><button className="primary" disabled={busy} onClick={run}>{busy?'Reviewing…':'Run policy review →'}</button></div>
    <div className="tabs" role="group" aria-label="Document views"><button className={view==='review'?'active':''} onClick={()=>setView('review')}>Policy review</button><button className={view==='annotations'?'active':''} onClick={()=>setView('annotations')}>CUAD labels ({detail.annotations.length})</button><button className={view==='source'?'active':''} onClick={()=>setView('source')}>Source passages ({detail.clauses.length})</button></div>
    {view==='review'&&(review?<>
     <div className="metrics"><div><b>{review.findings.filter(f=>f.status==='deviation').length}</b><span>Deviations</span></div><div><b>{review.findings.filter(f=>f.status==='needs_review').length}</b><span>Need review</span></div><div><b>{review.findings.filter(f=>f.citation_verified).length}/{review.findings.length}</b><span>Verified citations</span></div></div>
     <div className="results">{review.findings.map(f=><article key={f.rule_id}><div className="finding-head"><h3>{f.rule_name}</h3><span className={'badge '+f.status}>{f.status.replace('_',' ')}{f.status==='deviation'?' · '+f.severity:''}</span></div><p>{f.explanation}</p><div className="policy"><strong>Company policy</strong><p>{f.policy}</p></div>{f.quote&&<button className="quote" onClick={()=>setSelected(f.clause_id)}><blockquote>{f.quote}</blockquote><span>✓ Exact quote verified · {detail.sample||!detail.name.toLowerCase().endsWith('.pdf')?'Extracted text':`Page ${f.page}`} · View source →</span></button>}<p className="action"><strong>Suggested action</strong> {f.action}</p></article>)}</div><p className="hint">Reviewer: {review.provider}. Verification confirms source text, not legal correctness. Retrieved passages are not exhaustive.</p>
    </>:<div className="empty"><div>▤</div><h2>Your contract is ready.</h2><p>{detail.clauses.length} passages extracted. Run a policy review, browse source passages, or explore the available CUAD annotations.</p></div>)}
    {view==='annotations'&&<><p className="hint">Attorney-supervised CUAD labels identify source passages for diligence. Annotations are not findings of compliance. Original text offsets are retained; some excerpts span multiple parsed passages.</p><input className="annotation-search" aria-label="Search annotation labels" type="search" placeholder="Search labels, e.g. Governing Law or Cap On Liability" value={annotationQuery} onChange={e=>setAnnotationQuery(e.target.value)}/>{annotations.map(a=><article key={a.label}><h3>{a.label}</h3>{a.answers.map((answer,i)=><div className="annotated-quote" key={i}><blockquote>{answer.text}</blockquote>{answer.clause_id?<button onClick={()=>setSelected(answer.clause_id)}>Inspect source passage →</button>:<span className="hint">Excerpt spans parsed passages; use the original text download.</span>}<span className="hint"> · Original text offset {answer.start.toLocaleString()}</span></div>)}</article>)}{!annotations.length&&<div className="empty"><h2>No matching CUAD labels.</h2><p>Common Paper standards and fictional walkthroughs do not include CUAD annotations.</p></div>}</>}
    {view==='source'&&detail.clauses.map(c=><article key={c.id}><h3>{c.heading}</h3><p className="passage-preview">{c.text.slice(0,600)}{c.text.length>600?'…':''}</p><button onClick={()=>setSelected(c.id)}>Read full passage →</button></article>)}
    <a className="source-link" href={API+'/documents/'+detail.id+'/source'}>Download {detail.sample?'attributed source text':'original document'}</a>
   </>}
  </section></main>
  {passage&&<div className="overlay" role="dialog" aria-modal="true" aria-label="Citation source"><section className="source"><button className="close" onClick={()=>setSelected(null)}>Close ×</button><div className="eyebrow">SOURCE EVIDENCE · {location}</div><h2>{passage.heading}</h2><pre>{passage.text}</pre></section></div>}
 </>;
}

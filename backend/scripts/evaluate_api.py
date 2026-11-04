"""Run Claim Court against seeded GlowSerum items and produce honest prediction/metric files.
Run API first, seed with --email, then call this script with a bearer token.
"""
import argparse, asyncio, json, re
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[2]
GOLD=ROOT/'data'/'sample'/'glowserum_40_posts.jsonl'

def labels_for(result):
    labels=set()
    for finding in result.get('findings',[]):
        verdict=finding.get('verdict'); method=finding.get('analysis_method','')
        evidence=finding.get('evidence',[])
        codes={str(e.get('code','')) for e in evidence}
        types={str(e.get('type','')) for e in evidence}
        claim=finding.get('claim_text','').lower()
        if 'IN-2' in codes: labels.add('unsupported_superlative')
        if 'IN-5' in codes or 'brand_term_list' in types: labels.add('banned_term')
        if 'IN-4' in codes: labels.add('missing_disclosure')
        if verdict=='outdated': labels.add('expired_fact')
        if verdict=='contradicted': labels.add('wrong_number')
        if method=='image_intelligence_v1' or 'visual_check' in types: labels.add('visual')
    return sorted(labels)

async def main(args):
    gold=[json.loads(x) for x in GOLD.read_text(encoding='utf-8').splitlines() if x.strip()]
    by_title={r['title']:r for r in gold}
    headers={'Authorization':f'Bearer {args.token}'}
    async with httpx.AsyncClient(base_url=args.base_url.rstrip('/')+'/api',headers=headers,timeout=40) as client:
        response=await client.get('/content');response.raise_for_status()
        items=[x for x in response.json() if x.get('campaign')=='GlowSerum fictional evaluation set' and x['title'] in by_title]
        predictions=[]
        for item in items:
            row=by_title[item['title']]
            if row['expected_findings']==['visual']:
                image=await client.post(f"/content/{item['id']}/image-analysis")
                if image.status_code not in (200,409): image.raise_for_status()
            queued=await client.post(f"/content/{item['id']}/analyze")
            queued.raise_for_status(); job_id=queued.json()['job_id']; job=None
            for _ in range(180):
                check=await client.get(f'/jobs/{job_id}');check.raise_for_status();job=check.json()
                if job['status'] in {'completed','failed'}: break
                await asyncio.sleep(.5)
            if not job or job['status']!='completed':
                print(f"WARNING: {row['id']} did not complete: {job.get('error') if job else 'no job status'}")
                predicted=[]
            else: predicted=labels_for(job.get('result') or {})
            predictions.append({'id':row['id'],'predicted_findings':predicted})
            print(f"{row['id']} {row['title']}: {predicted or 'no findings'}")
        out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text('\n'.join(json.dumps(x) for x in predictions)+'\n',encoding='utf-8')
        print(json.dumps({'seeded_items_found':len(items),'expected_items':len(gold),'predictions_file':str(out),'notice':'Metrics are only valid if all expected items were found and jobs completed. Review missed items before reporting.'},indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base-url',default='http://localhost:8000');p.add_argument('--token',required=True);p.add_argument('--out',default=None);args=p.parse_args();args.out=args.out or str(ROOT/'data'/'sample'/'glowserum_predictions.jsonl');asyncio.run(main(args))

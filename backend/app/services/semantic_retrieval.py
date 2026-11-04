"""Local deterministic retrieval helpers and optional Ollama NLI adapter.
The default hashing vectors are retrieval features, not pretrained semantic embeddings.
"""
from __future__ import annotations
import hashlib, math, re, json

def embedding(text: str, dimensions: int=96) -> list[float]:
    tokens=re.findall(r"[a-z0-9]+",text.lower())
    features=tokens[:]
    for token in tokens:
        features.extend(token[i:i+3] for i in range(max(0,len(token)-2)))
    vector=[0.0]*dimensions
    for token in features:
        digest=hashlib.blake2b(token.encode('utf-8'),digest_size=8).digest()
        number=int.from_bytes(digest,'big'); index=number%dimensions
        vector[index]+=1.0 if (number>>8)&1 else -1.0
    norm=math.sqrt(sum(x*x for x in vector)) or 1.0
    return [x/norm for x in vector]

def cosine(a: list[float], b: list[float]) -> float:
    return sum(x*y for x,y in zip(a,b)) / ((math.sqrt(sum(x*x for x in a))*math.sqrt(sum(y*y for y in b))) or 1.0)

def hybrid_similarity(a: str,b: str) -> float:
    aw=set(re.findall(r"[a-z0-9]+",a.lower())); bw=set(re.findall(r"[a-z0-9]+",b.lower()))
    lexical=len(aw&bw)/len(aw|bw) if aw|bw else 0.0
    hashed=max(0.0,cosine(embedding(a),embedding(b)))
    return .65*lexical+.35*hashed

async def ollama_nli(claim: str, evidence: str, base_url: str, model: str) -> dict:
    """Returns entailment/contradiction/unknown; malformed/offline response is unknown."""
    try:
        import httpx
        prompt=("Classify the relationship between CLAIM and EVIDENCE as exactly one of "
                "supported, contradicted, or unknown. Do not use outside knowledge. "
                "Return JSON only: {\"label\":\"supported|contradicted|unknown\",\"reason\":\"short reason\"}.\n"
                f"CLAIM: {claim[:2000]}\nEVIDENCE: {evidence[:3000]}")
        async with httpx.AsyncClient(timeout=12.0) as client:
            response=await client.post(base_url.rstrip('/')+'/api/generate',json={'model':model,'prompt':prompt,'stream':False,'format':'json'})
            response.raise_for_status(); payload=response.json()
        raw=payload.get('response','')
        data=json.loads(raw)
        label=data.get('label')
        if label not in {'supported','contradicted','unknown'}: return {'label':'unknown','reason':'Ollama returned an invalid label.','status':'needs_human_review'}
        return {'label':label,'reason':str(data.get('reason',''))[:500],'status':'completed','model':model}
    except Exception as exc:
        return {'label':'unknown','reason':f'Local model unavailable or invalid response ({type(exc).__name__}).','status':'needs_human_review','model':model}


async def ollama_embeddings(texts: list[str], base_url: str, model: str) -> dict:
    """Request a batch of local embeddings. Caller must mask inputs before invoking.

    Returns a structured failure rather than raising so callers can fall back to deterministic
    retrieval while surfacing a Needs human review notice.
    """
    if not texts:
        return {'status':'completed','model':model,'embeddings':[]}
    try:
        import httpx
        async with httpx.AsyncClient(timeout=20.0) as client:
            response=await client.post(base_url.rstrip('/')+'/api/embed',json={'model':model,'input':texts})
            response.raise_for_status()
            payload=response.json()
        vectors=payload.get('embeddings')
        if not isinstance(vectors,list) or len(vectors)!=len(texts) or any(not isinstance(v,list) or not v for v in vectors):
            return {'status':'needs_human_review','model':model,'reason':'Ollama returned missing or mismatched embedding vectors.'}
        normalized=[]
        for vector in vectors:
            values=[float(x) for x in vector]
            norm=math.sqrt(sum(x*x for x in values)) or 1.0
            normalized.append([x/norm for x in values])
        return {'status':'completed','model':model,'embeddings':normalized}
    except Exception as exc:
        return {'status':'needs_human_review','model':model,'reason':f'Local embedding model unavailable or invalid response ({type(exc).__name__}).'}

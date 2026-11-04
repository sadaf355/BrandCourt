import base64, hashlib, hmac, json, os, time
from fastapi import HTTPException, status
from app.core.config import settings

def _b64(data: bytes) -> str: return base64.urlsafe_b64encode(data).rstrip(b'=').decode()
def _unb64(data: str) -> bytes: return base64.urlsafe_b64decode(data + '=' * (-len(data) % 4))
def hash_password(password: str) -> str:
    if len(password) < 8: raise ValueError('Password must contain at least 8 characters.')
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 310_000)
    return f"pbkdf2_sha256${_b64(salt)}${_b64(digest)}"
def verify_password(password: str, encoded: str) -> bool:
    try:
        _, salt, expected = encoded.split('$')
        actual = hashlib.pbkdf2_hmac('sha256', password.encode(), _unb64(salt), 310_000)
        return hmac.compare_digest(_b64(actual), expected)
    except Exception: return False
def create_access_token(subject: str, workspace_id: str, role: str) -> str:
    now = int(time.time())
    header = _b64(json.dumps({'alg':'HS256','typ':'JWT'}, separators=(',', ':')).encode())
    payload = _b64(json.dumps({'sub':subject,'workspace_id':workspace_id,'role':role,'iat':now,'exp':now+settings.access_token_minutes*60}, separators=(',', ':')).encode())
    signing = f'{header}.{payload}'
    signature = _b64(hmac.new(settings.secret_key.encode(), signing.encode(), hashlib.sha256).digest())
    return f'{signing}.{signature}'
def decode_access_token(token: str) -> dict:
    try:
        header, payload, signature = token.split('.')
        signing = f'{header}.{payload}'
        expected = _b64(hmac.new(settings.secret_key.encode(), signing.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected): raise ValueError('signature')
        claims = json.loads(_unb64(payload))
        if claims.get('exp', 0) < time.time(): raise ValueError('expired')
        return claims
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid or expired access token.', headers={'WWW-Authenticate':'Bearer'}) from exc

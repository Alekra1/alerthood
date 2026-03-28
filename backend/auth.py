import json
import logging
import time

import httpx
import jwt
from jwt.algorithms import ECAlgorithm
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import Settings, get_settings

logger = logging.getLogger(__name__)
security = HTTPBearer()

_jwks_cache: dict[str, tuple[float, dict]] = {}
JWKS_CACHE_TTL = 3600  # 1 hour


def _get_signing_key(supabase_url: str, kid: str):
    """Fetch JWKS via httpx and return the matching public key."""
    now = time.time()
    cached = _jwks_cache.get(supabase_url)
    if cached and now - cached[0] < JWKS_CACHE_TTL:
        jwks = cached[1]
    else:
        jwks_url = f"{supabase_url}/auth/v1/.well-known/jwks.json"
        resp = httpx.get(jwks_url, timeout=10)
        resp.raise_for_status()
        jwks = resp.json()
        _jwks_cache[supabase_url] = (now, jwks)

    for key_data in jwks.get("keys", []):
        if key_data.get("kid") == kid:
            return ECAlgorithm.from_jwk(json.dumps(key_data))
    raise ValueError(f"No matching key found for kid={kid}")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings),
) -> str:
    """Verify Supabase JWT and return user ID."""
    token = credentials.credentials
    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid", "")
        public_key = _get_signing_key(settings.supabase_url, kid)
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["ES256"],
            audience="authenticated",
        )
    except (jwt.PyJWTError, ValueError, httpx.HTTPError) as e:
        logger.warning("JWT decode failed: %s", e)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing user identity")
    return user_id

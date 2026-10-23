from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from sentinel.config import settings
from sentinel.db import get_db
from sentinel.models import Principal, RoleBinding

bearer = HTTPBearer(auto_error=False)


@lru_cache
def jwks_client():
    return jwt.PyJWKClient(settings().oidc_jwks_url, timeout=5, lifespan=300)


@dataclass(frozen=True)
class Actor:
    subject: str
    bindings: tuple

    def allows(self, role: str, scope_type: str, scope_id: str) -> bool:
        return any(b.role == role and b.scope_type == scope_type and b.scope_id == scope_id
                   for b in self.bindings)

    def institution_ids(self):
        return sorted({b.scope_id for b in self.bindings if b.scope_type == 'INSTITUTION'})

    def case_ids(self, roles=None):
        return sorted({b.scope_id for b in self.bindings if b.scope_type == 'CASE'
                       and (not roles or b.role in roles)})


def authenticate(credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
                 db: Session = Depends(get_db)) -> Actor:
    if not credentials:
        raise HTTPException(401, 'Bearer access token required', headers={'WWW-Authenticate': 'Bearer'})
    try:
        key = jwks_client().get_signing_key_from_jwt(credentials.credentials).key
        claims = jwt.decode(credentials.credentials, key, algorithms=['RS256'],
                            issuer=settings().oidc_issuer, audience=settings().oidc_audience,
                            options={'require': ['exp', 'iat', 'iss', 'sub', 'aud']})
        subject = claims['sub']
        if not isinstance(subject, str) or len(subject) > 128:
            raise ValueError('Invalid subject')
    except jwt.PyJWKClientConnectionError:
        raise HTTPException(503, 'Identity verification unavailable') from None
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(401, 'Invalid access token', headers={'WWW-Authenticate': 'Bearer'}) from None
    except Exception:
        raise HTTPException(503, 'Identity verification unavailable') from None
    principal = db.get(Principal, subject)
    if principal is None:
        db.execute(insert(Principal).values(subject=subject, enabled=True).on_conflict_do_nothing())
        db.commit()
        principal = db.get(Principal, subject)
    if not principal.enabled:
        raise HTTPException(403, 'Identity disabled')
    instant = datetime.now(timezone.utc)
    bindings = db.scalars(select(RoleBinding).where(
        RoleBinding.subject == subject, RoleBinding.enabled.is_(True),
        RoleBinding.valid_from <= instant,
        or_(RoleBinding.valid_until.is_(None), RoleBinding.valid_until > instant),
    )).all()
    return Actor(subject, tuple(bindings))


def require_scope(actor: Actor, institution_id: str, roles=None):
    if institution_id not in actor.institution_ids():
        raise HTTPException(404, 'Resource not found')
    if roles and not any(actor.allows(role, 'INSTITUTION', institution_id) for role in roles):
        raise HTTPException(403, 'Permission denied')

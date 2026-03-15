import os
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from rental_core.db import get_db
from rental_core.models.contractor import Contractor
from rental_core.models.owner import OwnerAccount
from rental_core.models.tenant import Tenant

JWT_SECRET = os.getenv("PROPIFY_JWT_SECRET", "dev-only-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("PROPIFY_JWT_EXPIRE_MINUTES", "480"))

bearer_scheme = HTTPBearer(auto_error=False)


def _create_access_token(payload: dict) -> str:
    now = datetime.now(UTC)
    token_payload = {**payload, "iat": now, "exp": now + timedelta(minutes=JWT_EXPIRE_MINUTES)}
    return jwt.encode(token_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_owner_access_token(owner: OwnerAccount) -> str:
    return _create_access_token({"sub": str(owner.id), "sub_type": "owner", "role": "owner", "username": owner.username})


def create_tenant_access_token(tenant: Tenant) -> str:
    return _create_access_token({"sub": str(tenant.id), "sub_type": "tenant", "role": "tenant", "phone": tenant.phone or ""})


def create_contractor_access_token(contractor: Contractor) -> str:
    return _create_access_token({"sub": str(contractor.id), "sub_type": "contractor", "role": "contractor", "phone": contractor.phone or ""})


def _decode_token(credentials: HTTPAuthorizationCredentials | None) -> dict:
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    token = credentials.credentials
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc


def require_role(*allowed_roles: str):
    normalized_roles = {r.strip().lower() for r in allowed_roles if r and r.strip()}

    def _role_dependency(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)):
        payload = _decode_token(credentials)
        role = str(payload.get("role") or "").strip().lower()
        if not role or role not in normalized_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role permissions")
        return payload

    return _role_dependency


def get_current_owner(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> OwnerAccount:
    payload = _decode_token(credentials)
    if payload.get("sub_type") != "owner":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    owner_id = payload.get("sub")
    if not owner_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    owner = db.query(OwnerAccount).filter(OwnerAccount.id == int(owner_id)).first()
    if not owner:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token user no longer exists")
    return owner


def get_current_tenant(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Tenant:
    payload = _decode_token(credentials)
    if payload.get("sub_type") != "tenant":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    tenant_id = payload.get("sub")
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    tenant = db.query(Tenant).filter(Tenant.id == int(tenant_id)).first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token user no longer exists")
    return tenant


def get_current_contractor(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Contractor:
    payload = _decode_token(credentials)
    if payload.get("sub_type") != "contractor":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    contractor_id = payload.get("sub")
    if not contractor_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    contractor = db.query(Contractor).filter(Contractor.id == int(contractor_id)).first()
    if not contractor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token user no longer exists")
    return contractor

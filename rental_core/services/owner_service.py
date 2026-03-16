import hashlib
import os
import re
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from rental_core.models.owner_admin import OwnerAdmin
from rental_core.models.owner import OwnerAccount
from rental_core.models.owner_password_reset import OwnerPasswordReset
from rental_core.schemas.owner import OwnerSetup, OwnerUpdate


OWNER_RESET_TOKEN_TTL_MINUTES = int(os.getenv("PROPIFY_OWNER_RESET_TTL_MINUTES", "30"))
OWNER_RESET_MIN_INTERVAL_SECONDS = int(os.getenv("PROPIFY_OWNER_RESET_MIN_INTERVAL_SECONDS", "60"))
PHONE_PATTERN = re.compile(r"^\+?[0-9]{8,15}$")


def _hash_password(password: str, salt_hex: str | None = None) -> tuple[str, str]:
    salt = bytes.fromhex(salt_hex) if salt_hex else os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 150000)
    return digest.hex(), salt.hex()


def _verify_password(password: str, stored_hash: str, salt_hex: str) -> bool:
    digest, _ = _hash_password(password, salt_hex)
    return digest == stored_hash


def normalize_owner_phone(phone: str) -> str:
    raw = (phone or "").strip()
    if not raw:
        raise ValueError("Phone is required")
    if any(ch.isspace() for ch in raw):
        raise ValueError("Phone must not contain spaces")
    if not PHONE_PATTERN.fullmatch(raw):
        raise ValueError("Phone must be digits with optional leading '+'")
    return raw


def _owner_phone_candidates(phone: str) -> list[str]:
    normalized = normalize_owner_phone(phone)
    digits = "".join(ch for ch in normalized if ch.isdigit())

    candidates = {normalized, digits}
    if normalized.startswith("+"):
        candidates.add(normalized[1:])
    else:
        candidates.add(f"+{digits}")

    # Convenience fallback for North America style entries: +1XXXXXXXXXX <-> XXXXXXXXXX
    if digits.startswith("1") and len(digits) == 11:
        candidates.add(digits[1:])
        candidates.add(f"+{digits[1:]}")

    return [c for c in candidates if c]


def get_owner(db: Session):
    return db.query(OwnerAccount).first()


def get_owner_by_id(db: Session, owner_id: int):
    return db.query(OwnerAccount).filter(OwnerAccount.id == owner_id).first()


def create_owner(db: Session, owner_in: OwnerSetup):
    if db.query(OwnerAccount).first():
        return None

    owner_phone = normalize_owner_phone(owner_in.owner_phone or "")

    password_hash, password_salt = _hash_password(owner_in.password)
    username = (owner_in.username or "").strip() or f"owner_{owner_phone.lstrip('+')}"
    owner = OwnerAccount(
        username=username,
        password_hash=password_hash,
        password_salt=password_salt,
        company_name=owner_in.company_name.strip(),
        company_address=(owner_in.company_address or "").strip(),
        company_phone=(owner_in.company_phone or "").strip(),
        owner_name=owner_in.owner_name.strip(),
        owner_email=(owner_in.owner_email or "").strip(),
        owner_phone=owner_phone,
        two_fa_enabled=False,
        is_blocked=False,
        blocked_reason="",
    )
    db.add(owner)
    db.commit()
    db.refresh(owner)
    return owner


def get_owner_by_phone(db: Session, phone: str):
    candidates = _owner_phone_candidates(phone)
    owner = db.query(OwnerAccount).filter(OwnerAccount.owner_phone.in_(candidates)).first()
    return owner


def get_owner_admin_by_phone(db: Session, phone: str):
    candidates = _owner_phone_candidates(phone)
    return db.query(OwnerAdmin).filter(OwnerAdmin.phone.in_(candidates)).first()


def login_owner(db: Session, phone: str, password: str):
    owner = get_owner_by_phone(db, phone)
    if owner and _verify_password(password, owner.password_hash, owner.password_salt):
        return {
            "owner": owner,
            "actor_type": "owner",
            "actor_id": owner.id,
            "actor_name": owner.owner_name,
        }

    admin = get_owner_admin_by_phone(db, phone)
    if not admin or admin.status != "approved":
        return None
    if not admin.password_hash or not admin.password_salt:
        return None
    if not _verify_password(password, admin.password_hash, admin.password_salt):
        return None

    owner = get_owner_by_id(db, admin.owner_id)
    if not owner:
        return None

    return {
        "owner": owner,
        "actor_type": "owner_admin",
        "actor_id": admin.id,
        "actor_name": admin.name or owner.owner_name,
    }


def update_owner(db: Session, owner_in: OwnerUpdate, owner_id: int):
    owner = get_owner_by_id(db, owner_id)
    if not owner:
        return None

    payload = owner_in.model_dump(exclude_unset=True)
    if "owner_phone" in payload and payload["owner_phone"] is not None:
        payload["owner_phone"] = normalize_owner_phone(payload["owner_phone"])

    for field, value in payload.items():
        setattr(owner, field, value.strip() if isinstance(value, str) else value)

    db.commit()
    db.refresh(owner)
    return owner


def request_owner_password_reset(db: Session, phone: str) -> str | None:
    if not phone:
        return None

    try:
        candidates = _owner_phone_candidates(phone)
    except ValueError:
        return None

    owner = db.query(OwnerAccount).filter(OwnerAccount.owner_phone.in_(candidates)).first()
    if not owner:
        return None
    if bool(owner.is_blocked):
        return None

    now = datetime.now(UTC)
    latest = (
        db.query(OwnerPasswordReset)
        .filter(OwnerPasswordReset.owner_id == owner.id)
        .order_by(OwnerPasswordReset.created_at.desc())
        .first()
    )
    if latest and latest.created_at and (now - latest.created_at.replace(tzinfo=UTC)).total_seconds() < OWNER_RESET_MIN_INTERVAL_SECONDS:
        return None

    active_tokens = (
        db.query(OwnerPasswordReset)
        .filter(
            OwnerPasswordReset.owner_id == owner.id,
            OwnerPasswordReset.used_at.is_(None),
            OwnerPasswordReset.expires_at > now,
        )
        .all()
    )
    for token in active_tokens:
        token.used_at = now

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    reset = OwnerPasswordReset(
        owner_id=owner.id,
        token_hash=token_hash,
        expires_at=now + timedelta(minutes=OWNER_RESET_TOKEN_TTL_MINUTES),
    )
    db.add(reset)
    db.commit()
    return raw_token


def confirm_owner_password_reset(db: Session, token: str, new_password: str) -> bool:
    raw_token = (token or "").strip()
    if not raw_token or not new_password:
        return False

    now = datetime.now(UTC)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    reset = (
        db.query(OwnerPasswordReset)
        .filter(
            OwnerPasswordReset.token_hash == token_hash,
            OwnerPasswordReset.used_at.is_(None),
            OwnerPasswordReset.expires_at > now,
        )
        .first()
    )
    if not reset:
        return False

    owner = db.query(OwnerAccount).filter(OwnerAccount.id == reset.owner_id).first()
    if not owner:
        return False

    password_hash, password_salt = _hash_password(new_password)
    owner.password_hash = password_hash
    owner.password_salt = password_salt

    reset.used_at = now
    other_tokens = (
        db.query(OwnerPasswordReset)
        .filter(
            OwnerPasswordReset.owner_id == owner.id,
            OwnerPasswordReset.id != reset.id,
            OwnerPasswordReset.used_at.is_(None),
            OwnerPasswordReset.expires_at > now,
        )
        .all()
    )
    for row in other_tokens:
        row.used_at = now

    db.commit()
    return True


def block_owner_by_phone(db: Session, phone: str, reason: str | None = None) -> bool:
    owner = get_owner_by_phone(db, phone)
    if not owner:
        return False
    owner.is_blocked = True
    owner.blocked_at = datetime.now(UTC)
    owner.blocked_reason = (reason or "Blocked by Propify operations").strip()
    db.commit()
    return True


def unblock_owner_by_phone(db: Session, phone: str) -> bool:
    owner = get_owner_by_phone(db, phone)
    if not owner:
        return False
    owner.is_blocked = False
    owner.blocked_at = None
    owner.blocked_reason = ""
    db.commit()
    return True


def get_owner_status_by_phone(db: Session, phone: str) -> dict:
    normalized_phone = normalize_owner_phone(phone)
    candidates = _owner_phone_candidates(phone)
    owner = db.query(OwnerAccount).filter(OwnerAccount.owner_phone.in_(candidates)).first()
    if not owner:
        return {"found": False, "phone": normalized_phone}
    return {
        "found": True,
        "phone": normalized_phone,
        "username": owner.username,
        "is_blocked": bool(owner.is_blocked),
        "blocked_reason": owner.blocked_reason or "",
    }


def register_owner_phone(db: Session, phone: str, password: str) -> bool:
    owner = get_owner(db)
    if not owner:
        return False
    if not _verify_password(password or "", owner.password_hash, owner.password_salt):
        return False

    owner.owner_phone = normalize_owner_phone(phone)
    db.commit()
    return True


def list_owner_admins(db: Session, owner_id: int):
    return (
        db.query(OwnerAdmin)
        .filter(OwnerAdmin.owner_id == owner_id)
        .order_by(OwnerAdmin.invited_at.desc(), OwnerAdmin.id.desc())
        .all()
    )


def invite_owner_admin(db: Session, owner_id: int, phone: str):
    normalized_phone = normalize_owner_phone(phone)
    owner = get_owner_by_id(db, owner_id)
    if not owner:
        return None
    if owner.owner_phone in _owner_phone_candidates(normalized_phone):
        raise ValueError("Primary owner phone is already registered for this company")

    existing = (
        db.query(OwnerAdmin)
        .filter(OwnerAdmin.owner_id == owner_id, OwnerAdmin.phone == normalized_phone)
        .first()
    )
    now = datetime.utcnow()
    if existing:
        existing.status = "invited"
        existing.invited_at = now
        existing.accepted_at = None
        existing.approved_at = None
        existing.password_hash = ""
        existing.password_salt = ""
        db.commit()
        db.refresh(existing)
        return existing

    admin = OwnerAdmin(owner_id=owner_id, phone=normalized_phone, status="invited", invited_at=now)
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


def lookup_owner_admin_invites(db: Session, phone: str):
    normalized_phone = normalize_owner_phone(phone)
    candidates = _owner_phone_candidates(normalized_phone)
    return (
        db.query(OwnerAdmin)
        .filter(OwnerAdmin.phone.in_(candidates))
        .order_by(OwnerAdmin.invited_at.desc(), OwnerAdmin.id.desc())
        .all()
    )


def accept_owner_admin_invite(
    db: Session,
    invite_id: int,
    phone: str,
    name: str,
    email: str | None,
    password: str,
):
    normalized_phone = normalize_owner_phone(phone)
    if len(password or "") < 8:
        raise ValueError("Password must be at least 8 characters")

    invite = db.query(OwnerAdmin).filter(OwnerAdmin.id == invite_id, OwnerAdmin.phone == normalized_phone).first()
    if not invite or invite.status not in {"invited", "accepted", "approved"}:
        return None

    password_hash, password_salt = _hash_password(password)
    now = datetime.utcnow()
    invite.name = (name or "").strip()
    invite.email = (email or "").strip()
    invite.password_hash = password_hash
    invite.password_salt = password_salt
    invite.status = "approved"
    if not invite.accepted_at:
        invite.accepted_at = now
    invite.approved_at = now
    db.commit()
    db.refresh(invite)
    return invite

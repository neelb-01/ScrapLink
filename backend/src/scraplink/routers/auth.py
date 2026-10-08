import hashlib
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ..deps import DB, CurrentUser, EnvDep
from ..errors import Conflict, Invalid
from ..kyc import normalise_gstin, normalise_pan, pan_in_gstin
from ..models import KycStatus, Role, User
from ..places import PLACES
from ..schemas import LoginIn, ProfileIn, RegisterIn, TokenOut, UserOut
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

# KYC and licence documents: a scan or photo of the certificate.
DOCUMENT_TYPES = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024


def _check_place(place: str | None) -> None:
    if place is not None and place not in PLACES:
        raise Invalid(f"unknown place '{place}'")


@router.post("/register", status_code=201, response_model=UserOut)
def register(body: RegisterIn, db: DB, env: EnvDep) -> User:
    try:
        gstin = normalise_gstin(body.gstin) if body.gstin else None
        pan = normalise_pan(body.pan) if body.pan else None
    except ValueError as exc:
        raise Invalid(str(exc)) from None
    _check_place(body.place)
    if body.role == Role.BUYER and gstin is None:
        raise Invalid("buyers must provide a GSTIN")
    if gstin and pan and pan_in_gstin(gstin) != pan:
        raise Invalid("the PAN does not match the PAN inside the GSTIN")
    if gstin and not pan:
        pan = pan_in_gstin(gstin)

    if db.scalars(select(User).where(User.phone == body.phone)).first():
        raise Conflict("this phone number is already registered")
    user = User(
        phone=body.phone,
        name=body.name.strip(),
        password_hash=hash_password(body.password),
        role=body.role,
        business_name=body.business_name,
        gstin=gstin,
        pan=pan,
        email=body.email,
        place=body.place,
        kyc_status=KycStatus.PENDING,
        created_at=env.now(),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        raise Conflict("this phone number is already registered") from None
    return user


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: DB, env: EnvDep) -> TokenOut:
    user = db.scalars(select(User).where(User.phone == body.phone)).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "phone number or password is wrong")
    token = create_access_token(
        user.id,
        user.role,
        secret=env.settings.jwt_secret,
        ttl_seconds=env.settings.jwt_access_ttl_seconds,
    )
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> User:
    return user


@router.patch("/me", response_model=UserOut)
def update_profile(body: ProfileIn, db: DB, user: CurrentUser) -> User:
    """The organisation profile. GSTIN and PAN are fixed once KYC has checked them."""
    changes = body.model_dump(exclude_unset=True)
    _check_place(changes.get("place"))
    if "business_name" in changes:
        user.business_name = (changes["business_name"] or "").strip() or None
    if "email" in changes:
        user.email = changes["email"]
    if "place" in changes:
        user.place = changes["place"]
    db.commit()
    return user


@router.post("/me/kyc-document", response_model=UserOut)
def upload_kyc_document(
    db: DB,
    env: EnvDep,
    user: CurrentUser,
    document: Annotated[UploadFile, File(description="KYC or licence document (PDF or photo)")],
) -> User:
    """Replaces any earlier upload. An admin opens it from the Approvals screen."""
    extension = DOCUMENT_TYPES.get(document.content_type or "")
    if extension is None:
        raise Invalid("upload a PDF, JPEG, PNG or WebP file")
    data = document.file.read(MAX_DOCUMENT_BYTES + 1)
    if not data:
        raise Invalid("the uploaded file is empty")
    if len(data) > MAX_DOCUMENT_BYTES:
        raise Invalid("documents must be 10 MB or smaller")
    user.kyc_document_key = env.storage.put("kyc", data, extension)
    user.kyc_document_name = (document.filename or f"document{extension}")[:200]
    user.kyc_document_sha256 = hashlib.sha256(data).hexdigest()
    db.commit()
    return user

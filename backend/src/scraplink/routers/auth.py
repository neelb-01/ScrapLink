from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ..deps import DB, CurrentUser, EnvDep
from ..errors import Conflict, Invalid
from ..kyc import normalise_gstin, normalise_pan, pan_in_gstin
from ..models import KycStatus, Role, User
from ..schemas import LoginIn, RegisterIn, TokenOut, UserOut
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=201, response_model=UserOut)
def register(body: RegisterIn, db: DB, env: EnvDep) -> User:
    try:
        gstin = normalise_gstin(body.gstin) if body.gstin else None
        pan = normalise_pan(body.pan) if body.pan else None
    except ValueError as exc:
        raise Invalid(str(exc)) from None
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

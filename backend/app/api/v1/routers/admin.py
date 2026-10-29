from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.constants import SENSOR_PARAM_SPECS
from app.db.session import get_db
from app.models import Role, SensorType, User
from app.schemas.auth import UserCreate, UserOut, UserUpdate
from app.services.auth_service import AuthService

router = APIRouter()


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return [AuthService.to_out(u) for u in AuthService(db).list_users()]


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    try:
        user = AuthService(db).create_user(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AuthService.to_out(user)


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    try:
        user = AuthService(db).update_user(user_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AuthService.to_out(user)


@router.get("/roles")
def list_roles(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return [
        {"id": r.id, "code": r.code, "name": r.name, "description": r.description}
        for r in db.query(Role).order_by(Role.id).all()
    ]


@router.get("/sensor-types")
def list_sensor_types(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    rows = db.query(SensorType).order_by(SensorType.code).all()
    return [
        {
            "id": r.id,
            "code": r.code,
            "name": r.name,
            "unit": r.unit,
            "min_value": r.min_value,
            "max_value": r.max_value,
            "critical_min": r.critical_min,
            "critical_max": r.critical_max,
        }
        for r in rows
    ]


@router.get("/parameter-specs")
def parameter_specs(_: User = Depends(require_admin)):
    return SENSOR_PARAM_SPECS

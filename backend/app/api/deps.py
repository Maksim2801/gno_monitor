from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session, joinedload

from app.core.roles import can_ack_alerts, can_manage_users, can_write
from app.core.security import TokenError, safe_decode_token
from app.db.session import get_db
from app.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = safe_decode_token(token)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Некорректный токен")

    user = (
        db.query(User)
        .options(joinedload(User.role))
        .filter(User.id == int(user_id))
        .first()
    )
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Пользователь не найден или отключён")
    return user


def require_roles(*roles: str):
    def _checker(user: User = Depends(get_current_user)) -> User:
        if user.role.code not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав для выполнения операции",
            )
        return user

    return _checker


def require_write(user: User = Depends(get_current_user)) -> User:
    if not can_write(user.role.code):
        raise HTTPException(status_code=403, detail="Операция недоступна в режиме просмотра")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not can_manage_users(user.role.code):
        raise HTTPException(status_code=403, detail="Требуются права администратора")
    return user


def require_alert_action(user: User = Depends(get_current_user)) -> User:
    if not can_ack_alerts(user.role.code):
        raise HTTPException(status_code=403, detail="Подтверждение тревог недоступно")
    return user

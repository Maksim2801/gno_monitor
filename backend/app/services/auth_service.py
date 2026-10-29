from sqlalchemy.orm import Session, joinedload

from app.core.security import create_access_token, hash_password, verify_password
from app.models import Role, User
from app.schemas.auth import UserCreate, UserUpdate


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def authenticate(self, username: str, password: str) -> User | None:
        user = (
            self.db.query(User)
            .options(joinedload(User.role))
            .filter(User.username == username)
            .first()
        )
        if not user or not user.is_active:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    def issue_token(self, user: User) -> str:
        return create_access_token(user.id, extra={"role": user.role.code})

    def list_users(self) -> list[User]:
        return (
            self.db.query(User)
            .options(joinedload(User.role))
            .order_by(User.id.asc())
            .all()
        )

    def create_user(self, payload: UserCreate) -> User:
        role = self.db.query(Role).filter(Role.code == payload.role).first()
        if not role:
            raise ValueError(f"Неизвестная роль: {payload.role}")
        if self.db.query(User).filter(User.username == payload.username).first():
            raise ValueError("Пользователь с таким именем уже существует")
        user = User(
            username=payload.username,
            password_hash=hash_password(payload.password),
            full_name=payload.full_name,
            email=payload.email,
            role_id=role.id,
            is_active=True,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return (
            self.db.query(User)
            .options(joinedload(User.role))
            .filter(User.id == user.id)
            .one()
        )

    def update_user(self, user_id: int, payload: UserUpdate) -> User:
        user = (
            self.db.query(User)
            .options(joinedload(User.role))
            .filter(User.id == user_id)
            .first()
        )
        if not user:
            raise LookupError("Пользователь не найден")
        data = payload.model_dump(exclude_unset=True)
        if "role" in data and data["role"] is not None:
            role = self.db.query(Role).filter(Role.code == data.pop("role")).first()
            if not role:
                raise ValueError("Неизвестная роль")
            user.role_id = role.id
        if "password" in data and data["password"]:
            user.password_hash = hash_password(data.pop("password"))
        for key, value in data.items():
            setattr(user, key, value)
        self.db.commit()
        self.db.refresh(user)
        return (
            self.db.query(User)
            .options(joinedload(User.role))
            .filter(User.id == user.id)
            .one()
        )

    @staticmethod
    def to_out(user: User) -> dict:
        return {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role.code,
            "role_name": user.role.name,
            "is_active": user.is_active,
        }

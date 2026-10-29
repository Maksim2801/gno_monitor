from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    TECHNOLOGIST = "technologist"
    VIEWER = "viewer"


ROLE_LABELS = {
    UserRole.ADMIN: "Администратор",
    UserRole.TECHNOLOGIST: "Технолог",
    UserRole.VIEWER: "Просмотр",
}


def can_write(role: str) -> bool:
    return role in {UserRole.ADMIN, UserRole.TECHNOLOGIST}


def can_manage_users(role: str) -> bool:
    return role == UserRole.ADMIN


def can_ack_alerts(role: str) -> bool:
    return role in {UserRole.ADMIN, UserRole.TECHNOLOGIST}

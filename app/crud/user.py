from sqlalchemy import insert, select, delete, update, func
from datetime import datetime
import uuid

from app.models.users import User
from app.db.connection import engine


def create_user(
    name: str,
    email: str,
    password: str,
    agree_to_terms: bool,
    age: int,
    role: int = None,
    is_active: bool = False,
    last_login: datetime = None,
    profile: str = None,
    company: str = None,
    position: str = None,
):
    new_user = {
        "name": name,
        "email": email,
        "password": password,
        "agree_to_terms": agree_to_terms,
        "age": age,
        "role": role,
        "is_active": is_active,
        "last_login": last_login,
        "profile": profile,
        "company": company,
        "position": position,
    }

    query = insert(User).values(**new_user)

    with engine.begin() as conn:
        conn.execute(query)


def get_user_by_email(email: str):
    query = select(User).where(User.email == email)

    with engine.begin() as conn:
        result = conn.execute(query)
        return result


def get_all_users():
    query = select(User)

    with engine.begin() as conn:
        result = conn.execute(query).fetchall()
        return [dict(row) for row in result]


def get_user_by_id(id: uuid):
    query = select(User).where(User.id == id)

    with engine.begin() as conn:
        result = conn.execute(query)
        return result


def update_user_details(
    name: str,
    password: str,
    age: int,
    role: int,
    profile: str,
    company: str,
    position: str,
    updated_at: datetime = func.now(),
):
    new_data = {
        "name": name,
        "password": password,
        "age": age,
        "role": role,
        "profile": profile,
        "company": company,
        "position": position,
        "updated_at": updated_at,
    }
    query = update(User).where(User.id == id).values(new_data)

    with engine.begin() as conn:
        result = conn.execute(query)
        return result


def delete_user(id: uuid):
    query = delete(User).where(User.id == id)

    with engine.begin() as conn:
        result = conn.execute(query)
        return result.rowcount

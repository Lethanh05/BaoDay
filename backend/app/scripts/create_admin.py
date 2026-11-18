import argparse
from getpass import getpass

from pydantic import ValidationError

from app.core.errors import ApiError
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.user import Role
from app.schemas.auth import RegisterRequest
from app.services.auth import create_user


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a Bao Day admin account.")
    parser.add_argument("--username", required=True)
    parser.add_argument("--email", required=True)
    args = parser.parse_args()

    password = getpass("Admin password: ")
    if password != getpass("Confirm password: "):
        parser.exit(1, "Passwords do not match.\n")
    try:
        data = RegisterRequest(username=args.username, email=args.email, password=password)
    except ValidationError:
        parser.exit(1, "Use a valid email, a username of 3-50 characters and a password of 8-128 characters.\n")

    Base.metadata.create_all(engine)
    try:
        with SessionLocal() as db:
            user = create_user(db, data, role=Role.ADMIN)
    except ApiError as exc:
        parser.exit(1, f"Could not create admin ({exc.code}).\n")
    print(f"Created admin with ID {user.id}.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Password Reset Script
Usage: python reset_password.py <email> <new_password>
"""

import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import User
from auth import hash_password

DATABASE_URL = "sqlite:///./readin_ai.db"

def reset_password(email: str, new_password: str):
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    user = session.query(User).filter(User.email == email).first()

    if not user:
        print(f"Error: No user found with email '{email}'")
        session.close()
        return False

    user.hashed_password = hash_password(new_password)
    session.commit()
    session.close()

    print(f"Password successfully reset for {email}")
    return True

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python reset_password.py <email> <new_password>")
        sys.exit(1)

    email = sys.argv[1]
    new_password = sys.argv[2]

    success = reset_password(email, new_password)
    sys.exit(0 if success else 1)

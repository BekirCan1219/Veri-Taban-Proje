from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token
from app.models.user import User
from app.repositories.user_repo import UserRepo

class AuthService:
    @staticmethod
    def register(username: str, email: str, password: str, role: str = "user"):
        if UserRepo.get_by_username(username) or UserRepo.get_by_email(email):
            raise ValueError("Kullanıcı adı veya e-posta zaten kayıtlı")

        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            role=role
        )
        UserRepo.create(user)
        return user

    @staticmethod
    def login(username: str, password: str):
        user = UserRepo.get_by_username(username)
        if not user or not check_password_hash(user.password_hash, password):
            raise ValueError("Hatalı kullanıcı adı veya şifre")

        token = create_access_token(
            identity=str(user.id),
            additional_claims={"role": user.role, "username": user.username}
        )
        return token, user

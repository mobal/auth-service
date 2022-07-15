import bcrypt


class PasswordUtils:
    @classmethod
    def hash(cls, password: str) -> str:
        return bcrypt.hashpw(bytes(password), bcrypt.gensalt()).decode()

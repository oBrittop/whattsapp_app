import os
from cryptography.fernet import Fernet

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", Fernet.generate_key().decode("utf-8"))
cipher_suite = Fernet(ENCRYPTION_KEY.encode("utf-8"))

def encrypt_data(data: str) -> str:
    """
    Criptografa uma string em texto plano para armazenamento seguro.
    """
    if not data:
        return data
    return cipher_suite.encrypt(data.encode("utf-8")).decode("utf-8")

def decrypt_data(encrypted_data: str) -> str:
    """
    Descriptografa uma string armazenada para uso em memoria.
    """
    if not encrypted_data:
        return encrypted_data
    return cipher_suite.decrypt(encrypted_data.encode("utf-8")).decode("utf-8")

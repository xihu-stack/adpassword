"""敏感凭据对称加密（Fernet）。密钥来自环境变量 SECRET_ENCRYPTION_KEY。"""
import os
from cryptography.fernet import Fernet, InvalidToken


def _fernet():
    key = os.getenv('SECRET_ENCRYPTION_KEY')
    if not key:
        raise RuntimeError('SECRET_ENCRYPTION_KEY 环境变量未设置')
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_value(plain):
    """加密明文，返回字符串 token。空值原样返回。"""
    if plain is None or plain == '':
        return plain
    return _fernet().encrypt(plain.encode('utf-8')).decode('utf-8')


def decrypt_value(token):
    """解密 token，返回明文。非 token/损坏返回 None。"""
    if token is None or token == '':
        return None
    try:
        return _fernet().decrypt(token.encode('utf-8')).decode('utf-8')
    except (InvalidToken, Exception):
        return None


def is_encrypted(value):
    """判断一个值是否已经是加密 token（启发式：Fernet token 以 gAAAA 开头）。"""
    return isinstance(value, str) and value.startswith('gAAAA')

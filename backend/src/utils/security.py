import hashlib, hmac, os, time
import jwt
from ..config.settings import JWT_SECRET
def hash_password(password):
    salt = os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 210000).hex()
    return salt + ":" + digest
def verify_password(password, encoded):
    salt, digest = encoded.split(":")
    return hmac.compare_digest(digest, hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 210000).hex())
def make_token(user):
    return jwt.encode({"sub": str(user.id), "exp": int(time.time())+28800}, JWT_SECRET, algorithm="HS256")

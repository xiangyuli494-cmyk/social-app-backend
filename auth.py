import jwt
import hashlib
import time
from functools import wraps
from flask import request, jsonify, g
from supabase_client import db

SECRET_KEY = 'social_app_secret_key_2024'
TOKEN_EXPIRE = 7 * 24 * 3600  # 7 days


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def generate_token(user_id):
    payload = {
        'user_id': user_id,
        'exp': int(time.time()) + TOKEN_EXPIRE
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')


def verify_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload['user_id']
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_id = verify_token(token)
        if not user_id:
            return jsonify({'code': 401, 'msg': '请先登录'}), 401

        result = db().table('users').select('*').eq('id', user_id).execute()
        if not result.data:
            return jsonify({'code': 401, 'msg': '用户不存在'}), 401

        g.current_user = result.data[0]
        return f(*args, **kwargs)
    return decorated

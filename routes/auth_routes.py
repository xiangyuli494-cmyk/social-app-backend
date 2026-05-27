from flask import Blueprint, request, jsonify
from supabase_client import db
from auth import hash_password, generate_token
import re
import uuid

auth_bp = Blueprint('auth', __name__)


def generate_uid():
    return uuid.uuid4().hex[:8].upper()


@auth_bp.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    phone = data.get('phone', '').strip()
    password = data.get('password', '').strip()
    nickname = data.get('nickname', '新用户').strip()

    if not re.match(r'^1[3-9]\d{9}$', phone):
        return jsonify({'code': 400, 'msg': '请输入正确的手机号'})
    if len(password) < 6:
        return jsonify({'code': 400, 'msg': '密码至少6位'})

    supabase = db()
    exist = supabase.table('users').select('id').eq('phone', phone).execute()
    if exist.data:
        return jsonify({'code': 400, 'msg': '该手机号已注册'})

    uid = generate_uid()
    while supabase.table('users').select('id').eq('uid', uid).execute().data:
        uid = generate_uid()

    result = supabase.table('users').insert({
        'uid': uid, 'phone': phone,
        'password_hash': hash_password(password),
        'nickname': nickname
    }).execute()
    user = result.data[0]
    token = generate_token(user['id'])

    return jsonify({
        'code': 200, 'msg': '注册成功',
        'data': {'token': token, 'user': dict_user(user)}
    })


@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    phone = data.get('phone', '').strip()
    password = data.get('password', '').strip()

    supabase = db()
    result = supabase.table('users').select('*') \
        .eq('phone', phone) \
        .eq('password_hash', hash_password(password)) \
        .execute()

    if not result.data:
        return jsonify({'code': 400, 'msg': '手机号或密码错误'})

    user = result.data[0]
    token = generate_token(user['id'])
    return jsonify({
        'code': 200, 'msg': '登录成功',
        'data': {'token': token, 'user': dict_user(user)}
    })


@auth_bp.route('/api/auth/sms', methods=['POST'])
def sms_login():
    data = request.get_json()
    phone = data.get('phone', '').strip()
    code = data.get('code', '').strip()

    if not re.match(r'^1[3-9]\d{9}$', phone):
        return jsonify({'code': 400, 'msg': '请输入正确的手机号'})
    if code != '1234':
        return jsonify({'code': 400, 'msg': '验证码错误'})

    supabase = db()
    result = supabase.table('users').select('*').eq('phone', phone).execute()

    if not result.data:
        uid = generate_uid()
        while supabase.table('users').select('id').eq('uid', uid).execute().data:
            uid = generate_uid()
        result = supabase.table('users').insert({
            'uid': uid, 'phone': phone,
            'password_hash': hash_password(phone[-6:]),
            'nickname': '用户' + phone[-4:]
        }).execute()

    user = result.data[0] if result.data else None
    if not user:
        result = supabase.table('users').select('*').eq('phone', phone).execute()
        user = result.data[0]

    token = generate_token(user['id'])
    return jsonify({
        'code': 200, 'msg': '登录成功',
        'data': {'token': token, 'user': dict_user(user)}
    })


def dict_user(user):
    return {
        'id': user['id'],
        'uid': user.get('uid') or '',
        'phone': user['phone'],
        'nickname': user['nickname'],
        'avatar': user.get('avatar') or '',
        'bio': user.get('bio') or '',
        'created_at': user.get('created_at', '')
    }

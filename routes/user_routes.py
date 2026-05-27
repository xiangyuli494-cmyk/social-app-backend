import io
import uuid
from flask import Blueprint, request, jsonify
from PIL import Image
from supabase_client import db, upload_file
from auth import login_required, g

user_bp = Blueprint('user', __name__)


@user_bp.route('/api/user/profile', methods=['GET'])
@login_required
def get_profile():
    return jsonify({'code': 200, 'data': g.current_user})


@user_bp.route('/api/user/profile', methods=['PUT'])
@login_required
def update_profile():
    data = request.get_json()
    nickname = data.get('nickname', '').strip()
    bio = data.get('bio', '').strip()

    if nickname and len(nickname) > 20:
        return jsonify({'code': 400, 'msg': '昵称不能超过20字'})
    if bio and len(bio) > 100:
        return jsonify({'code': 400, 'msg': '简介不能超过100字'})

    supabase = db()
    updates = {}
    if nickname:
        updates['nickname'] = nickname
    if bio:
        updates['bio'] = bio

    if updates:
        supabase.table('users').update(updates).eq('id', g.current_user['id']).execute()

    result = supabase.table('users').select('*').eq('id', g.current_user['id']).execute()
    return jsonify({'code': 200, 'msg': '更新成功', 'data': dict(result.data[0])})


@user_bp.route('/api/user/avatar', methods=['POST'])
@login_required
def upload_avatar():
    file = request.files.get('avatar')
    if not file:
        return jsonify({'code': 400, 'msg': '请选择图片'})

    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'jpg'
    if ext not in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
        ext = 'jpg'

    img = Image.open(file)
    img.thumbnail((400, 400), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format='JPEG' if ext in ('jpg', 'jpeg') else ext.upper(), quality=75)
    buf.seek(0)

    path = f"avatars/{g.current_user['id']}_{uuid.uuid4().hex[:8]}.{ext}"
    avatar_url = upload_file('avatars', path, buf.read(), f'image/{ext}')

    supabase = db()
    supabase.table('users').update({'avatar': avatar_url}).eq('id', g.current_user['id']).execute()

    return jsonify({'code': 200, 'msg': '上传成功', 'data': {'avatar': avatar_url}})


@user_bp.route('/api/users/<int:user_id>', methods=['GET'])
@login_required
def user_space(user_id):
    supabase = db()
    result = supabase.table('users').select('id, uid, nickname, avatar, bio, created_at') \
        .eq('id', user_id).execute()
    if not result.data:
        return jsonify({'code': 404, 'msg': '用户不存在'}), 404

    user = result.data[0]
    count_result = supabase.table('posts').select('*', count='exact').eq('user_id', user_id).execute()

    return jsonify({
        'code': 200,
        'data': {
            'id': user['id'], 'uid': user.get('uid') or '',
            'nickname': user['nickname'], 'avatar': user.get('avatar') or '',
            'bio': user.get('bio') or '',
            'post_count': count_result.count or 0,
            'created_at': user.get('created_at', '')
        }
    })


@user_bp.route('/api/users/<int:user_id>/posts', methods=['GET'])
@login_required
def user_posts(user_id):
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 20, type=int)
    offset = (page - 1) * size

    supabase = db()
    my_id = g.current_user['id']

    total_result = supabase.table('posts').select('*', count='exact') \
        .eq('user_id', user_id).execute()
    total = total_result.count or 0

    posts_result = supabase.table('posts').select(
        '*, user_id(id, nickname, avatar), likes(count), comments(count)'
    ).eq('user_id', user_id) \
     .order('created_at', desc=True) \
     .range(offset, offset + size - 1).execute()

    posts = posts_result.data
    post_ids = [p['id'] for p in posts]

    liked_post_ids = set()
    if post_ids:
        liked = supabase.table('likes').select('post_id') \
            .eq('user_id', my_id) \
            .in_('post_id', post_ids).execute()
        liked_post_ids = {r['post_id'] for r in liked.data}

    return jsonify({
        'code': 200,
        'data': {
            'list': [_post_dict(p, liked_post_ids) for p in posts],
            'total': total, 'page': page, 'size': size,
            'has_more': offset + size < total
        }
    })


@user_bp.route('/api/user/posts', methods=['GET'])
@login_required
def my_posts():
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 20, type=int)
    offset = (page - 1) * size

    supabase = db()
    my_id = g.current_user['id']

    total_result = supabase.table('posts').select('*', count='exact') \
        .eq('user_id', my_id).execute()
    total = total_result.count or 0

    posts_result = supabase.table('posts').select(
        '*, user_id(id, nickname, avatar), likes(count), comments(count)'
    ).eq('user_id', my_id) \
     .order('created_at', desc=True) \
     .range(offset, offset + size - 1).execute()

    posts = posts_result.data

    return jsonify({
        'code': 200,
        'data': {
            'list': [_post_dict(p, set()) for p in posts],
            'total': total, 'page': page, 'size': size,
            'has_more': offset + size < total
        }
    })


def _post_dict(p, liked_post_ids=None):
    if liked_post_ids is None:
        liked_post_ids = set()

    # Handle nested user_id from join
    author = p.get('user_id') if isinstance(p.get('user_id'), dict) else {}
    # Handle nested likes/comments counts
    likes_data = p.get('likes', [])
    comments_data = p.get('comments', [])
    like_count = likes_data[0]['count'] if likes_data else 0
    comment_count = comments_data[0]['count'] if comments_data else 0

    images = p.get('images') or ''
    if isinstance(images, str) and images:
        images_list = images.split(',')
    else:
        images_list = []

    return {
        'id': p['id'], 'user_id': p['user_id'] if isinstance(p['user_id'], int) else author.get('id'),
        'content': p.get('content') or '',
        'images': images_list,
        'video': p.get('video') or '',
        'location': p.get('location') or '',
        'nickname': author.get('nickname') or '',
        'avatar': author.get('avatar') or '',
        'like_count': like_count,
        'comment_count': comment_count,
        'is_liked': p['id'] in liked_post_ids,
        'view_count': p.get('view_count') or 0,
        'created_at': p.get('created_at', '')
    }


def dict(row):
    return {
        'id': row['id'], 'uid': row.get('uid') or '',
        'phone': row.get('phone', ''), 'nickname': row.get('nickname', ''),
        'avatar': row.get('avatar') or '', 'bio': row.get('bio') or '',
        'created_at': row.get('created_at', '')
    }

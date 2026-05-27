import io
import uuid
from flask import Blueprint, request, jsonify
from PIL import Image
from supabase_client import db, upload_file, delete_file, SUPABASE_URL
from auth import login_required, g

post_bp = Blueprint('post', __name__)

ALLOWED_IMAGE = {'jpg', 'jpeg', 'png', 'gif', 'webp'}


@post_bp.route('/api/posts', methods=['GET'])
@login_required
def feed():
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 20, type=int)
    offset = (page - 1) * size
    my_id = g.current_user['id']

    supabase = db()

    total_result = supabase.table('posts').select('*', count='exact').execute()
    total = total_result.count or 0

    posts_result = supabase.table('posts').select(
        '*, user_id(id, nickname, avatar), likes(count), comments(count)'
    ).order('created_at', desc=True) \
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
            'list': [_post_dict(row, liked_post_ids) for row in posts],
            'total': total, 'page': page, 'size': size,
            'has_more': offset + size < total
        }
    })


@post_bp.route('/api/posts', methods=['POST'])
@login_required
def create_post():
    content = request.form.get('content', '').strip()
    images_str = ''

    if not content and 'images' not in request.files:
        return jsonify({'code': 400, 'msg': '请输入内容或上传图片'})

    uid = g.current_user['id']

    images = request.files.getlist('images')
    if images:
        image_urls = []
        for img in images[:9]:
            if img and img.filename:
                ext = img.filename.rsplit('.', 1)[-1].lower() if '.' in img.filename else 'jpg'
                if ext in ALLOWED_IMAGE:
                    try:
                        im = Image.open(img)
                        max_size = (1280, 1280)
                        im.thumbnail(max_size, Image.LANCZOS)
                        buf = io.BytesIO()
                        fmt = 'JPEG' if ext in ('jpg', 'jpeg') else ext.upper()
                        im.save(buf, format=fmt, quality=80)
                        buf.seek(0)

                        mime = f'image/{"jpeg" if ext in ("jpg","jpeg") else ext}'
                        path = f'posts/{uid}/img_{uuid.uuid4().hex[:8]}.{ext}'
                        url = upload_file('posts', path, buf.read(), mime)
                        image_urls.append(url)
                    except Exception:
                        pass
        images_str = ','.join(image_urls)

    supabase = db()
    result = supabase.table('posts').insert({
        'user_id': uid,
        'content': content,
        'images': images_str,
        'video': ''
    }).execute()
    post_id = result.data[0]['id']

    post_result = supabase.table('posts').select(
        '*, user_id(id, nickname, avatar)'
    ).eq('id', post_id).execute()

    post = post_result.data[0] if post_result.data else result.data[0]
    return jsonify({'code': 200, 'msg': '发布成功', 'data': _post_dict(post, set())})


@post_bp.route('/api/posts/<int:post_id>', methods=['DELETE'])
@login_required
def delete_post(post_id):
    supabase = db()
    result = supabase.table('posts').select('*') \
        .eq('id', post_id).eq('user_id', g.current_user['id']).execute()

    if not result.data:
        return jsonify({'code': 404, 'msg': '动态不存在'}), 404

    post = result.data[0]
    supabase_url_prefix = f'{SUPABASE_URL}/storage/v1/object/public/'
    for field in ['images', 'video']:
        val = post.get(field) or ''
        if val:
            for url in val.split(','):
                url = url.strip()
                if url.startswith(supabase_url_prefix):
                    # Extract bucket/path from URL
                    # Format: .../public/{bucket}/{path}
                    obj_path = url[len(supabase_url_prefix):]
                    parts = obj_path.split('/', 1)
                    if len(parts) == 2:
                        bucket, path = parts
                        try:
                            delete_file(bucket, path)
                        except Exception:
                            pass

    supabase.table('posts').delete().eq('id', post_id).execute()
    return jsonify({'code': 200, 'msg': '删除成功'})


@post_bp.route('/api/posts/<int:post_id>/like', methods=['POST'])
@login_required
def like_post(post_id):
    supabase = db()
    my_id = g.current_user['id']

    exist = supabase.table('likes').select('id') \
        .eq('user_id', my_id).eq('post_id', post_id).execute()

    if exist.data:
        supabase.table('likes').delete().eq('id', exist.data[0]['id']).execute()
        return jsonify({'code': 200, 'msg': '取消点赞', 'data': {'liked': False}})
    else:
        supabase.table('likes').insert({
            'user_id': my_id, 'post_id': post_id
        }).execute()
        return jsonify({'code': 200, 'msg': '点赞成功', 'data': {'liked': True}})


@post_bp.route('/api/posts/<int:post_id>/comments', methods=['GET'])
@login_required
def get_comments(post_id):
    supabase = db()
    comments = supabase.table('comments').select(
        '*, user_id(id, nickname, avatar)'
    ).eq('post_id', post_id) \
     .order('created_at').execute()

    return jsonify({
        'code': 200,
        'data': {'list': [_comment_dict(row) for row in comments.data]}
    })


@post_bp.route('/api/posts/<int:post_id>/comments', methods=['POST'])
@login_required
def add_comment(post_id):
    data = request.get_json()
    content = data.get('content', '').strip()
    if not content:
        return jsonify({'code': 400, 'msg': '请输入评论内容'})
    if len(content) > 500:
        return jsonify({'code': 400, 'msg': '评论不能超过500字'})

    supabase = db()
    result = supabase.table('comments').insert({
        'user_id': g.current_user['id'],
        'post_id': post_id,
        'content': content
    }).execute()
    comment_id = result.data[0]['id']

    comment_result = supabase.table('comments').select(
        '*, user_id(id, nickname, avatar)'
    ).eq('id', comment_id).execute()

    return jsonify({
        'code': 200, 'msg': '评论成功',
        'data': _comment_dict(comment_result.data[0])
    })


@post_bp.route('/api/comments/<int:comment_id>', methods=['DELETE'])
@login_required
def delete_comment(comment_id):
    supabase = db()
    result = supabase.table('comments').select('*') \
        .eq('id', comment_id).eq('user_id', g.current_user['id']).execute()

    if not result.data:
        return jsonify({'code': 404, 'msg': '评论不存在'}), 404

    supabase.table('comments').delete().eq('id', comment_id).execute()
    return jsonify({'code': 200, 'msg': '删除成功'})


def _comment_dict(row):
    author = row.get('user_id') if isinstance(row.get('user_id'), dict) else {}
    return {
        'id': row['id'], 'user_id': row['user_id'] if isinstance(row['user_id'], int) else author.get('id'),
        'post_id': row['post_id'],
        'content': row['content'],
        'nickname': author.get('nickname') or row.get('nickname') or '',
        'avatar': author.get('avatar') or row.get('avatar') or '',
        'created_at': row.get('created_at', '')
    }


def _post_dict(row, liked_post_ids=None):
    if liked_post_ids is None:
        liked_post_ids = set()

    author = row.get('user_id') if isinstance(row.get('user_id'), dict) else {}
    likes_data = row.get('likes', [])
    comments_data = row.get('comments', [])
    like_count = likes_data[0]['count'] if likes_data else 0
    comment_count = comments_data[0]['count'] if comments_data else 0

    images = row.get('images') or ''
    if isinstance(images, str) and images:
        images_list = images.split(',')
    else:
        images_list = []

    return {
        'id': row['id'],
        'user_id': row['user_id'] if isinstance(row['user_id'], int) else author.get('id'),
        'content': row.get('content') or '',
        'images': images_list,
        'video': row.get('video') or '',
        'location': row.get('location') or '',
        'nickname': author.get('nickname') or '',
        'avatar': author.get('avatar') or '',
        'like_count': like_count,
        'comment_count': comment_count,
        'is_liked': row['id'] in liked_post_ids,
        'view_count': row.get('view_count') or 0,
        'created_at': row.get('created_at', '')
    }

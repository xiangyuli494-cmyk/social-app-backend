from flask import Blueprint, request, jsonify
from supabase_client import db
from auth import login_required, g

friend_bp = Blueprint('friend', __name__)


@friend_bp.route('/api/users/search', methods=['GET'])
@login_required
def search_users():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({'code': 400, 'msg': '请输入UID'})

    supabase = db()
    result = supabase.table('users').select('id, uid, nickname, avatar, bio') \
        .ilike('uid', f'%{q}%').limit(20).execute()

    return jsonify({
        'code': 200,
        'data': {'list': [_user_dict(row) for row in result.data]}
    })


@friend_bp.route('/api/friends', methods=['GET'])
@login_required
def get_friends():
    my_id = g.current_user['id']
    supabase = db()

    f1 = supabase.table('friendships').select('friend_id, created_at') \
        .eq('user_id', my_id).eq('status', 'accepted').execute()
    f2 = supabase.table('friendships').select('user_id, created_at') \
        .eq('friend_id', my_id).eq('status', 'accepted').execute()

    friends_map = {}
    for r in f1.data:
        friends_map[r['friend_id']] = r.get('created_at', '')
    for r in f2.data:
        friends_map[r['user_id']] = r.get('created_at', '')

    if not friends_map:
        return jsonify({'code': 200, 'data': {'list': []}})

    friend_ids = list(friends_map.keys())
    users_result = supabase.table('users').select('id, uid, nickname, avatar, bio') \
        .in_('id', friend_ids).execute()

    friends_list = []
    for u in users_result.data:
        uid = u['id']
        # Get last message: check both directions
        last_msg = ''
        msg_a = supabase.table('messages').select('content, created_at') \
            .eq('sender_id', my_id).eq('receiver_id', uid) \
            .order('created_at', desc=True).limit(1).execute()
        msg_b = supabase.table('messages').select('content, created_at') \
            .eq('sender_id', uid).eq('receiver_id', my_id) \
            .order('created_at', desc=True).limit(1).execute()

        all_msgs = msg_a.data + msg_b.data
        if all_msgs:
            all_msgs.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            last_msg = all_msgs[0].get('content') or ''

        friends_list.append({
            'id': u['id'], 'uid': u.get('uid') or '',
            'nickname': u['nickname'], 'avatar': u.get('avatar') or '',
            'bio': u.get('bio') or '',
            'last_msg': last_msg
        })

    return jsonify({'code': 200, 'data': {'list': friends_list}})


@friend_bp.route('/api/friends/add', methods=['POST'])
@login_required
def add_friend():
    data = request.get_json()
    uid = data.get('uid', '').strip()
    if not uid:
        return jsonify({'code': 400, 'msg': '请输入对方UID'})

    supabase = db()
    target = supabase.table('users').select('id, uid, nickname, avatar') \
        .eq('uid', uid).execute()
    if not target.data:
        return jsonify({'code': 404, 'msg': '未找到该用户'})

    target_user = target.data[0]
    target_id = target_user['id']
    my_id = g.current_user['id']

    if target_id == my_id:
        return jsonify({'code': 400, 'msg': '不能添加自己为好友'})

    # Check existing friendship (both directions)
    d1 = supabase.table('friendships').select('id') \
        .eq('user_id', my_id).eq('friend_id', target_id).execute()
    d2 = supabase.table('friendships').select('id') \
        .eq('user_id', target_id).eq('friend_id', my_id).execute()
    if d1.data or d2.data:
        return jsonify({'code': 400, 'msg': '已经是好友了'})

    supabase.table('friendships').insert({
        'user_id': my_id, 'friend_id': target_id
    }).execute()

    return jsonify({
        'code': 200, 'msg': '添加成功',
        'data': {
            'id': target_user['id'], 'uid': target_user.get('uid') or '',
            'nickname': target_user['nickname'], 'avatar': target_user.get('avatar') or ''
        }
    })


@friend_bp.route('/api/friends/<int:friend_id>', methods=['DELETE'])
@login_required
def remove_friend(friend_id):
    my_id = g.current_user['id']
    supabase = db()

    supabase.table('friendships').delete() \
        .eq('user_id', my_id).eq('friend_id', friend_id).execute()
    supabase.table('friendships').delete() \
        .eq('user_id', friend_id).eq('friend_id', my_id).execute()

    return jsonify({'code': 200, 'msg': '删除成功'})


@friend_bp.route('/api/friends/<int:friend_id>/status', methods=['GET'])
@login_required
def friend_status(friend_id):
    my_id = g.current_user['id']
    supabase = db()

    d1 = supabase.table('friendships').select('id') \
        .eq('user_id', my_id).eq('friend_id', friend_id).eq('status', 'accepted').execute()
    d2 = supabase.table('friendships').select('id') \
        .eq('user_id', friend_id).eq('friend_id', my_id).eq('status', 'accepted').execute()

    return jsonify({
        'code': 200,
        'data': {'is_friend': bool(d1.data or d2.data)}
    })


def _user_dict(row):
    return {
        'id': row['id'], 'uid': row.get('uid') or '',
        'nickname': row['nickname'], 'avatar': row.get('avatar') or '',
        'bio': row.get('bio') or ''
    }

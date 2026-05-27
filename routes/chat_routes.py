from flask import Blueprint, request, jsonify
from supabase_client import db
from auth import login_required, g

chat_bp = Blueprint('chat', __name__)


@chat_bp.route('/api/conversations', methods=['GET'])
@login_required
def conversations():
    my_id = g.current_user['id']
    supabase = db()

    sent = supabase.table('messages').select('receiver_id').eq('sender_id', my_id).execute()
    received = supabase.table('messages').select('sender_id').eq('receiver_id', my_id).execute()

    peer_ids = set()
    for r in sent.data:
        peer_ids.add(r['receiver_id'])
    for r in received.data:
        peer_ids.add(r['sender_id'])

    if not peer_ids:
        return jsonify({'code': 200, 'data': {'list': []}})

    users_result = supabase.table('users').select('id, uid, nickname, avatar') \
        .in_('id', list(peer_ids)).execute()
    users_map = {u['id']: u for u in users_result.data}

    conv_list = []
    for peer_id in peer_ids:
        # Get last message from both directions
        a = supabase.table('messages').select('sender_id, content, created_at') \
            .eq('sender_id', my_id).eq('receiver_id', peer_id) \
            .order('created_at', desc=True).limit(1).execute()
        b = supabase.table('messages').select('sender_id, content, created_at') \
            .eq('sender_id', peer_id).eq('receiver_id', my_id) \
            .order('created_at', desc=True).limit(1).execute()

        all_msgs = a.data + b.data
        if not all_msgs:
            continue

        all_msgs.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        last = all_msgs[0]

        user = users_map.get(peer_id)
        if not user:
            continue

        conv_list.append({
            'id': user['id'],
            'uid': user.get('uid') or '',
            'nickname': user['nickname'],
            'avatar': user.get('avatar') or '',
            'last_msg': last.get('content') or '',
            'last_time': last.get('created_at') or '',
            'is_me': last['sender_id'] == my_id
        })

    conv_list.sort(key=lambda x: x['last_time'] or '', reverse=True)

    return jsonify({'code': 200, 'data': {'list': conv_list}})


@chat_bp.route('/api/messages/<int:peer_id>', methods=['GET'])
@login_required
def get_messages(peer_id):
    my_id = g.current_user['id']
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 50, type=int)
    offset = (page - 1) * size

    supabase = db()

    # Mark messages as read
    unread = supabase.table('messages').select('id') \
        .eq('sender_id', peer_id).eq('receiver_id', my_id).eq('is_read', 0).execute()
    for r in unread.data:
        supabase.table('messages').update({'is_read': 1}).eq('id', r['id']).execute()

    # Count total in both directions
    a_count = supabase.table('messages').select('*', count='exact') \
        .eq('sender_id', my_id).eq('receiver_id', peer_id).execute()
    b_count = supabase.table('messages').select('*', count='exact') \
        .eq('sender_id', peer_id).eq('receiver_id', my_id).execute()
    total = (a_count.count or 0) + (b_count.count or 0)

    # Get messages from both directions and merge
    a = supabase.table('messages').select('*') \
        .eq('sender_id', my_id).eq('receiver_id', peer_id) \
        .order('created_at', desc=True).limit(size * 2).execute()
    b = supabase.table('messages').select('*') \
        .eq('sender_id', peer_id).eq('receiver_id', my_id) \
        .order('created_at', desc=True).limit(size * 2).execute()

    all_msgs = a.data + b.data
    all_msgs.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    all_msgs = all_msgs[offset:offset + size]

    msg_list = [_msg_dict(row) for row in all_msgs]
    msg_list.reverse()

    return jsonify({
        'code': 200,
        'data': {
            'list': msg_list,
            'total': total, 'page': page, 'size': size,
            'has_more': offset + size < total
        }
    })


@chat_bp.route('/api/messages', methods=['POST'])
@login_required
def send_message():
    data = request.get_json()
    receiver_id = data.get('receiver_id')
    content = data.get('content', '').strip()

    if not receiver_id or not content:
        return jsonify({'code': 400, 'msg': '缺少参数'})
    if len(content) > 1000:
        return jsonify({'code': 400, 'msg': '消息太长'})

    supabase = db()
    my_id = g.current_user['id']

    # Check friendship (both directions)
    d1 = supabase.table('friendships').select('id') \
        .eq('user_id', my_id).eq('friend_id', receiver_id).eq('status', 'accepted').execute()
    d2 = supabase.table('friendships').select('id') \
        .eq('user_id', receiver_id).eq('friend_id', my_id).eq('status', 'accepted').execute()

    if not d1.data and not d2.data:
        return jsonify({'code': 403, 'msg': '只能给好友发送消息'})

    result = supabase.table('messages').insert({
        'sender_id': my_id,
        'receiver_id': receiver_id,
        'content': content
    }).execute()

    return jsonify({
        'code': 200, 'msg': '发送成功',
        'data': _msg_dict(result.data[0])
    })


def _msg_dict(row):
    return {
        'id': row['id'],
        'sender_id': row['sender_id'],
        'receiver_id': row['receiver_id'],
        'content': row['content'],
        'is_read': row.get('is_read', 0),
        'created_at': row.get('created_at', '')
    }

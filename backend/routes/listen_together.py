from flask import Blueprint
from flask_socketio import join_room, leave_room
import time

listen_bp = Blueprint('listen', __name__)

# Global shared room — no codes needed
# members: { sid: { nickname, user_id } }
# state: current playback state
listen_members = {}
listen_state = {
    'songId': None,
    'songData': None,
    'isPlaying': False,
    'position': 0,
    'updatedAt': 0,
}
dj_sid = None  # SID of the current DJ (first to join)

socketio = None
ROOM = 'listen_global'


def _get_dj_info():
    """Return DJ info dict or None."""
    global dj_sid
    if dj_sid and dj_sid in listen_members:
        m = listen_members[dj_sid]
        return {'nickname': m['nickname'], 'user_id': m['user_id']}
    return None


def _pick_new_dj(sio, announce=True):
    """Pick the first remaining member as DJ. Broadcast if changed."""
    global dj_sid
    old_dj = dj_sid
    if listen_members:
        dj_sid = next(iter(listen_members))
    else:
        dj_sid = None

    if announce and dj_sid and dj_sid != old_dj:
        new_dj_info = listen_members[dj_sid]
        # Notify everyone in the room about DJ change
        sio.emit('listen_dj_change', {
            'nickname': new_dj_info['nickname'],
            'user_id': new_dj_info['user_id'],
        }, room=ROOM)


def init_listen_socketio(sio):
    global socketio
    socketio = sio

    @sio.on('listen_join')
    def handle_join(data=None):
        global dj_sid
        from flask import request as req
        from routes.chat import online_users
        user = online_users.get(req.sid)
        if not user:
            sio.emit('listen_error', {'msg': '请先登录'}, to=req.sid)
            return

        # 已在房间 — 可能是 tab 切回后重连 rejoin，补发当前状态
        if req.sid in listen_members:
            sio.emit('listen_update', {
                'members': _members_list(),
                'state': _estimated_state(),
                'dj': _get_dj_info(),
                'msg': '',
            }, to=req.sid)
            return

        listen_members[req.sid] = {'nickname': user['nickname'], 'user_id': user['id']}
        join_room(ROOM)

        # First member becomes DJ
        is_new_dj = False
        if dj_sid is None or dj_sid not in listen_members:
            dj_sid = req.sid
            is_new_dj = True

        ml = _members_list()
        dj_info = _get_dj_info()
        state_snap = _estimated_state()
        print(f'[listen_join] {user["nickname"]} joined, now {len(ml)} members, DJ={dj_info and dj_info["nickname"]}')
        sio.emit('listen_update', {
            'members': ml,
            'state': state_snap,
            'dj': dj_info,
            'msg': f'{user["nickname"]} 加入了一起听',
        }, room=ROOM)

        # If this user became DJ, notify (only if there are other members already)
        if is_new_dj and len(listen_members) > 1:
            sio.emit('listen_dj_change', {
                'nickname': user['nickname'],
                'user_id': user['id'],
            }, room=ROOM)

    @sio.on('listen_leave')
    def handle_leave(data=None):
        from flask import request as req
        _remove(req.sid, sio)

    @sio.on('listen_sync')
    def handle_sync(data):
        from flask import request as req
        from routes.chat import online_users
        user = online_users.get(req.sid)
        if not user or req.sid not in listen_members:
            print(f'[listen_sync] rejected: user={bool(user)}, in_members={req.sid in listen_members}')
            return

        print(f'[listen_sync] from {user["nickname"]}: action={data.get("action")}, songId={data.get("songId")}')

        if 'songId' in data:
            listen_state['songId'] = data['songId']
            listen_state['songData'] = data.get('songData')
        if 'isPlaying' in data:
            listen_state['isPlaying'] = data['isPlaying']
        if 'position' in data:
            listen_state['position'] = data['position']
        listen_state['updatedAt'] = time.time()

        member_count = len(listen_members)
        print(f'[listen_sync] broadcasting listen_state to {member_count} members, state songId={listen_state["songId"]}')
        sio.emit('listen_state', {
            'state': listen_state,
            'from': user['nickname'],
            'action': data.get('action', 'sync'),
        }, room=ROOM, skip_sid=req.sid)


def cleanup_listen_room(sid):
    if socketio:
        _remove(sid, socketio)


def _remove(sid, sio):
    global dj_sid
    info = listen_members.pop(sid, None)
    if not info:
        return
    sio.server.leave_room(sid, ROOM)
    nickname = info['nickname']

    was_dj = (sid == dj_sid)

    # If DJ left, pick a new one
    if was_dj:
        _pick_new_dj(sio, announce=True)

    sio.emit('listen_update', {
        'members': _members_list(),
        'state': listen_state,
        'dj': _get_dj_info(),
        'msg': f'{nickname} 退出了一起听',
    }, room=ROOM)

    sio.emit('listen_left', {}, to=sid)


def _members_list():
    return [{'nickname': m['nickname'], 'user_id': m['user_id']}
            for m in listen_members.values()]


def _estimated_state():
    """Return listen_state with position estimated to current time."""
    s = dict(listen_state)
    if s['isPlaying'] and s['updatedAt'] > 0:
        elapsed = time.time() - s['updatedAt']
        s['position'] = s['position'] + elapsed
    s['updatedAt'] = time.time()
    return s

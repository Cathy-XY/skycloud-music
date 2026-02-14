from flask import Blueprint
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

socketio = None
ROOM = 'listen_global'


def init_listen_socketio(sio):
    global socketio
    socketio = sio

    @sio.on('listen_join')
    def handle_join(data=None):
        from flask import request as req
        from routes.chat import online_users
        user = online_users.get(req.sid)
        if not user:
            sio.emit('listen_error', {'msg': '请先登录'}, to=req.sid)
            return

        if req.sid in listen_members:
            return  # already in

        listen_members[req.sid] = {'nickname': user['nickname'], 'user_id': user['id']}
        sio.enter_room(req.sid, ROOM)

        # Tell everyone the member list changed
        ml = _members_list()
        sio.emit('listen_update', {
            'members': ml,
            'state': listen_state,
            'msg': f'{user["nickname"]} 加入了一起听',
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
            return

        if 'songId' in data:
            listen_state['songId'] = data['songId']
            listen_state['songData'] = data.get('songData')
        if 'isPlaying' in data:
            listen_state['isPlaying'] = data['isPlaying']
        if 'position' in data:
            listen_state['position'] = data['position']
        listen_state['updatedAt'] = time.time()

        sio.emit('listen_state', {
            'state': listen_state,
            'from': user['nickname'],
            'action': data.get('action', 'sync'),
        }, room=ROOM)


def cleanup_listen_room(sid):
    if socketio:
        _remove(sid, socketio)


def _remove(sid, sio):
    info = listen_members.pop(sid, None)
    if not info:
        return
    sio.leave_room(sid, ROOM)
    nickname = info['nickname']

    sio.emit('listen_update', {
        'members': _members_list(),
        'state': listen_state,
        'msg': f'{nickname} 退出了一起听',
    }, room=ROOM)

    sio.emit('listen_left', {}, to=sid)


def _members_list():
    return [{'nickname': m['nickname'], 'user_id': m['user_id']}
            for m in listen_members.values()]

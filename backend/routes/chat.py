from flask import Blueprint, request, jsonify, g
from models import get_messages, create_message, get_user_by_id
from routes.auth import login_required
import jwt
from config import SECRET_KEY

chat_bp = Blueprint('chat', __name__)

# Store socketio reference, set from app.py
socketio = None
online_users = {}


def init_socketio(sio):
    global socketio
    socketio = sio

    @sio.on('connect')
    def handle_connect(auth=None):
        from flask import request as req
        token = None
        if auth and isinstance(auth, dict):
            token = auth.get('token', '')
        if not token:
            return False
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            user = get_user_by_id(payload['user_id'])
            if not user:
                return False
            online_users[req.sid] = user
            sio.emit('user_joined', {'nickname': user['nickname']})
            sio.emit('online_count', {'count': len(online_users)})
        except jwt.InvalidTokenError:
            return False

    @sio.on('disconnect')
    def handle_disconnect():
        from flask import request as req
        user = online_users.pop(req.sid, None)
        if user:
            sio.emit('user_left', {'nickname': user['nickname']})
            sio.emit('online_count', {'count': len(online_users)})

    @sio.on('send_message')
    def handle_message(data):
        from flask import request as req
        user = online_users.get(req.sid)
        if not user:
            return
        content = data.get('content', '').strip()
        if not content:
            return
        msg = create_message(user['id'], content)
        if msg:
            sio.emit('new_message', msg)


@chat_bp.route('/messages', methods=['GET'])
def list_messages():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    messages = get_messages(page, per_page)
    return jsonify(messages)


@chat_bp.route('/messages', methods=['POST'])
@login_required
def post_message():
    data = request.get_json()
    content = data.get('content', '').strip()
    if not content:
        return jsonify({'error': 'Content required'}), 400
    msg = create_message(g.user_id, content)
    return jsonify(msg), 201

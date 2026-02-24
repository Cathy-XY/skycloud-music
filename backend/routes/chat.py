import os
import uuid
from flask import Blueprint, request, jsonify, g, send_from_directory
from werkzeug.utils import secure_filename
from models import get_messages, create_message, get_message_with_reply, get_user_by_id
from routes.auth import login_required
import jwt
from config import SECRET_KEY, UPLOAD_DIR, MAX_IMAGE_SIZE, ALLOWED_IMAGE_EXTENSIONS

chat_bp = Blueprint('chat', __name__)

# Store socketio reference, set from app.py
socketio = None
online_users = {}


def _unique_online_count():
    """按 user_id 去重计算在线人数"""
    seen = set()
    for u in online_users.values():
        seen.add(u['id'])
    return len(seen)


def _allowed_image(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


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
            sio.emit('online_count', {'count': _unique_online_count()})
        except jwt.InvalidTokenError:
            return False

    @sio.on('disconnect')
    def handle_disconnect():
        from flask import request as req
        # Clean up listen-together room first
        from routes.listen_together import cleanup_listen_room
        cleanup_listen_room(req.sid)
        # Then clean up chat online users
        user = online_users.pop(req.sid, None)
        if user:
            sio.emit('user_left', {'nickname': user['nickname']})
            sio.emit('online_count', {'count': _unique_online_count()})

    @sio.on('send_message')
    def handle_message(data):
        from flask import request as req
        user = online_users.get(req.sid)
        if not user:
            return
        content = data.get('content', '').strip()
        image_url = data.get('image_url', '').strip() or None
        if not content and not image_url:
            return
        reply_to = data.get('reply_to')
        if reply_to is not None:
            try:
                reply_to = int(reply_to)
            except (ValueError, TypeError):
                reply_to = None
        msg = create_message(user['id'], content, reply_to=reply_to, image_url=image_url)
        if msg:
            full_msg = get_message_with_reply(msg['id'])
            sio.emit('new_message', full_msg or msg)


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
    image_url = data.get('image_url', '').strip() or None
    if not content and not image_url:
        return jsonify({'error': 'Content or image required'}), 400
    reply_to = data.get('reply_to')
    if reply_to is not None:
        try:
            reply_to = int(reply_to)
        except (ValueError, TypeError):
            reply_to = None
    msg = create_message(g.user_id, content, reply_to=reply_to, image_url=image_url)
    return jsonify(msg), 201


@chat_bp.route('/chat/upload', methods=['POST'])
@login_required
def upload_chat_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No image file'}), 400
    file = request.files['image']
    if not file.filename or not _allowed_image(file.filename):
        return jsonify({'error': 'Invalid image format. Allowed: jpg, png, gif, webp'}), 400
    file_data = file.read()
    if len(file_data) > MAX_IMAGE_SIZE:
        return jsonify({'error': 'Image too large. Max 2MB'}), 413
    ext = file.filename.rsplit('.', 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    with open(os.path.join(UPLOAD_DIR, unique_name), 'wb') as f:
        f.write(file_data)
    return jsonify({'image_url': unique_name}), 201


@chat_bp.route('/uploads/<filename>')
def serve_upload(filename):
    safe_name = secure_filename(filename)
    return send_from_directory(UPLOAD_DIR, safe_name)

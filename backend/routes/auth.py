from flask import Blueprint, request, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import time
from config import SECRET_KEY, JWT_EXPIRATION
from models import create_user, get_user_by_username, get_user_by_id
from functools import wraps

auth_bp = Blueprint('auth', __name__)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'Authentication required'}), 401
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            g.user_id = payload['user_id']
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        return f(*args, **kwargs)
    return decorated


def make_token(user_id):
    return jwt.encode(
        {'user_id': user_id, 'exp': int(time.time()) + JWT_EXPIRATION},
        SECRET_KEY,
        algorithm='HS256'
    )


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    nickname = data.get('nickname', '').strip()
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    if not nickname:
        nickname = username
    if get_user_by_username(username):
        return jsonify({'error': 'Username already taken'}), 409
    pw_hash = generate_password_hash(password, method='pbkdf2:sha256')
    user = create_user(username, pw_hash, nickname)
    token = make_token(user['id'])
    return jsonify({'token': token, 'user': user}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    user = get_user_by_username(username)
    if not user or not check_password_hash(user['password'], password):
        return jsonify({'error': 'Invalid credentials'}), 401
    token = make_token(user['id'])
    return jsonify({
        'token': token,
        'user': {'id': user['id'], 'username': user['username'], 'nickname': user['nickname']}
    })


@auth_bp.route('/me', methods=['GET'])
@login_required
def me():
    user = get_user_by_id(g.user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({'user': user})

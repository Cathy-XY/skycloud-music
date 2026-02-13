from flask import Blueprint, request, jsonify, g
from models import get_comments_by_song, create_comment, delete_comment
from routes.auth import login_required

comments_bp = Blueprint('comments', __name__)


@comments_bp.route('/songs/<int:song_id>/comments', methods=['GET'])
def list_comments(song_id):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    comments = get_comments_by_song(song_id, page, per_page)
    return jsonify(comments)


@comments_bp.route('/songs/<int:song_id>/comments', methods=['POST'])
@login_required
def add_comment(song_id):
    data = request.get_json()
    content = data.get('content', '').strip()
    if not content:
        return jsonify({'error': 'Content required'}), 400
    comment = create_comment(song_id, g.user_id, content)
    return jsonify(comment), 201


@comments_bp.route('/comments/<int:comment_id>', methods=['DELETE'])
@login_required
def remove_comment(comment_id):
    if delete_comment(comment_id, g.user_id):
        return jsonify({'message': 'Deleted'})
    return jsonify({'error': 'Comment not found or not yours'}), 404

from flask import Blueprint, request, jsonify, g
from models import get_lyrics, save_lyrics, get_lyrics_history, get_line_comments, create_line_comment, get_all_line_comments
from routes.auth import login_required

lyrics_bp = Blueprint('lyrics', __name__)


@lyrics_bp.route('/songs/<int:song_id>/lyrics', methods=['GET'])
def get_song_lyrics(song_id):
    lyric = get_lyrics(song_id)
    if not lyric:
        return jsonify({'content': '', 'edited_by_name': None, 'updated_at': None})
    return jsonify(lyric)


@lyrics_bp.route('/songs/<int:song_id>/lyrics', methods=['PUT'])
@login_required
def update_lyrics(song_id):
    data = request.get_json()
    content = data.get('content', '')
    save_lyrics(song_id, g.user_id, content)
    return jsonify({'message': 'Lyrics saved'})


@lyrics_bp.route('/songs/<int:song_id>/lyrics/history', methods=['GET'])
def lyrics_history(song_id):
    history = get_lyrics_history(song_id)
    return jsonify(history)


@lyrics_bp.route('/songs/<int:song_id>/lyrics/lines/<int:line_index>/comments', methods=['GET'])
def get_line_comments_route(song_id, line_index):
    comments = get_line_comments(song_id, line_index)
    return jsonify(comments)


@lyrics_bp.route('/songs/<int:song_id>/lyrics/lines/<int:line_index>/comments', methods=['POST'])
@login_required
def post_line_comment(song_id, line_index):
    data = request.get_json()
    content = data.get('content', '').strip()
    line_text = data.get('line_text', '').strip()
    if not content:
        return jsonify({'error': 'Content required'}), 400
    comment = create_line_comment(song_id, line_index, line_text, g.user_id, content)
    return jsonify(comment), 201


@lyrics_bp.route('/songs/<int:song_id>/lyrics/line-comments', methods=['GET'])
def get_all_line_comments_route(song_id):
    grouped = get_all_line_comments(song_id)
    return jsonify(grouped)

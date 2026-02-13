from flask import Blueprint, request, jsonify, g
from models import get_lyrics, save_lyrics, get_lyrics_history
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

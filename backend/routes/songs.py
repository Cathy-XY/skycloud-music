from flask import Blueprint, jsonify
from models import get_all_songs, get_song_by_id
from storage import serve_audio

songs_bp = Blueprint('songs', __name__)


@songs_bp.route('', methods=['GET'])
def list_songs():
    songs = get_all_songs()
    return jsonify(songs)


@songs_bp.route('/<int:song_id>', methods=['GET'])
def get_song(song_id):
    song = get_song_by_id(song_id)
    if not song:
        return jsonify({'error': 'Song not found'}), 404
    return jsonify(song)


@songs_bp.route('/<int:song_id>/stream', methods=['GET'])
def stream_song(song_id):
    song = get_song_by_id(song_id)
    if not song:
        return jsonify({'error': 'Song not found'}), 404
    return serve_audio(song['filename'])

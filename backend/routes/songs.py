from flask import Blueprint, jsonify
from models import get_all_songs, get_song_by_id, scan_songs
from storage import serve_audio, get_signed_url

songs_bp = Blueprint('songs', __name__)


@songs_bp.route('', methods=['GET'])
def list_songs():
    songs = get_all_songs()
    return jsonify(songs)


@songs_bp.route('/refresh', methods=['POST'])
def refresh_songs():
    scan_songs()
    songs = get_all_songs()
    return jsonify({'message': f'Scanned {len(songs)} songs', 'count': len(songs)})


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


@songs_bp.route('/<int:song_id>/stream-url', methods=['GET'])
def stream_url(song_id):
    song = get_song_by_id(song_id)
    if not song:
        return jsonify({'error': 'Song not found'}), 404
    url = get_signed_url(song['filename'])
    if url:
        return jsonify({'url': url})
    return jsonify({'url': f'/api/songs/{song_id}/stream'})

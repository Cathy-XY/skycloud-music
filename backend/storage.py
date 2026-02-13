import os
from flask import send_from_directory, redirect
from config import MUSIC_DIR, STORAGE_TYPE


def serve_audio(filename):
    if STORAGE_TYPE == 'oss':
        # Future: generate pre-signed URL and redirect
        # url = oss_client.sign_url('GET', BUCKET, filename, expires=3600)
        # return redirect(url)
        pass
    return send_from_directory(
        MUSIC_DIR,
        filename,
        mimetype='audio/mpeg',
        conditional=True
    )

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-prod')
DATABASE_PATH = os.getenv('DATABASE_PATH', os.path.join(BASE_DIR, 'data', 'music.db'))
MUSIC_DIR = os.getenv('MUSIC_DIR', os.path.join(os.path.dirname(BASE_DIR), 'music'))
STORAGE_TYPE = os.getenv('STORAGE_TYPE', 'local')  # 'local' or 'oss'

# JWT token expiration (seconds)
JWT_EXPIRATION = 86400 * 7  # 7 days

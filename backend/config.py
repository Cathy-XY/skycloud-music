import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 加载 .env 文件（如果存在）
_env_file = os.path.join(BASE_DIR, '.env')
if os.path.exists(_env_file):
    with open(_env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip())

SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-prod')
DATABASE_PATH = os.getenv('DATABASE_PATH', os.path.join(BASE_DIR, 'data', 'music.db'))
MUSIC_DIR = os.getenv('MUSIC_DIR', os.path.join(os.path.dirname(BASE_DIR), 'music'))
STORAGE_TYPE = os.getenv('STORAGE_TYPE', 'local')  # 'local', 'oss', 'bos'

# 对象存储通用配置（适用于 OSS / BOS）
OSS_AK = os.getenv('OSS_AK', '')
OSS_SK = os.getenv('OSS_SK', '')
OSS_ENDPOINT = os.getenv('OSS_ENDPOINT', '')
OSS_BUCKET = os.getenv('OSS_BUCKET', '')

# 百度云 BOS 配置（兼容旧配置，优先读 OSS_* 通用配置）
BOS_AK = os.getenv('BOS_AK', '') or OSS_AK
BOS_SK = os.getenv('BOS_SK', '') or OSS_SK
BOS_ENDPOINT = os.getenv('BOS_ENDPOINT', 'http://bj.bcebos.com') if not OSS_ENDPOINT else OSS_ENDPOINT
BOS_BUCKET = os.getenv('BOS_BUCKET', '') or OSS_BUCKET

# JWT token expiration (seconds)
JWT_EXPIRATION = 86400 * 7  # 7 days

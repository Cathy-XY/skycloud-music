import os
from flask import send_from_directory, redirect
from config import MUSIC_DIR, STORAGE_TYPE, OSS_AK, OSS_SK, OSS_ENDPOINT, OSS_BUCKET, \
    BOS_AK, BOS_SK, BOS_ENDPOINT, BOS_BUCKET

_oss_bucket = None
_bos_client = None


# ========== 阿里云 OSS ==========

def _get_oss_bucket():
    global _oss_bucket
    if _oss_bucket is None:
        import oss2
        auth = oss2.Auth(OSS_AK, OSS_SK)
        _oss_bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET)
    return _oss_bucket


# ========== 百度云 BOS ==========

def _get_bos_client():
    global _bos_client
    if _bos_client is None:
        from baidubce.bce_client_configuration import BceClientConfiguration
        from baidubce.auth.bce_credentials import BceCredentials
        from baidubce.services.bos.bos_client import BosClient
        config = BceClientConfiguration(
            credentials=BceCredentials(BOS_AK, BOS_SK),
            endpoint=BOS_ENDPOINT,
        )
        _bos_client = BosClient(config)
    return _bos_client


# ========== 统一接口 ==========

def get_signed_url(filename):
    """获取云存储签名 URL（字符串），本地模式返回 None"""
    if STORAGE_TYPE == 'oss':
        bucket = _get_oss_bucket()
        return bucket.sign_url('GET', filename, 3600)
    elif STORAGE_TYPE == 'bos':
        client = _get_bos_client()
        url = client.generate_pre_signed_url(
            BOS_BUCKET, filename, expiration_in_seconds=3600,
        )
        if isinstance(url, bytes):
            url = url.decode('utf-8')
        return url
    return None


def serve_audio(filename):
    """返回音频文件：本地直接发送，云存储则 302 重定向到签名 URL"""
    url = get_signed_url(filename)
    if url:
        return redirect(url)
    return send_from_directory(
        MUSIC_DIR, filename, mimetype='audio/mpeg', conditional=True,
    )


def list_cloud_songs():
    """列出云存储 bucket 中所有 mp3 文件名"""
    if STORAGE_TYPE == 'oss':
        return _list_oss_songs()
    elif STORAGE_TYPE == 'bos':
        return _list_bos_songs()
    return []


def download_from_cloud(filename, local_path):
    """从云存储下载文件到本地（用于提取歌曲元数据）"""
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    if STORAGE_TYPE == 'oss':
        bucket = _get_oss_bucket()
        bucket.get_object_to_file(filename, local_path)
    elif STORAGE_TYPE == 'bos':
        client = _get_bos_client()
        client.get_object_to_file(BOS_BUCKET, filename, local_path)


def _list_oss_songs():
    bucket = _get_oss_bucket()
    result = []
    marker = ''
    while True:
        resp = bucket.list_objects(prefix='', marker=marker, max_keys=1000)
        for obj in resp.object_list:
            if obj.key.lower().endswith('.mp3'):
                result.append(obj.key)
        if not resp.is_truncated:
            break
        marker = resp.next_marker
    return result


def _list_bos_songs():
    client = _get_bos_client()
    result = []
    marker = None
    while True:
        response = client.list_objects(BOS_BUCKET, prefix='', marker=marker, max_keys=1000)
        for obj in response.contents:
            if obj.key.lower().endswith('.mp3'):
                result.append(obj.key)
        if not response.is_truncated:
            break
        marker = response.next_marker
    return result

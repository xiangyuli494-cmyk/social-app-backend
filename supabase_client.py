"""
Supabase REST API 客户端 (PostgREST + Storage)
使用 service_role key 绕过 RLS，对数据库有完全访问权限
"""
import os
import requests
from supabase import create_client

SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://ykwmyebnewzhbrjedtxd.supabase.co')
SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', '')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def db():
    """获取 Supabase 客户端，作为"数据库连接"对象"""
    return supabase


def upload_file(bucket, path, file_bytes, content_type='image/jpeg'):
    """上传文件到 Supabase Storage，返回公开 URL"""
    headers = {
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'apikey': SUPABASE_KEY,
    }
    url = f'{SUPABASE_URL}/storage/v1/object/{bucket}/{path}'
    r = requests.post(url, headers=headers, data=file_bytes,
                      params={'content-type': content_type})
    if r.status_code in (200, 201):
        return f'{SUPABASE_URL}/storage/v1/object/public/{bucket}/{path}'
    else:
        raise Exception(f'Storage upload failed: {r.status_code} {r.text}')


def delete_file(bucket, path):
    """从 Supabase Storage 删除文件"""
    headers = {
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'apikey': SUPABASE_KEY,
    }
    url = f'{SUPABASE_URL}/storage/v1/object/{bucket}/{path}'
    requests.delete(url, headers=headers)

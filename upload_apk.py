"""Upload APK to Supabase Storage"""
import uuid, os, sys, requests

SUPABASE_URL = 'https://ykwmyebnewzhbrjedtxd.supabase.co'
SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', '')

if not SUPABASE_KEY:
    print('请先设置环境变量: set SUPABASE_SERVICE_KEY=你的key')
    sys.exit(1)

apk_path = sys.argv[1] if len(sys.argv) > 1 else '../android/app/build/outputs/apk/debug/app-debug.apk'
with open(apk_path, 'rb') as f:
    data = f.read()

filename = 'app-debug-latest.apk'
headers = {
    'Authorization': f'Bearer {SUPABASE_KEY}',
    'apikey': SUPABASE_KEY,
}
url = f'{SUPABASE_URL}/storage/v1/object/posts/app/{filename}'
r = requests.post(url, headers=headers, data=data,
                  params={'content-type': 'application/vnd.android.package-archive'})

if r.status_code in (200, 201):
    public_url = f'{SUPABASE_URL}/storage/v1/object/public/posts/app/{filename}'
    print(f'上传成功: {public_url}')
    print(f'请将 app.py 中下载链接更新为: {public_url}')
else:
    print(f'上传失败: {r.status_code} {r.text}')

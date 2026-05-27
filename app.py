from flask import Flask
from flask_cors import CORS
from models import init_db
from routes.auth_routes import auth_bp
from routes.user_routes import user_bp
from routes.post_routes import post_bp
from routes.friend_routes import friend_bp
from routes.chat_routes import chat_bp

app = Flask(__name__)
CORS(app)


@app.route('/download')
def download_page():
    return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>香芋 下载</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh; display: flex; align-items: center; justify-content: center;
  }
  .card {
    background: #fff; border-radius: 16px; padding: 40px 30px; text-align: center;
    box-shadow: 0 20px 60px rgba(0,0,0,.3); max-width: 360px; width: 90%;
  }
  .icon {
    width: 72px; height: 72px;
    background: linear-gradient(135deg, #667eea, #764ba2);
    border-radius: 18px; margin: 0 auto 20px;
    display: flex; align-items: center; justify-content: center;
    font-size: 36px; color: #fff;
  }
  h1 { font-size: 22px; margin-bottom: 8px; color: #333; }
  .version { color: #999; font-size: 13px; margin-bottom: 28px; }
  .btn {
    display: block;
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: #fff; text-decoration: none; padding: 14px;
    border-radius: 10px; font-size: 17px; font-weight: 600; margin-bottom: 12px;
  }
  .btn:active { transform: scale(0.97); }
  .tip { color: #aaa; font-size: 12px; margin-top: 20px; }
</style>
</head>
<body>
<div class="card">
  <div class="icon">??</div>
  <h1>香芋之家</h1>
  <p class="version">v2.0 · Android</p>
  <a class="btn" href="https://ykwmyebnewzhbrjedtxd.supabase.co/storage/v1/object/public/posts/app/app-debug-latest.apk">下载安装</a>
  <p class="tip">下载后点击安装包即可安装<br>如提示"未知来源"，请在设置中允许</p>
</div>
</body>
</html>'''


app.register_blueprint(auth_bp)
app.register_blueprint(user_bp)
app.register_blueprint(post_bp)
app.register_blueprint(friend_bp)
app.register_blueprint(chat_bp)

if __name__ == '__main__':
    init_db()
    print('Connected to Supabase PostgreSQL')
    print('Server starting on http://0.0.0.0:5000')
    app.run(host='0.0.0.0', port=5000, debug=True)

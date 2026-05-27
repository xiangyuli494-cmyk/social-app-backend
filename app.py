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

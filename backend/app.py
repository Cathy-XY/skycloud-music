import os
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from database import init_db
from models import scan_songs
from routes.auth import auth_bp
from routes.songs import songs_bp
from routes.comments import comments_bp
from routes.lyrics import lyrics_bp
from routes.chat import chat_bp, init_socketio
from routes.listen_together import listen_bp, init_listen_socketio

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading',
                    ping_timeout=120, ping_interval=25)

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(songs_bp, url_prefix='/api/songs')
app.register_blueprint(comments_bp, url_prefix='/api')
app.register_blueprint(lyrics_bp, url_prefix='/api')
app.register_blueprint(chat_bp, url_prefix='/api')
app.register_blueprint(listen_bp, url_prefix='/api')

# Initialize SocketIO events
init_socketio(socketio)
init_listen_socketio(socketio)

# Initialize database and scan songs on startup
with app.app_context():
    init_db()
    scan_songs()
    print("Database initialized and songs scanned.")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=True, allow_unsafe_werkzeug=True)

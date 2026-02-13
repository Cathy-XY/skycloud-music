# Skycloud Music - 擎天云音乐

一个 Web 音乐播放器，支持多用户听歌、评论、歌词编辑和实时聊天。

## 技术栈

- **后端**: Python + Flask + SQLite + Flask-SocketIO
- **前端**: Vue 3 + Vite + Pinia

## 快速启动

### 前置条件
- Python 3.9+
- Node.js 18+

### 一键启动
```bash
./start.sh
```

### 手动启动

```bash
# 后端
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py

# 前端 (另一个终端)
cd frontend
npm install
npm run dev
```

打开浏览器访问 `http://localhost:5173`

## 添加音乐

将 MP3 文件放入 `music/` 目录，重启后端即自动识别。

## 功能

- 音乐播放（播放/暂停/切歌/进度/音量）
- 用户注册登录
- 每首歌评论
- 歌词查看与编辑
- 实时聊天室

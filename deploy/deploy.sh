#!/bin/bash
# deploy.sh - 在云服务器（ECS/BCC 等）上部署 demo-music（双版本）
# 用法: 将代码上传到服务器后，在项目根目录执行 bash deploy/deploy.sh
#
# 部署后运行两个后端进程：
#   - 端口 5000（SQLite 单机版）→ Nginx 80
#   - 端口 5001（RDS 拓展版）  → Nginx 8080

set -e

APP_DIR="/opt/demo-music"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Demo Music 云部署（双版本）==="

# 1. 系统依赖
echo "[1/7] 安装系统依赖..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-venv python3-pip nginx nodejs npm

# 2. 复制项目到部署目录
echo "[2/7] 部署项目文件..."
sudo mkdir -p $APP_DIR
sudo cp -r "$PROJECT_DIR"/* $APP_DIR/
sudo chown -R $USER:$USER $APP_DIR

# 3. 后端环境
echo "[3/7] 配置后端..."
cd $APP_DIR/backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt -q

# 检查 .env 是否存在（RDS 版需要）
if [ ! -f ".env" ]; then
    echo ""
    echo "  ⚠ 未找到 backend/.env 配置文件！"
    echo "  RDS 版需要此文件，请创建并填入实际值："
    echo "    vim $APP_DIR/backend/.env"
    echo "  示例内容："
    echo "    DB_TYPE=mysql"
    echo "    MYSQL_HOST=your-rds-host"
    echo "    MYSQL_PORT=3306"
    echo "    MYSQL_USER=music_user"
    echo "    MYSQL_PASSWORD=your-password"
    echo "    MYSQL_DB=demo_music"
    echo ""
fi

# 4. 前端构建
echo "[4/7] 构建前端..."
cd $APP_DIR/frontend
npm install --silent
npm run build

# 5. Nginx 配置（双版本：80→SQLite, 8080→RDS）
echo "[5/7] 配置 Nginx..."
sudo cp $APP_DIR/deploy/nginx.conf /etc/nginx/sites-available/demo-music
sudo ln -sf /etc/nginx/sites-available/demo-music /etc/nginx/sites-enabled/demo-music
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

# 6. SQLite 单机版（端口 5000）
echo "[6/7] 配置 SQLite 单机版服务..."
sudo tee /etc/systemd/system/demo-music-sqlite.service > /dev/null <<EOF
[Unit]
Description=Demo Music Backend (SQLite)
After=network.target

[Service]
User=$USER
WorkingDirectory=$APP_DIR/backend
Environment=PATH=$APP_DIR/backend/venv/bin:/usr/bin
Environment=DB_TYPE=sqlite
ExecStart=$APP_DIR/backend/venv/bin/gunicorn -w 1 -b 0.0.0.0:5000 --worker-class eventlet app:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# 7. RDS 拓展版（端口 5001，读 .env 配置）
echo "[7/7] 配置 RDS 拓展版服务..."
sudo tee /etc/systemd/system/demo-music-rds.service > /dev/null <<EOF
[Unit]
Description=Demo Music Backend (RDS)
After=network.target

[Service]
User=$USER
WorkingDirectory=$APP_DIR/backend
Environment=PATH=$APP_DIR/backend/venv/bin:/usr/bin
ExecStart=$APP_DIR/backend/venv/bin/gunicorn -w 1 -b 0.0.0.0:5001 --worker-class eventlet app:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable demo-music-sqlite demo-music-rds
sudo systemctl restart demo-music-sqlite demo-music-rds

# 清理旧的单进程 service（如果存在）
sudo systemctl disable demo-music 2>/dev/null || true
sudo systemctl stop demo-music 2>/dev/null || true

echo ""
echo "=== 部署完成 ==="
PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || echo '你的公网IP')
echo "SQLite 单机版: http://$PUBLIC_IP        (Nginx 80  → 后端 5000)"
echo "RDS 拓展版:    http://$PUBLIC_IP:8080   (Nginx 8080 → 后端 5001)"
echo ""
echo "常用命令："
echo "  查看 SQLite 版日志: sudo journalctl -u demo-music-sqlite -f"
echo "  查看 RDS 版日志:    sudo journalctl -u demo-music-rds -f"
echo "  重启 SQLite 版:     sudo systemctl restart demo-music-sqlite"
echo "  重启 RDS 版:        sudo systemctl restart demo-music-rds"
echo "  重启 Nginx:         sudo systemctl restart nginx"

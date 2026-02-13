#!/bin/bash
# deploy.sh - 在云服务器（ECS/BCC 等）上部署 demo-music
# 用法: 将代码上传到服务器后，在项目根目录执行 bash deploy/deploy.sh

set -e

APP_DIR="/opt/demo-music"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Demo Music 云部署 ==="

# 1. 系统依赖
echo "[1/6] 安装系统依赖..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-venv python3-pip nginx nodejs npm

# 2. 复制项目到部署目录
echo "[2/6] 部署项目文件..."
sudo mkdir -p $APP_DIR
sudo cp -r "$PROJECT_DIR"/* $APP_DIR/
sudo chown -R $USER:$USER $APP_DIR

# 3. 后端环境
echo "[3/6] 配置后端..."
cd $APP_DIR/backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt -q

# 检查 .env 是否存在
if [ ! -f ".env" ]; then
    echo ""
    echo "  ⚠ 未找到 backend/.env 配置文件！"
    echo "  请复制模板并填入实际值："
    echo "    cp $APP_DIR/backend/.env.production $APP_DIR/backend/.env"
    echo "    vim $APP_DIR/backend/.env"
    echo ""
fi

# 4. 前端构建
echo "[4/6] 构建前端..."
cd $APP_DIR/frontend
npm install --silent
npm run build

# 5. Nginx 配置
echo "[5/6] 配置 Nginx..."
sudo cp $APP_DIR/deploy/nginx.conf /etc/nginx/sites-available/demo-music
sudo ln -sf /etc/nginx/sites-available/demo-music /etc/nginx/sites-enabled/demo-music
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

# 6. 启动后端（用 systemd 管理）
echo "[6/6] 配置后端服务..."
sudo tee /etc/systemd/system/demo-music.service > /dev/null <<EOF
[Unit]
Description=Demo Music Backend
After=network.target

[Service]
User=$USER
WorkingDirectory=$APP_DIR/backend
Environment=PATH=$APP_DIR/backend/venv/bin:/usr/bin
ExecStart=$APP_DIR/backend/venv/bin/python app.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable demo-music
sudo systemctl restart demo-music

echo ""
echo "=== 部署完成 ==="
echo "访问: http://$(curl -s ifconfig.me 2>/dev/null || echo '你的公网IP')"
echo ""
echo "常用命令："
echo "  查看后端日志: sudo journalctl -u demo-music -f"
echo "  重启后端:     sudo systemctl restart demo-music"
echo "  重启 Nginx:   sudo systemctl restart nginx"

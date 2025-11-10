#!/bin/bash
# ============================================================
# 🩺 VTSurgical - Instalador Automático do Sistema Cirúrgico
# ============================================================

BASE_DIR="$(dirname "$0")"
cd "$BASE_DIR"
USER_NAME="vtsurgical"
SERVICE_FILE="/etc/systemd/system/vtsurgical.service"
PYTHON_ENV="${BASE_DIR}/.venv"
LOG_DIR="${BASE_DIR}/logs"
LOG_FILE="${LOG_DIR}/vtsurgical.log"

echo "============================================================"
echo "🩺 Instalador Automático - VTSurgical"
echo "============================================================"

# 1️⃣ Dependências do sistema
echo "📦 Instalando dependências do sistema..."
sudo apt update -y
sudo apt install -y python3-venv python3-pip python3-opencv net-tools ffmpeg

# 2️⃣ Ambiente virtual
if [ ! -d "$PYTHON_ENV" ]; then
    echo "⚙️ Criando ambiente virtual..."
    python3 -m venv "$PYTHON_ENV"
else
    echo "✅ Ambiente virtual já existe."
fi

# 3️⃣ Ativar ambiente e instalar libs
echo "📚 Instalando bibliotecas Python..."
source "${PYTHON_ENV}/bin/activate"
pip install --upgrade pip
pip install flask tensorflow opencv-python netifaces numpy

# 4️⃣ Criar diretório de logs
mkdir -p "$LOG_DIR"
touch "$LOG_FILE"
echo "✅ Pasta de logs criada em $LOG_DIR"

# 5️⃣ Criar o serviço systemd
echo "⚙️ Criando serviço systemd em: $SERVICE_FILE"
sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=🩺 VTSurgical - Sistema de Transmissão Cirúrgica
After=network.target
StartLimitIntervalSec=60
StartLimitBurst=3

[Service]
Type=simple
User=${USER_NAME}
WorkingDirectory=${BASE_DIR}
ExecStart=${BASE_DIR}/stream.sh
Restart=always
RestartSec=10
Environment="PYTHONUNBUFFERED=1"
StandardOutput=append:${LOG_FILE}
StandardError=append:${LOG_FILE}
ProtectSystem=full
ProtectHome=no
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# 6️⃣ Recarregar systemd e iniciar
echo "🔁 Recarregando e iniciando o serviço..."
sudo systemctl daemon-reload
sudo systemctl enable vtsurgical.service
sudo systemctl restart vtsurgical.service

echo "============================================================"
echo "✅ Instalação concluída!"
echo "------------------------------------------------------------"
echo "📡 Acesse: http://127.0.0.1:5001"
echo "📜 Logs: $LOG_FILE"
echo "🔍 Status: sudo systemctl status vtsurgical"
echo "============================================================"

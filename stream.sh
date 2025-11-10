#!/bin/bash
# ==============================================================
# 🩺 VTSurgical - Sistema de Transmissão Cirúrgica
# Inicia o servidor Flask com reinicialização automática de câmeras
# ==============================================================

# Caminho base do projeto
cd "$(dirname "$0")"

# Caminho do Python virtualenv
PYTHON_BIN="./.venv/bin/python"

# Define a porta (padrão 5000, ou argumento passado)
PORT_ARG=${1:-5000}

# Diretório e arquivo de log
LOG_DIR="./logs"
LOG_FILE="${LOG_DIR}/vtsurgical.log"

mkdir -p "$LOG_DIR"

echo "=============================================================="
echo "🩺 VTSurgical - Sistema de Transmissão Cirúrgica"
echo "--------------------------------------------------------------"
echo "🕒 Início: $(date)"
echo "🌐 Porta: ${PORT_ARG}"
echo "📄 Log: ${LOG_FILE}"
echo "=============================================================="
echo ""

# ==============================================================
# 1️⃣ Função: Reset de Câmeras Automático
# ==============================================================

reset_cameras() {
    echo "🔍 Verificando e liberando câmeras em uso..."
    # Mata qualquer processo que ainda esteja usando /dev/video*
    sudo kill -9 $(sudo fuser /dev/video* 2>/dev/null) 2>/dev/null

    echo "♻️ Recarregando módulo uvcvideo..."
    sudo rmmod -f uvcvideo 2>/dev/null
    sudo modprobe uvcvideo 2>/dev/null

    echo "✅ Câmeras reiniciadas com sucesso!"
    echo ""
    v4l2-ctl --list-devices || echo "⚠️ Nenhum dispositivo detectado após reinício."
}

# Chama o reset automático antes de iniciar o servidor
reset_cameras

# ==============================================================
# 2️⃣ Verifica se o Python existe
# ==============================================================

if [ ! -f "$PYTHON_BIN" ]; then
    echo "❌ ERRO: Python virtualenv não encontrado em .venv/bin/python"
    echo "🔧 Solução: Crie o ambiente com:"
    echo "    python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# ==============================================================
# 3️⃣ Inicia o servidor Flask e monitora falhas
# ==============================================================

RESTART_DELAY=5

while true; do
    echo "🚀 Iniciando servidor Flask na porta ${PORT_ARG}..."
    "$PYTHON_BIN" webstream_linux.py "$PORT_ARG" >> "$LOG_FILE" 2>&1
    EXIT_CODE=$?

    if [ $EXIT_CODE -eq 0 ]; then
        echo "✅ Servidor encerrado normalmente."
        break
    else
        echo "⚠️ Servidor caiu com código ${EXIT_CODE}. Reiniciando em ${RESTART_DELAY}s..."
        sleep $RESTART_DELAY
        reset_cameras
    fi
done

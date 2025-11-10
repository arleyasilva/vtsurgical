#!/bin/bash
cd "$(dirname "$0")"
PORT=5001

echo "🩺 Verificando processo Flask na porta $PORT..."
PID=$(sudo lsof -t -i :$PORT)

if [ -n "$PID" ]; then
    echo "🔪 Encerrando processo antigo (PID: $PID)..."
    sudo kill -9 $PID
else
    echo "✅ Nenhum processo ativo encontrado."
fi

echo "🚀 Reiniciando servidor Flask..."
source .venv/bin/activate
python3 webstream_linux.py $PORT

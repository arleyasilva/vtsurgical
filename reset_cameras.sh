#!/bin/bash
echo "🩺 Reiniciando módulos de vídeo..."
sudo kill -9 $(sudo fuser /dev/video* 2>/dev/null)
sudo rmmod -f uvcvideo
sudo modprobe uvcvideo
echo "✅ Câmeras reiniciadas com sucesso!"
v4l2-ctl --list-devices

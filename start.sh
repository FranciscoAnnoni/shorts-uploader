#!/bin/bash
cd ~/Proyectos/shorts-uploader

# Matar cualquier proceso que esté usando el puerto 7860
PID=$(lsof -ti :7860)
if [ -n "$PID" ]; then
    kill "$PID" 2>/dev/null
    sleep 1
fi

source venv/bin/activate
python main.py

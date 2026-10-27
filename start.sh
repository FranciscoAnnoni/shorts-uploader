#!/bin/bash
cd ~/Proyectos/shorts-uploader

# Matar cualquier proceso que esté usando el puerto 7860
PID=$(lsof -ti :7860)
if [ -n "$PID" ]; then
    kill "$PID" 2>/dev/null
    sleep 1
fi

source venv/bin/activate
# todo lo que imprime la app queda tambien en logs/AAAA-MM-DD.log, con la hora
# de cada linea para medir cuanto tarda cada paso
mkdir -p logs
python -u main.py 2>&1 \
    | perl -MPOSIX -pe 'BEGIN { $| = 1 } $_ = strftime("%H:%M:%S ", localtime) . $_' \
    | tee -a "logs/$(date +%F).log"

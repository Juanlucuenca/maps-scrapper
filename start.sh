#!/bin/bash
# Iniciar Xvfb
Xvfb :0 -screen 0 1280x800x24 &

# Esperar a que Xvfb inicie
sleep 1

# Iniciar servidor VNC
x11vnc -display :0 -forever -passwd playwright -noxdamage -ncache_cr &

# Iniciar entorno de ventanas
fluxbox &

# Iniciar la aplicación
python main.py 
#!/bin/bash

set -e

APP_DIR="/opt/igsismani"
APP_USER="sistemas"

echo "==> Instalando paquetes básicos..."
###sudo apt update
sudo apt install -y git curl

echo "==> Creando directorios..."
sudo mkdir -p "$APP_DIR"
sudo mkdir -p "$APP_DIR/logs"

echo "==> Configurando permisos..."
sudo chown -R "$APP_USER:$APP_USER" "$APP_DIR"

echo "==> Provisionamiento básico terminado."

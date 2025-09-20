#!/bin/bash
set -euo pipefail

# Defaults
ENV_NAME=""
DO_BUILD=1
SINCE_VAL=""
UNTIL_VAL=""

usage() {
  cat <<EOF
Uso:
  ./run.sh [--env dev|stage|prod|custom] [--since ISO8601] [--until ISO8601] [--no-build]

Ejemplos:
  ./run.sh --env dev
  ./run.sh --env stage --since 2025-09-01T00:00:00Z --until 2025-09-19T23:59:59Z
  ./run.sh --env prod --no-build
EOF
}

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)   ENV_NAME="${2:-}"; shift 2 ;;
    --since) SINCE_VAL="${2:-}"; shift 2 ;;
    --until) UNTIL_VAL="${2:-}"; shift 2 ;;
    --no-build) DO_BUILD=0; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Argumento no reconocido: $1"; usage; exit 1 ;;
  esac
done

# Resolver env file
case "${ENV_NAME}" in
  ""|"custom") ENV_FILE=".env" ;;
  dev)         ENV_FILE=".env.dev" ;;
  stage)       ENV_FILE=".env.stage" ;;
  prod)        ENV_FILE=".env.prod" ;;
  *) echo "Valor de --env inválido: ${ENV_NAME}"; usage; exit 1 ;;
esac

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "⚠️  No existe ${ENV_FILE}. Crea uno o ajusta --env."
  exit 1
fi

# Export UID/GID del host
export HOST_UID="$(id -u)"
export HOST_GID="$(id -g)"

# Overrides opcionales
[[ -n "${SINCE_VAL}" ]] && export SINCE="${SINCE_VAL}"
[[ -n "${UNTIL_VAL}" ]] && export UNTIL="${UNTIL_VAL}"

# Asegurar carpeta de salida
mkdir -p data || true

echo "============================"
echo " 🧭  ENV_FILE = ${ENV_FILE}"
echo " 👤  HOST_UID:GID = ${HOST_UID}:${HOST_GID}"
[[ -n "${SINCE_VAL}" ]] && echo " ⏱  SINCE    = ${SINCE_VAL}"
[[ -n "${UNTIL_VAL}" ]] && echo " ⏱  UNTIL    = ${UNTIL_VAL}"
echo "============================"

# Build (opcional)
if [[ "${DO_BUILD}" -eq 1 ]]; then
  echo "🛠  Construyendo imagen..."
  docker compose build
else
  echo "⏩  Saltando build (--no-build)"
fi

# Run con el env-file correcto
echo "🚀 Ejecutando contenedor (runner)..."
docker compose --env-file "${ENV_FILE}" run --rm runner

echo
echo "============================"
echo " ✅ Proceso terminado"
echo " Archivos generados en ./data"
echo "============================"
ls -lah ./data || true

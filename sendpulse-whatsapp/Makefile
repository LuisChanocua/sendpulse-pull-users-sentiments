# ===== Config =====
COMPOSE := docker compose
IMAGE := sendpulse-whatsapp:latest
SERVICE_RUN := runner
SERVICE_SCHED := scheduler

# ===== Helpers =====
.PHONY: help
help:
	@echo "Targets disponibles:"
	@echo "  make build           -> Construye la imagen Docker"
	@echo "  make run             -> Ejecuta una corrida one-shot (runner)"
	@echo "  make logs            -> Muestra logs del último run (si aplica)"
	@echo "  make clean           -> Elimina contenedores detenidos y caché dangling"
	@echo "  make bash            -> Abre una shell dentro de un contenedor temporal"
	@echo "  make schedule-up     -> (Futuro) Levanta el scheduler con crontab"
	@echo "  make schedule-down   -> (Futuro) Detiene/elimina el scheduler"
	@echo "  make data-tree       -> Lista archivos generados en ./data"

# ===== Build =====
.PHONY: build
build:
	$(COMPOSE) build

# ===== One-shot run =====
.PHONY: run
run:
	$(COMPOSE) run --rm $(SERVICE_RUN)

# (opcional) logs del servicio si lo lanzaste con 'up'
.PHONY: logs
logs:
	$(COMPOSE) logs -f $(SERVICE_RUN) || true

# ===== Dev utils =====
.PHONY: bash
bash:
	$(COMPOSE) run --rm $(SERVICE_RUN) /bin/bash

.PHONY: clean
clean:
	@echo "Limpiando contenedores detenidos e imágenes dangling..."
	-docker container prune -f
	-docker image prune -f
	@echo "Listo."

.PHONY: data-tree
data-tree:
	@echo "Contenido de ./data:"
	@mkdir -p data && ls -lah data || true

# ===== Scheduler (preparado, desactivado por defecto) =====
.PHONY: schedule-up
schedule-up:
	@echo "⚠️  Asegúrate de DESCOMENTAR el servicio 'scheduler' en docker-compose.yml"
	$(COMPOSE) up -d $(SERVICE_SCHED)

.PHONY: schedule-down
schedule-down:
	$(COMPOSE) rm -sf $(SERVICE_SCHED)

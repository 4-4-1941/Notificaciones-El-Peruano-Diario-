# Notificaciones El Peruano - Monitor MINSA

Monitoreo automático de Resoluciones Ministeriales (RM) y Normas Técnicas de Salud (NTS) del **Ministerio de Salud (MINSA)** publicadas en el Diario Oficial El Peruano.

## Objetivo

Detectar nuevas normas del MINSA publicadas en [busquedas.elperuano.pe](https://busquedas.elperuano.pe/) y notificarlas automáticamente (Telegram, Discord, Email o Webhook).

## Características

- Consulta periódica a El Peruano
- Filtro específico para MINSA / NTS / RM
- Almacenamiento de historial (JSON + SQLite)
- Notificaciones configurables
- Ejecución automática con GitHub Actions

## Estructura del proyecto

## Instalación

```bash
git clone https://github.com/4-4-1941/Notificaciones-El-Peruano-Diario-.git
cd Notificaciones-El-Peruano-Diario-
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
cp config.example.yaml config.yaml
cp .env.example .env

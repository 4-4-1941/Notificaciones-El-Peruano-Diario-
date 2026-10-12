"""
main.py
Punto de entrada principal del monitor de normas MINSA en El Peruano.
"""

import logging
import sys
from pathlib import Path

# Asegurar que el paquete src sea importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.scraper import ElPeruanoScraper
from src.filter_minsa import filtrar_minsa
from src.storage import Storage
from src.notifiers.telegram import TelegramNotifier
from src.notifiers.discord import DiscordNotifier
from src.notifiers.email_notifier import EmailNotifier
from src.notifiers.webhook import WebhookNotifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def cargar_config():
    """Carga configuración básica desde variables de entorno o valores por defecto."""
    import os
    from dotenv import load_dotenv

    load_dotenv()

    return {
        "telegram_token": os.getenv("TELEGRAM_BOT_TOKEN"),
        "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID"),
        "discord_webhook": os.getenv("DISCORD_WEBHOOK_URL"),
        "email_enabled": os.getenv("EMAIL_ENABLED", "false").lower() == "true",
        "webhook_url": os.getenv("WEBHOOK_URL"),
        "palabras_clave": ["MINSA", "NTS", "Resolución Ministerial", "Norma Técnica de Salud"],
    }


def crear_notificadores(config: dict):
    """Instancia los notificadores que estén configurados."""
    notificadores = []

    if config.get("telegram_token") and config.get("telegram_chat_id"):
        notificadores.append(
            TelegramNotifier(
                token=config["telegram_token"],
                chat_id=config["telegram_chat_id"],
            )
        )

    if config.get("discord_webhook"):
        notificadores.append(DiscordNotifier(webhook_url=config["discord_webhook"]))

    if config.get("email_enabled"):
        notificadores.append(EmailNotifier())

    if config.get("webhook_url"):
        notificadores.append(WebhookNotifier(url=config["webhook_url"]))

    return notificadores


def ejecutar():
    """Flujo principal: scrapear → filtrar → guardar → notificar."""
    logger.info("Iniciando monitor MINSA - El Peruano")

    config = cargar_config()
    scraper = ElPeruanoScraper()
    storage = Storage()

    # 1. Buscar dispositivos del día
    dispositivos = scraper.buscar_por_fecha(
        palabras_clave=config["palabras_clave"]
    )

    if not dispositivos:
        logger.info("No se encontraron dispositivos hoy")
        return

    # 2. Filtrar solo MINSA
    normas_minsa = filtrar_minsa(dispositivos)

    if not normas_minsa:
        logger.info("No hay normas del MINSA en los resultados de hoy")
        return

    # 3. Guardar solo las nuevas
    nuevas = storage.guardar(normas_minsa)

    if not nuevas:
        logger.info("No hay normas nuevas para notificar")
        return

    # 4. Notificar
    notificadores = crear_notificadores(config)

    if not notificadores:
        logger.warning("No hay notificadores configurados. Solo se guardó en storage.")
        return

    for norma in nuevas:
        mensaje = (
            f"📢 *Nueva norma MINSA*\n\n"
            f"*Título:* {norma.get('titulo', 'Sin título')}\n"
            f"*OP:* {norma.get('op')}\n"
            f"*RM:* {norma.get('numero_rm', 'N/A')}\n"
            f"*NTS:* {norma.get('numero_nts', 'N/A')}\n"
            f"*Enlace:* {norma.get('url')}"
        )

        for notifier in notificadores:
            try:
                notifier.enviar(mensaje, norma)
                storage.marcar_notificado(norma["op"])
            except Exception as e:
                logger.error(f"Error al notificar {norma.get('op')}: {e}")

    logger.info(f"Proceso finalizado. {len(nuevas)} normas nuevas procesadas.")


if __name__ == "__main__":
    ejecutar()

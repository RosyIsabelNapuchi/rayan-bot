"""Conector de Telegram (opcional). Requiere TELEGRAM_TOKEN en .env.   Ejecutar: python -m rayan.telegram_bot

El usuario de Telegram (@usuario) debe estar activo en data/usuarios.csv.
"""
from __future__ import annotations

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

from .bot import Rayan
from .config import settings

BOT = Rayan()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(BOT.responder("ayuda", usuario=update.effective_user.username).texto)


async def mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    respuesta = BOT.responder(update.message.text or "", usuario=update.effective_user.username)
    await update.message.reply_text(respuesta.texto)


def main() -> None:
    if not settings.telegram_token:
        raise SystemExit("Falta TELEGRAM_TOKEN en el archivo .env")
    app = ApplicationBuilder().token(settings.telegram_token).build()
    app.add_handler(CommandHandler(["start", "ayuda"], start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensaje))
    app.run_polling()


if __name__ == "__main__":
    main()

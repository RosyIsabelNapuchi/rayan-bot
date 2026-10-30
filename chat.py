"""Chat en la terminal con Rayan (no necesita Telegram ni claves).   Uso: python chat.py"""
from rayan.bot import Rayan

if __name__ == "__main__":
    bot = Rayan(exigir_usuario=False)
    print("Rayan Bot · datos sintéticos · escribe 'ayuda' para ejemplos o 'salir' para terminar\n")
    while True:
        try:
            texto = input("Tú: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if texto.lower() in {"salir", "exit", "quit"}:
            break
        print("\nRayan:", bot.responder(texto).texto, "\n")

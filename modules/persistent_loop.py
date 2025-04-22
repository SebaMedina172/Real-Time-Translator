import asyncio
import threading

_loop = None

def init_event_loop(loop):
    """Inicializa el event loop persistente con el loop del hilo principal."""
    global _loop
    _loop = loop

def get_event_loop():
    """Devuelve el event loop que ya fue inicializado (idealmente el del hilo principal)."""
    return _loop
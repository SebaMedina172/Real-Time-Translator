import asyncio
import threading

_loop = None

def start_loop(loop):
    """Ejecuta el event loop en un hilo separado."""
    asyncio.set_event_loop(loop)
    loop.run_forever()

def get_event_loop():
    """Devuelve un event loop persistente. Si no existe, lo crea y lo inicia en un hilo daemon."""
    global _loop
    if _loop is None:
        _loop = asyncio.new_event_loop()
        t = threading.Thread(target=start_loop, args=(_loop,), daemon=True)
        t.start()
    return _loop
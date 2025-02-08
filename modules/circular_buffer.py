from collections import deque


class CircularBuffer:
    def __init__(self, size):
        # Se crea un deque con tamaño máximo (FIFO)
        self.buffer = deque(maxlen=size)

    def append(self, item):
        self.buffer.append(item)

    def get_data(self):
        # Se retorna una lista con los datos actuales
        return list(self.buffer)

    def clear(self):
        self.buffer.clear()
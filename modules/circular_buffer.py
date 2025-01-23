class CircularBuffer:
    def __init__(self, size):
        self.size = size
        self.buffer = [None] * size
        self.head = 0
        self.tail = 0
        self.full = False

    def append(self, item):
        self.buffer[self.head] = item
        if self.full:
            self.tail = (self.tail + 1) % self.size  # Mueve el tail si está lleno
        self.head = (self.head + 1) % self.size
        self.full = self.head == self.tail  # Marca como lleno si head alcanza a tail

    def get_data(self):
        if self.full:
            return self.buffer[self.tail:] + self.buffer[:self.head]
        return self.buffer[self.tail:self.head]

    def clear(self):
        self.head = 0
        self.tail = 0
        self.full = False

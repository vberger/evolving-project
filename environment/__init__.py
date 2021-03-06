import math

from .pheromone import Pheromone

from conf import OBJECTS_DECAY

def distance(x, y, a, b):
    return math.sqrt((x-a)**2 + (y-b)**2)

class Food:
    def __init__(self, x, y, amount):
        self.x = x
        self.y = y
        self.amount = amount
        self.tick = 1.0
        self.kind = 0

    def update(self, animals, pheromones, timedelta):
        for a in animals:
            if distance(a.x, a.y, self.x, self.y) < 8:
                consume = min(self.amount, 100 - a.energy)
                self.amount -= consume
                a.energy += consume
                if self.amount <= 0:
                    break
        self.tick -= timedelta
        self.amount -= timedelta * OBJECTS_DECAY
        if self.amount > 0 and self.tick <= 0:
            self.tick = 1.0
            pheromones.append(Pheromone(self.kind, self.x, self.y, self.amount, 10))

class Poison:
    def __init__(self, x, y, amount):
        self.x = x
        self.y = y
        self.amount = amount
        self.tick = 1.0
        self.kind = 1

    def update(self, animals, pheromones, timedelta):
        for a in animals:
            if distance(a.x, a.y, self.x, self.y) < 8:
                consume = min(self.amount, a.energy)
                self.amount -= consume
                a.energy -= consume
                if self.amount <= 0:
                    break
        self.tick -= timedelta
        self.amount -= timedelta * OBJECTS_DECAY
        if self.amount > 0 and self.tick <= 0:
            self.tick = 1.0
            pheromones.append(Pheromone(self.kind, self.x, self.y, self.amount, 10))

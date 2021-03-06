import math, random
from multiprocessing import Pool, Manager
from animal import Animal
from environment import Food, Poison
from environment.predator import Predator

from neural.breeding import breed

from conf import PHEROMONES, ANIMALS_BASE_SPEED, ANIMALS_BASE_ANGULAR_SPEED
from conf import FOOD_PERIOD, BREEDING_PERIOD, BREEDING_FITNESS, POISON_PERIOD

def update_animal(animal, pheromones, timestep, width, height):
    # compute food smells
    val = [0.0 for _ in range(PHEROMONES)]
    gradx = [0.0 for _ in range(PHEROMONES)]
    grady = [0.0 for _ in range(PHEROMONES)]
    for f in pheromones:
        x = animal.x
        y = animal.y
        # take the warping into account
        if x - f.x > width / 2:
            x -= width
        elif x - f.x < -width / 2:
            x += width
        if y - f.y > height / 2:
            y -= height
        elif y - f.y < -height / 2:
            y += height
        (fval, fgx, fgy) = f.values_at(x, y)
        val[f.sid] += fval
        gradx[f.sid] += fgx
        grady[f.sid] += fgy
    angle_val = [
        math.tanh(math.tan((math.atan2(gy, gx) - animal.theta)/2)) for (gy, gx) in zip(grady, gradx)
    ]
    # update animals
    new_pheromones = animal.update(zip(val, angle_val), timestep, ANIMALS_BASE_SPEED, ANIMALS_BASE_ANGULAR_SPEED)
    if animal.x > width: animal.x -= width
    if animal.x < 0: animal.x += width
    if animal.y > height: animal.y -= height
    if animal.y < 0: animal.y += height
    return (animal, new_pheromones)

class Simulator:
    def __init__(self, space_width, space_height, animal_count, pred_count, genomes):
        self.pool = Pool()
        self.manager = Manager()

        self.width = space_width
        self.height = space_height
        self.genomes = genomes
        self.predators = [
            Predator(
                random.randrange(0, self.width, 1),
                random.randrange(0, self.height, 1)
            ) for _ in range(pred_count)
        ]
        self.animals = [ Animal(random.choice(genomes), PHEROMONES) for _ in range(animal_count) ]
        self.objects = [
            Food(
                random.randrange(0, self.width, 1),
                random.randrange(0, self.height, 1),
                10
            ) for _ in range(animal_count)
        ]
        for a in self.animals:
            a.teleport(
                random.randrange(0, self.width, 1),
                random.randrange(0, self.height, 1),
                random.uniform(0, 6.28)
            )
        self.next_food = random.expovariate(1.0/FOOD_PERIOD)
        self.next_poison = random.expovariate(1.0/POISON_PERIOD)
        self.pheromones = self.manager.list([])
        self.next_breed = random.expovariate(1.0/BREEDING_PERIOD)
        self.new_genomes = []

    def insert_animal(self, genome):
        a = Animal(genome, PHEROMONES)
        a.teleport(
            random.randrange(0, self.width, 1),
            random.randrange(0, self.height, 1),
            random.uniform(0, 6.28)
        )
        self.animals.append(a)
        self.objects.append(Food(
            random.randrange(0, self.width, 1),
            random.randrange(0, self.height, 1),
            10
        ))

    def update(self, timestep):
        
        self.next_food -= timestep
        if self.next_food <= 0.0:
            self.next_food = random.expovariate(1.0/FOOD_PERIOD)
            self.objects.append(Food(
                random.randrange(0, self.width, 1),
                random.randrange(0, self.height, 1),
                10
            ))

        self.next_poison -= timestep
        if self.next_poison <= 0.0:
            self.next_poison = random.expovariate(1.0/POISON_PERIOD)
            self.objects.append(Poison(
                random.randrange(0, self.width, 1),
                random.randrange(0, self.height, 1),
                10
            ))

        self.next_breed -= timestep
        if self.next_breed <= 0.0:
            self.next_breed = random.expovariate(1.0/BREEDING_PERIOD)
            self.animals.sort(key=lambda a: a.energy, reverse=True)
            # choose parents
            parentA = 0
            while random.uniform(0,1) >= BREEDING_FITNESS:
                parentA += 1
            if parentA >= len(self.animals):
                parentA = len(self.animals) - 1
            parentB = 0
            while random.uniform(0,1) >= BREEDING_FITNESS:
                parentB += 1
            if parentB >= len(self.animals):
                parentB = len(self.animals) - 1
            # breed
            self.new_genomes.append(self.pool.apply_async(
                breed,
                (self.animals[parentA].brain.genome, self.animals[parentB].brain.genome)
            ))

        if len(self.new_genomes) > 0 and self.new_genomes[0].ready():
            new_genome = self.new_genomes.pop(0)
            child = Animal(new_genome.get(), PHEROMONES)
            child.teleport(
                random.randrange(0, self.width, 1),
                random.randrange(0, self.height, 1),
                random.uniform(0, 6.28)
            )
            self.animals.append(child)

        result = list(zip(*(a for a in self.pool.starmap(update_animal,
            ((a, self.pheromones, timestep, self.width, self.height) for a in self.animals)
        ))))
        self.animals = [ a for a in result[0] if a.energy > 0 ]
        for fl in result[1]:
            self.pheromones.extend(fl)

        for f in self.objects:
            f.update(self.animals, self.pheromones, timestep)

        for p in self.predators:
            p.update(self.animals, self.pheromones, timestep, self.width, self.height)

        for f in self.pheromones:
            f.tick(timestep)

        # remove finished foods
        self.objects = [ f for f in self.objects if f.amount > 0.0 ]
        # remove vanished pheromones
        self.pheromones = [ f for f in self.pheromones if f.power() > 0.1 ]

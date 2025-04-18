"""
World related operations
"""


import random
import numpy as np
from scipy.ndimage import zoom
from source.blocks import *
from source.options import *
from source.exceptions import *


class World:
    """
    Container for large amount of cubes
    """

    def __init__(self):
        self.voxels: np.ndarray = np.zeros(WORLD_SIZE ** 3, dtype=np.uint8)

        self.sun: tuple[float, float, float] = (1, 2, -3)
        length = (self.sun[0]**2 + self.sun[1]**2 + self.sun[2]**2) ** 0.5
        self.sun = (self.sun[0] / length, self.sun[1] / length, self.sun[2] / length)

    def set_unsafe(self, position: tuple[int, int, int], value: int) -> None:
        """
        Sets block at given XYZ to given value.
        Don't use it unless you are sure the position doesn't go over chunk bounds.
        :param position: block position
        :param value: id to set
        """

        self.voxels[position[2] * WORLD_LAYER + position[1] * WORLD_SIZE + position[0]] = value

    def set(self, position: tuple[int, int, int], value: int | str) -> bool:
        """
        High level method that sets block at given XYZ to given value.
        :param position: block position
        :param value: id to set
        :return: True when block was set, False when block was out of bounds
        """

        if isinstance(value, str):
            value = Blocks.named.get(value)
            if value is None:
                return False

        if (-1 < position[0] < WORLD_SIZE) and (-1 < position[1] < WORLD_SIZE) and (-1 < position[2] < WORLD_SIZE):
            self.voxels[position[2] * WORLD_LAYER + position[1] * WORLD_SIZE + position[0]] = value
            return True
        return False

    # noinspection PyTypeChecker
    def get_unsafe(self, position: tuple[int, int, int]) -> int:
        """
        Gets block at given XYZ to given value.
        Don't use it unless you are sure the position doesn't go over chunk bounds.
        :param position: block position
        """

        return self.voxels[position[2] * WORLD_LAYER + position[1] * WORLD_SIZE + position[0]]

    # noinspection PyTypeChecker
    def get(self, position: tuple[int, int, int]) -> int:
        """
        Gets block at given XYZ to given value
        :param position: block position
        :return: block id when inbound, -1 when out of bounds
        """

        if (-1 < position[0] < WORLD_SIZE) and (-1 < position[1] < WORLD_SIZE) and (-1 < position[2] < WORLD_SIZE):
            return self.voxels[position[2] * WORLD_LAYER + position[1] * WORLD_SIZE + position[0]]
        return -1

    def save(self, filename: str):
        """
        Saves the world to file with given name.
        :param filename: name of the file
        """

        np.save(filename, self.voxels)

    def load(self, filename: str) -> None:
        """
        Loads the world from a file with given name.
        :param filename: name of the file
        """

        self.voxels = np.load(filename)

        # Check correct world size
        if self.voxels.shape != (WORLD_SIZE**3,):
            raise WorldGenSizeError("Incorrect world size")


class WorldGen:
    """
    World generation
    """

    @staticmethod
    def generate_flat(level: int) -> World:
        """
        Generates a flat chunk
        :param level: sea level
        :return: generated world
        """

        world = World()
        for y in range(WORLD_SIZE):
            for x in range(WORLD_SIZE):
                for z in range(level):
                    world.set_unsafe((x, y, z), 1)
        return world

    @staticmethod
    def generate_debug(infill: float) -> World:
        """
        Generates chunk with randomly placed blocks with a given infill
        :param infill: % of space filled
        :return: generated world
        """

        world = World()
        voxels = np.random.random(WORLD_SIZE ** 3)
        world.voxels = (np.vectorize(lambda x: x < infill)(voxels)).astype(np.uint8)
        return world

    @staticmethod
    def generate_landscape(level: int, magnitude: float) -> World:
        """
        Generates simple landscape
        :param level: sea level
        :param magnitude: magnitude
        :return: generated world
        """

        print("Generating height map...")
        octets = [
            (2, 0.05),
            (4, 0.05),
            (8, 0.2),
            (16, 0.2),
            (32, 0.5)]
        height_map = np.zeros([WORLD_SIZE, WORLD_SIZE], dtype=np.float64)
        for octet, influence in octets:
            temp_height_map = np.random.random([WORLD_SIZE // octet, WORLD_SIZE // octet]).astype(np.float64)
            height_map += zoom(temp_height_map, octet) * influence
        print("done;\n")

        print("Putting in the blocks...")
        world = World()
        for y in range(WORLD_SIZE):
            for x in range(WORLD_SIZE):
                height = int((height_map[y][x] - 0.5) * magnitude + level)
                for z in range(height):
                    if z == height - 1:  # grass
                        world.set((x, y, z), "grass_block")
                    else:  # dirt
                        world.set((x, y, z), "dirt_block")
                if random.random() > 0.9:
                    WorldGen.generate_tree(world, (x, y, height))
            if y % (WORLD_SIZE // 25) == 0:
                print(f"{y / WORLD_SIZE * 100:.2f}% done;")
        print("done;\n")

        return world

    @staticmethod
    def generate_tree(world: World, pos: tuple[int, int, int]):
        """
        Generates a tree at given position
        """

        height = int(random.random() * 4) + 3
        leaves_height = random.random() * 2 + 1
        for i in range(height):
            world.set((pos[0], pos[1], pos[2] + i), "oak_logs")

            if i >= leaves_height:
                world.set((pos[0], pos[1] + 1, pos[2] + i), "oak_leaves")
                world.set((pos[0], pos[1] - 1, pos[2] + i), "oak_leaves")
                world.set((pos[0] + 1, pos[1], pos[2] + i), "oak_leaves")
                world.set((pos[0] - 1, pos[1], pos[2] + i), "oak_leaves")
        world.set((pos[0], pos[1], pos[2] + height), "oak_leaves")


class Ray:
    """
    Ray class
    """

    def __init__(self, origin: tuple[float, float, float], direction: tuple[float, float, float]):
        self.origin: tuple[float, float, float] = origin
        self.direction: tuple[float, float, float] = direction

        self.integer_position: list[int] = [0, 0, 0]
        self.float_position: list[float] = [0, 0, 0]
        self.length: float = 0

    def cast(self, world: World) -> "Ray":
        """
        Casts the ray for the given world.
        :returns: ray
        """

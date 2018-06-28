import random

from src.world.worldstate import World
from src.game.enemies import EnemyFactory
from src.world.entities import Player, ExitEntity, DoorEntity, ChestEntity


NEIGHBORS = [(-1, 0), (0, -1), (1, 0), (0, 1)]
DIAGS = [(-1, -1), (1, -1), (1, 1), (-1, 1)]


class Room:

    def __init__(self):
        self.x = 0
        self.y = 0
        self._floor = set()
        self._walls = set()

        self._adj_rooms = []
        self._doors = []

    def offset(self):
        return (self.x, self.y)

    def set_offset(self, x, y):
        self.x = x
        self.y = y

    def add_neighbor(self, room, door_pos):
        self._adj_rooms.append(room)
        self._doors.append((door_pos[0] - self.x, door_pos[1] - self.y))

    def all_floors(self):
        for f in self._floor:
            yield (f[0] + self.x, f[1] + self.y)

    def all_walls(self):
        for w in self._walls:
            yield (w[0] + self.x, w[1] + self.y)

    def all_doors(self):
        for d in self._doors:
            yield (d[0] + self.x, d[1] + self.y)

    def get_adorable_walls(self):
        """
            it's a pun, get it? adorable == door-able. walls that can be replaced with doors.
        """
        res = []
        for w in self.all_walls():
            # needs to be wall, floor, wall, empty clockwise
            for i in range(0, 4):
                ns = []
                for j in range(0, len(NEIGHBORS)):
                    ns.append((w[0] + NEIGHBORS[(j + i) % 4][0], w[1] + NEIGHBORS[(j + i) % 4][1]))

                if (self.has_wall_at(ns[0]) and self.has_floor_at(ns[1])
                        and self.has_wall_at(ns[2]) and self.is_empty_at(ns[3])):
                    res.append(w)
        return res

    def autofill_walls(self):
        for f in self._floor:
            for n in NEIGHBORS:
                p = (f[0] + n[0], f[1] + n[1])
                if p not in self._floor:
                    self._walls.add(p)

    def is_empty_at(self, xy):
        return not self.has_floor_at(xy) and not self.has_wall_at(xy)

    def has_wall_at(self, xy):
        return (xy[0] - self.x, xy[1] - self.y) in self._walls

    def has_floor_at(self, xy):
        return (xy[0] - self.x, xy[1] - self.y) in self._floor

    def add_to_blueprint(self, bp):
        for w in self.all_walls():
            bp.set(*w, World.WALL)
        for f in self.all_floors():
            bp.set(*f, World.FLOOR)
        for d in self.all_doors():
            bp.set(*d, World.DOOR)


class RoomFactory:

    @staticmethod
    def gen_room(self):
        pass

    @staticmethod
    def gen_rand_rectangular_room(w_range, h_range):
        w = w_range[0] + int((w_range[1] - w_range[0]) * random.random())
        h = h_range[0] + int((h_range[1] - h_range[0]) * random.random())
        return RoomFactory.gen_rectangular_room(w, h)

    @staticmethod
    def gen_rectangular_room(w, h):
        res = Room()
        for x in range(0, w):
            for y in range(0, h):
                res._floor.add((x, y))
        res.autofill_walls()
        return res


class BuilderUtils:

    @staticmethod
    def can_place_room(room, room_list):
        for floor_pos in room.all_floors():
            for existing_room in room_list:
                if existing_room.has_floor_at(floor_pos):
                    return False
        return True

    @staticmethod
    def attempt_to_add_room(to_place, to_attach_to, all_rooms, num_attempts=300):
        to_place.set_offset(0, 0)
        doors1 = to_place.get_adorable_walls()
        doors2 = to_attach_to.get_adorable_walls()
        print(doors1)
        print(doors2)

        if len(doors1) == 0 or len(doors2) == 0:
            return False
        else:
            for _ in range(0, num_attempts):
                d1 = doors1[int(len(doors1) * random.random())]
                d2 = doors2[int(len(doors2) * random.random())]
                offs = (d2[0] - d1[0], d2[1] - d1[1])
                print("trying position {}".format(offs))
                to_place.set_offset(*offs)
                if BuilderUtils.can_place_room(to_place, all_rooms):
                    print("placing room at {}".format(to_place.offset()))
                    to_place.add_neighbor(to_attach_to, d2)
                    to_attach_to.add_neighbor(to_place, d2)
                    all_rooms.append(to_place)
                    return True
        return False

    @staticmethod
    def shift_to_origin_and_get_size(room_list):
        bounds = None
        for room in room_list:
            for w in room.all_walls():
                if bounds is None:
                    bounds = [w[0], w[1], w[0], w[1]]
                else:
                    bounds[0] = min(w[0], bounds[0])
                    bounds[1] = min(w[1], bounds[1])
                    bounds[2] = max(w[0], bounds[2])
                    bounds[3] = max(w[1], bounds[3])

        size = (bounds[2] - bounds[0] + 1, bounds[3] - bounds[1] + 1)
        for room in room_list:
            offs = room.offset()
            room.set_offset(offs[0] - bounds[0], offs[1] - bounds[1])

        return size


class WorldBlueprint:

    def __init__(self, size, level):
        self.size = size
        self.level = level
        self.geo = []
        for i in range(0, size[0]):
            self.geo.append([World.EMPTY] * size[1])

        self.player_spawn = [1, 1]
        self.enemy_spawns = []
        self.chest_spawns = []
        self.exit_spawn = [2, 1]

    def get(self, x, y):
        if self.is_valid(x, y):
            return self.geo[x][y]
        else:
            return World.EMPTY

    def set(self, x, y, val):
        if self.is_valid(x, y):
            self.geo[x][y] = val

    def is_valid(self, x, y):
        return 0 <= x < self.size[0] and 0 <= y < self.size[1]

    def build_world(self):
        w = World(*self.size)
        for x in range(0, self.size[0]):
            for y in range(0, self.size[1]):
                w.set_geo(x, y, self.geo[x][y])
                if self.geo[x][y] == World.DOOR:
                    w.add(DoorEntity(x, y))

        for spawn_pos in self.enemy_spawns:
            enemies = EnemyFactory.gen_enemies(self.level, n=2)
            for e in enemies:
                w.add(e, gridcell=spawn_pos)

        for chest_pos in self.chest_spawns:
            w.add(ChestEntity(0, 0), gridcell=chest_pos)

        w.add(Player(0, 0), gridcell=self.player_spawn)
        w.add(ExitEntity(*self.exit_spawn))

        return w


def is_perfect_door_location(bp, x, y):
    left_geo = bp.get(x - 1, y)
    right_geo = bp.get(x + 1, y)
    up_geo = bp.get(x, y - 1)
    down_geo = bp.get(x, y + 1)

    config = (left_geo, right_geo, up_geo, down_geo)
    v_door = (World.WALL, World.WALL, World.FLOOR, World.FLOOR)
    h_door = (World.FLOOR, World.FLOOR, World.WALL, World.WALL)
    return config == v_door or config == h_door


def rand_iterate_through_points(x, y, w, h):
    all_points = []
    for x_i in range(x, x + w):
        for y_i in range(y, y + h):
            all_points.append((x_i, y_i))
    random.shuffle(all_points)
    return all_points


class WorldFactory:
    MAX_SIZE = (15, 10)
    ROOM_NUM_BOUNDS = [10, 30]

    @staticmethod
    def gen_world_from_rooms(num_rooms=8):
        size_range = (3, 8)
        rooms = []
        idx = 0

        while len(rooms) < num_rooms:
            r = RoomFactory.gen_rand_rectangular_room(size_range, size_range)
            if len(rooms) == 0:
                rooms.append(r)
            else:
                to_add_to = rooms[idx]
                if BuilderUtils.attempt_to_add_room(r, to_add_to, rooms, num_attempts=3):
                    idx = len(rooms) - 1
                else:
                    idx = (idx - 1) % len(rooms)

        size = BuilderUtils.shift_to_origin_and_get_size(rooms)

        bp = WorldBlueprint(size, 5)
        for room in rooms:
            room.add_to_blueprint(bp)

        WorldFactory._fill_corners(bp)

        flrs = [f for f in rooms[0].all_floors()]
        random.shuffle(flrs)
        bp.player_spawn = flrs[0]

        bp.enemy_spawns = WorldFactory._get_random_floors(bp, num_rooms // 2)
        bp.chest_spawns = WorldFactory._get_random_floors(bp, num_rooms // 3)

        bp.exit_spawn = WorldFactory._get_random_exit_pos(bp)

        return bp

    @staticmethod
    def _get_random_exit_pos(bp):
        for pt in rand_iterate_through_points(0, 0, bp.size[0], bp.size[1]):
            if bp.get(*pt) == World.FLOOR and bp.get(pt[0], pt[1] - 1) == World.WALL:
                return pt

    @staticmethod
    def _get_random_floors(bp, max_num_to_grab):
        res = []
        for pt in rand_iterate_through_points(0, 0, bp.size[0], bp.size[1]):
            if bp.get(*pt) == World.FLOOR:
                res.append(pt)
                if len(res) >= max_num_to_grab:
                    return res

        return res

    @staticmethod
    def _fill_corners(bp):
        for x in range(0, bp.size[0]):
            for y in range(0, bp.size[1]):
                if bp.get(x, y) == World.FLOOR:
                    for n in DIAGS:
                        if bp.get(x + n[0], y + n[1]) == World.EMPTY:
                            bp.set(x + n[0], y + n[1], World.WALL)

    @staticmethod
    def gen_test_world(level):
        width, height = WorldFactory.MAX_SIZE
        bp = WorldBlueprint((width, height), level)

        for x in range(0, width):
            for y in range(0, height):
                if x == 0 or y == 0 or x == width - 1 or y == height - 1:
                    bp.geo[x][y] = World.WALL
                elif x < 3 and y < 3:
                    bp.geo[x][y] = World.FLOOR
                else:
                    if random.random() < 0.33:
                        bp.geo[x][y] = World.WALL
                    else:
                        bp.geo[x][y] = World.FLOOR

        for x in range(0, width):
            for y in range(0, height):
                if bp.geo[x][y] == World.FLOOR:
                    if is_perfect_door_location(bp, x, y):
                        if random.random() < 0.5:
                            bp.set(x, y, World.DOOR)

                    elif random.random() < 0.05:
                        bp.enemy_spawns.append((x, y))

                    elif random.random() < 0.05:
                        bp.chest_spawns.append((x, y))

        bp.exit_spawn = WorldFactory._get_random_exit_pos(bp)

        return bp


if __name__ == "__main__":
    room1 = RoomFactory.gen_rectangular_room(3, 3)
    room2 = RoomFactory.gen_rectangular_room(7, 3)
    print(room2.get_adorable_walls())
    BuilderUtils.attempt_to_add_room(room1, room2, [room2])
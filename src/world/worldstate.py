import random
import math
from collections import deque

import src.renderengine.img as img
import src.game.spriteref as spriteref
from src.utils.util import Utils


CELLSIZE = 64


class World:
    EMPTY = 0
    WALL = 1
    DOOR = 2
    FLOOR = 3 
    
    SOLIDS = [WALL, DOOR]
    
    def __init__(self, width, height):
        self._size = (width, height)
        self._level_geo = []
        self._hidden = []
        self._active_light_events = []
        self._light_update_freq = 1  # ticks per update
        self._bg_color = (92, 92, 92)

        for _ in range(0, width):
            self._level_geo.append([World.EMPTY] * height)
            self._hidden.append([False] * height)

        self._geo_bundle_lookup = {}    # x,y -> bundle id

        self._onscreen_bundles = set()

        self._dirty_bundles = []

        self.entities = []
        self._ents_to_remove = []
        self._ents_to_add = []
        self._onscreen_entities = set()

        self._wall_type = spriteref.WALL_NORMAL_ID
        self._floor_type = spriteref.FLOOR_NORMAL_ID

        self._wall_art_overrides = {}  # x,y -> wall_type_id
        self._floor_art_overrides = {}  # x,y -> floor_type_id

    def cellsize(self):
        return CELLSIZE
        
    def add(self, entity, gridcell=None, next_update=True):
        """
            gridcell: (grid_x, grid_y) or None
        """
        if entity is None:
            raise ValueError("tried to add None to world.")

        if gridcell is not None:
            x = gridcell[0] * self.cellsize() + (self.cellsize() - entity.w()) // 2
            y = gridcell[1] * self.cellsize() + (self.cellsize() - entity.h()) // 2
            entity.set_x(x)
            entity.set_y(y)

        if next_update:
            self._ents_to_add.append(entity)
        else:
            self.entities.append(entity)
            entity._alive = True
        
    def remove(self, entity):
        self._ents_to_remove.append(entity)

    def __contains__(self, entity):
        return entity in self.entities
        
    def get_player(self):
        for e in self.entities:
            if e.is_player():
                return e
        return None

    def get_npc(self, npc_id):
        for e in self.entities:
            if e.is_npc() and e.get_id() == npc_id:
                return e
        return None
    
    def entities_in_circle(self, center, radius, onscreen=True):
        """
            returns: list of entities in circle, sorted by distance from center 
        """
        r2 = radius*radius
        res = []
        search_space = self._onscreen_entities if onscreen else self.entities
        for e in search_space:
            e_c = e.center()
            dx = e_c[0] - center[0]
            dy = e_c[1] - center[1]
            if dx*dx + dy*dy <= r2:
                res.append(e)
        
        res.sort(key=lambda e: Utils.dist(center, e.center()))
        
        return res

    def set_wall_type(self, wall_id, xy=None):
        if xy is None:
            self._wall_type = wall_id
        elif wall_id is None:
            if xy in self._wall_art_overrides:
                del self._wall_art_overrides[xy]
        else:
            self._wall_art_overrides[xy] = wall_id

    def wall_type_at(self, grid_xy):
        if grid_xy in self._wall_art_overrides:
            return self._wall_art_overrides[grid_xy]
        else:
            return self._wall_type

    def set_floor_type(self, floor_id, xy=None):
        if xy is None:
            self._floor_type = floor_id
        elif floor_id is None:
            if xy in self._floor_art_overrides:
                del self._floor_art_overrides[xy]
        else:
            self._floor_art_overrides[xy] = floor_id

    def floor_type_at(self, grid_xy):
        if grid_xy in self._floor_art_overrides:
            return self._floor_art_overrides[grid_xy]
        else:
            return self._floor_type

    def set_geo(self, grid_x, grid_y, geo_id):
        if self.is_valid(grid_x, grid_y):
            self._level_geo[grid_x][grid_y] = geo_id
        elif geo_id != World.EMPTY:
            raise ValueError("Cannot set out of bounds grid cell to " + 
                    "non-empty: ({}, {}) <- {}".format(grid_x, grid_y, geo_id))

    def to_grid_coords(self, pixel_x, pixel_y):
        return (pixel_x // CELLSIZE, pixel_y // CELLSIZE)

    def get_geo(self, grid_x, grid_y):
        if self.is_valid(grid_x, grid_y):
            return self._level_geo[grid_x][grid_y]
        else:
            return World.EMPTY

    def get_geo_at(self, pixel_x, pixel_y):
        return self.get_geo(pixel_x // self.cellsize(), pixel_y // self.cellsize())

    def door_opened(self, grid_x, grid_y):
        print("door opened at {}".format((grid_x, grid_y)))
        for n in World.NEIGHBORS:
            self.set_hidden(grid_x + n[0], grid_y + n[1], False, and_fill_adj_floors=True)

    def get_hidden_at(self, pixel_x, pixel_y):
        return self.get_hidden(*self.to_grid_coords(pixel_x, pixel_y))

    def get_hidden(self, grid_x, grid_y):
        if self.is_valid(grid_x, grid_y):
            return self._hidden[grid_x][grid_y]
        else:
            return False

    def set_bg_color(self, color):
        self._bg_color = color

    def get_bg_color(self):
        return self._bg_color

    def set_hidden(self, grid_x, grid_y, val, and_fill_adj_floors=True):
        if self.get_geo(grid_x, grid_y) == World.FLOOR and self._hidden[grid_x][grid_y] != val:
            self._hidden[grid_x][grid_y] = val
            self.update_geo_bundle(grid_x, grid_y, and_neighbors=False)

            if and_fill_adj_floors:
                for n in World.NEIGHBORS:
                    self.set_hidden(grid_x + n[0], grid_y + n[1], val, and_fill_adj_floors=True)

    def hide_all_floors(self):
        for x in range(0, self.size()[0]):
            for y in range(0, self.size()[1]):
                if self.get_geo(x, y) == World.FLOOR:
                    self.set_hidden(x, y, True, and_fill_adj_floors=False)

    def is_solid_at(self, pixel_x, pixel_y):
        geo = self.get_geo_at(pixel_x, pixel_y)
        return geo in World.SOLIDS
            
    def is_valid(self, grid_x, grid_y):
        return 0 <= grid_x < self.size()[0] and 0 <= grid_y < self.size()[1]

    def size(self):
        return self._size

    NEIGHBORS = [(-1, 0), (0, -1), (1, 0), (0, 1)]
    ALL_NEIGHBORS = [(-1, -1), (0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0)]
    
    def get_neighbor_info(self, grid_x, grid_y, mapping=lambda x: x):
        return [mapping(self.get_geo(grid_x + offs[0], grid_y + offs[1])) for offs in World.ALL_NEIGHBORS]

    def update_geo_bundle(self, grid_x, grid_y, and_neighbors=False):
        if not self.is_valid(grid_x, grid_y):
            return

        bundle = self.get_geo_bundle(grid_x, grid_y)
        sprite = self.calc_sprite_for_geo(grid_x, grid_y)
        if bundle is not None:
            if sprite is not None:
                new_bun = bundle.update(new_model=sprite, new_x=grid_x*CELLSIZE, new_y=grid_y*CELLSIZE,
                                        new_scale=4, new_depth=10)
                self._geo_bundle_lookup[(grid_x, grid_y)] = new_bun
                self._dirty_bundles.append((grid_x, grid_y))

        if and_neighbors:
            for n in World.ALL_NEIGHBORS:
                self.update_geo_bundle(grid_x + n[0], grid_y + n[1], and_neighbors=False)

    def calc_sprite_for_geo(self, grid_x, grid_y):
        geo = self.get_geo(grid_x, grid_y)

        if geo == World.WALL:
            def mapping(x): return 1 if x == World.WALL or x == World.DOOR else 0
            n_info = self.get_neighbor_info(grid_x, grid_y, mapping=mapping)
            mults = [1, 2, 4, 8, 16, 32, 64, 128]
            wall_img_id = sum(n_info[i] * mults[i] for i in range(0, 8))
            return spriteref.get_wall(wall_img_id, wall_type_id=self.wall_type_at((grid_x, grid_y)))

        elif geo == World.DOOR:
            return spriteref.floor_totally_dark

        elif geo == World.FLOOR:
            if self.get_hidden(grid_x, grid_y):
                return spriteref.floor_hidden
            else:
                def mapping(x): return 1 if x in (World.WALL, World.EMPTY, World.DOOR) else 0
                n_info = self.get_neighbor_info(grid_x, grid_y, mapping=mapping)

                floor_img_id = 2 * n_info[0] + 4 * n_info[1] + 1 * n_info[7]
                return spriteref.get_floor(floor_img_id, floor_type_id=self.floor_type_at((grid_x, grid_y)))

        return None

    def get_geo_bundle(self, grid_x, grid_y):
        key = (grid_x, grid_y)
        if key in self._geo_bundle_lookup:
            return self._geo_bundle_lookup[key] 
        else:
            geo = self.get_geo(grid_x, grid_y)
            if geo is World.WALL:
                layer = spriteref.WALL_LAYER
            else:
                layer = spriteref.FLOOR_LAYER

            self._geo_bundle_lookup[key] = img.ImageBundle(None, 0, 0, layer=layer)
            self.update_geo_bundle(grid_x, grid_y)
            return self._geo_bundle_lookup[key]

    def get_all_bundles(self, geo_id=None):
        res = []
        for x in range(0, self.size()[0]):
            for y in range(0, self.size()[1]):
                if geo_id is None or self.get_geo(x, y) == geo_id:
                    bun = self.get_geo_bundle(x, y)
                    if bun is not None:
                        res.append(bun)
                    
        return res

    def _update_onscreen_geo_bundles(self, gs, render_engine):
        px, py = gs.get_world_camera()
        pw, ph = gs.get_world_camera_size()
        grid_rect = [px // CELLSIZE, py // CELLSIZE,
                     pw // CELLSIZE + 3, ph // CELLSIZE + 3]

        new_onscreen = set()
        for x in range(grid_rect[0], grid_rect[0] + grid_rect[2]):
            for y in range(grid_rect[1], grid_rect[1] + grid_rect[3]):
                bun_key = (x, y)
                bun = self.get_geo_bundle(*bun_key)
                if bun is not None:
                    new_onscreen.add(bun_key)
                    if bun_key not in self._onscreen_bundles or bun_key in self._dirty_bundles:
                        render_engine.update(bun)

        for bun_key in self._onscreen_bundles:
            if bun_key not in new_onscreen:
                render_engine.remove(self.get_geo_bundle(*bun_key))

        self._onscreen_bundles = new_onscreen

    def update_all(self, gs, input_state, render_engine):
        for e in self._ents_to_add:
            self.entities.append(e)
            e._alive = True
        self._ents_to_add.clear()

        for e in self._ents_to_remove:
            self.entities.remove(e)  # n^2 but whatever
            e._alive = False
            if e in self._onscreen_entities:
                self._onscreen_entities.remove(e)
            e.cleanup(gs, render_engine)
        self._ents_to_remove.clear()

        cam_center = gs.get_world_camera(center=True)

        for e in self.entities:
            e_center = e.center()
            on_camera = Utils.dist(e.center(), cam_center) <= 800
            is_hidden = self.get_hidden(*self.to_grid_coords(*e_center))

            if on_camera:
                # still want them to wander around if they're hidden
                e.update(self, gs, input_state, render_engine)

            if on_camera and not is_hidden:
                self._onscreen_entities.add(e)
                for bun in e.all_bundles():
                    render_engine.update(bun)

            elif e in self._onscreen_entities:
                e.cleanup(gs, render_engine)
                self._onscreen_entities.remove(e)

        p = self.get_player()
        if p is not None:
            cam_center = gs.get_world_camera(center=True)
            dist = Utils.dist(cam_center, p.center())
            min_speed = 10
            max_speed = 20
            if dist > 200 or dist <= min_speed:
                gs.set_world_camera_center(*p.center())
            else:
                speed = min_speed + (max_speed - min_speed) * math.sqrt(dist / 200)
                move_xy = Utils.set_length(Utils.sub(p.center(), cam_center), speed)
                new_pos = Utils.add(cam_center, move_xy)
                gs.set_world_camera_center(*Utils.round(new_pos))

        self._update_onscreen_geo_bundles(gs, render_engine)

    def cleanup_active_bundles(self, render_eng):
        for e in self._onscreen_entities:
            for bun in e.all_bundles():
                render_eng.remove(bun)
        self._onscreen_entities.clear()

        for bun_key in self._onscreen_bundles:
            render_eng.remove(self._geo_bundle_lookup[bun_key])
        self._onscreen_bundles.clear()








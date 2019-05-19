import math
import random
import os
import json
import sys
import numbers

import pygame


class Utils:

    @staticmethod
    def bound(val, lower, upper):
        if upper is not None and val > upper:
            return upper
        elif lower is not None and val < lower:
            return lower
        else:
            return val

    @staticmethod
    def add(v1, v2):
        return tuple(i[0] + i[1] for i in zip(v1, v2))

    @staticmethod
    def sub(v1, v2):
        return tuple(i[0] - i[1] for i in zip(v1, v2))

    @staticmethod
    def mult(v, a):
        return tuple(a*v_i for v_i in v)

    @staticmethod
    def rotate(v, rad):
        cos = math.cos(rad)
        sin = math.sin(rad)
        return (v[0]*cos - v[1]*sin, v[0]*sin + v[1]*cos)

    @staticmethod
    def to_degrees(rads):
        return rads * 180 / 3.141529

    @staticmethod
    def to_rads(degrees):
        return degrees * 3.141529 / 180

    @staticmethod
    def set_length(v, length):
        mag = math.sqrt(v[0]*v[0] + v[1]*v[1])
        if mag == 0:
            return Utils.rand_vec(length)
        else:
            return Utils.mult(v, length / mag)

    @staticmethod
    def mag(v):
        return math.sqrt(sum(i*i for i in v))

    @staticmethod
    def dist(v1, v2):
        return Utils.mag(Utils.sub(v1, v2))

    @staticmethod
    def dist_manhattan(v1, v2):
        res = 0
        for i, j in zip(v1, v2):
            res += abs(i - j)
        return res

    @staticmethod
    def rand_vec(length=1):
        angle = 6.2832 * random.random()
        return [length*math.cos(angle), length*math.sin(angle)]

    @staticmethod
    def rect_expand(rect, left_expand, right_expand, up_expand, down_expand):
        return [rect[0] - left_expand,
                rect[1] - up_expand,
                rect[2] + (left_expand + right_expand),
                rect[3] + (up_expand + down_expand)]

    @staticmethod
    def rect_contains(rect, v):
        return rect[0] <= v[0] < rect[0] + rect[2] and rect[1] <= v[1] < rect[1] + rect[3]

    @staticmethod
    def linear_interp(v1, v2, a):
        if isinstance(v1, numbers.Number):
            return v1 * (1 - a) + v2 * a
        else:
            return tuple([v1[i] * (1 - a) + v2[i] * a for i in range(0, len(v1))])

    @staticmethod
    def round(v):
        return tuple([round(i) for i in v])

    @staticmethod
    def replace_all_except(text, replace_txt, except_for=()):
        return "".join(x if (x in except_for) else replace_txt for x in text)

    @staticmethod
    def listify(obj):
        if (isinstance(obj, list)):
            return obj
        else:
            return [obj]

    @staticmethod
    def min_component(v_list, i):
        res = None
        for v in v_list:
            if i < len(v):
                res = min(v[i], res) if res is not None else v[i]
        return res

    @staticmethod
    def max_component(v_list, i):
        res = None
        for v in v_list:
            if i < len(v):
                res = max(v[i], res) if res is not None else v[i]
        return res

    @staticmethod
    def cells_between(p1, p2, include_endpoints=True):
        if p1 == p2:
            return [tuple(p1)] if include_endpoints else []

        start = [p1[0] + 0.5, p1[1] + 0.5]
        end = [p2[0] + 0.5, p2[1] + 0.5]

        xy = [start[0], start[1]]
        step_dist = 0.1
        step_vec = Utils.set_length(Utils.sub(end, start), step_dist)

        res = []
        for i in range(0, int(Utils.dist(start, end) // step_dist)):
            xy[0] = xy[0] + step_vec[0]
            xy[1] = xy[1] + step_vec[1]
            cur_cell = (int(xy[0]), int(xy[1]))
            if len(res) > 0 and res[-1] == cur_cell:
                continue
            else:
                if cur_cell == p1 or cur_cell == p2:
                    if include_endpoints:
                        res.append(cur_cell)
                else:
                    res.append(cur_cell)

        return res





    @staticmethod
    def stringify_key(keycode):
        if keycode == pygame.K_LEFT:
            return "←"
        elif keycode == pygame.K_UP:
            return "↑"
        elif keycode == pygame.K_RIGHT:
            return "→"
        elif keycode == pygame.K_DOWN:
            return "↓"
        elif isinstance(keycode, str) and keycode.startswith("MOUSE_BUTTON_"):
            num = keycode.replace("MOUSE_BUTTON_", "")
            return "M{}".format(num)
        else:
            return pygame.key.name(keycode)

    @staticmethod
    def resource_path(relative_path):
        """ Get absolute path to resource, works for dev and for PyInstaller """
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")

        return os.path.join(base_path, relative_path)

    @staticmethod
    def load_json_from_path(filepath):
        with open(filepath) as f:
            data = json.load(f)
            return data

    @staticmethod
    def save_json_to_path(json_blob, filepath):
        directory = os.path.dirname(filepath)
        if not os.path.exists(directory):
            os.makedirs(directory)

        with open(filepath, 'w') as outfile:
            json.dump(json_blob, outfile)

    @staticmethod
    def read_int(json_blob, key, default):
        return Utils.read_safely(json_blob, key, default, mapper=lambda x: int(x))

    @staticmethod
    def read_string(json_blob, key, default):
        return Utils.read_safely(json_blob, key, default, mapper=lambda x: str(x))

    @staticmethod
    def read_bool(json_blob, key, default):
        return Utils.read_safely(json_blob, key, default, mapper=lambda x: bool(x))

    @staticmethod
    def read_map(json_blob, key, default):
        return default  # hmmm, one day~

    @staticmethod
    def parabola_height(vertex_y, x):
        """
        finds f(x) of the parabola for which f(0) = 0, f(0.5) = vertex_y, f(1.0) = 0
        """
        #  mmm delicious math
        a = -4 * vertex_y
        b = 4 * vertex_y
        return (a * x * x) + (b * x)

    @staticmethod
    def get_shake_points(strength, duration, falloff=3, freq=6):
        """
        int strength: max pixel offset of shake
        int duration: ticks for which the shake will remain active
        int freq: "speed" of the shake. 1 is really fast, higher is slower
        """

        if duration % freq != 0:
            duration += freq - (duration % freq)

        decay = lambda t: math.exp(-falloff*(t / duration))
        num_keypoints = int(duration / freq)
        x_pts = [round(2 * (0.5 - random.random()) * strength * decay(t * freq)) for t in range(0, num_keypoints)]
        y_pts = [round(2 * (0.5 - random.random()) * strength * decay(t * freq)) for t in range(0, num_keypoints)]
        x_pts.append(0)
        y_pts.append(0)

        shake_pts = []
        for i in range(0, duration):
            if i % freq == 0:
                shake_pts.append((x_pts[i // freq], y_pts[i // freq]))
            else:
                prev_pt = (x_pts[i // freq], y_pts[i // freq])
                next_pt = (x_pts[i // freq + 1], y_pts[i // freq + 1])
                shake_pts.append(Utils.linear_interp(prev_pt, next_pt, (i % freq) / freq))

        if len(shake_pts) == 0:
            return  # this shouldn't happen but ehh

        shake_pts.reverse()  # this is used as a stack
        return shake_pts

    @staticmethod
    def neighbors(x, y, and_diags=False):
        yield (x + 1, y)
        yield (x, y + 1)
        yield (x - 1, y)
        yield (x, y - 1)
        if and_diags:
            yield (x + 1, y + 1)
            yield (x - 1, y + 1)
            yield (x + 1, y - 1)
            yield (x - 1, y - 1)

    @staticmethod
    def read_safely(json_blob, key, default, mapper=lambda x: x):
        if key not in json_blob or json_blob[key] is None:
            print("returning default {} for key {}".format(default, key))
            return default
        else:
            try:
                return mapper(json_blob[key])
            except ValueError:
                return default


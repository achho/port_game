import random
import time

import numpy as np
from shapely import Polygon, box

import port_game.vehicles
from port_game.Port import Port
from port_game.utils import overlap, compute_convex_hull, intersection, point_inside_convex_hull, rect_size


class Cargo:
    types = {
        1: {"color": "magenta", "width": 20, "height": 15, "freq": 0.5, "value": 1 / 0.5},
        2: {"color": "darkblue", "width": 25, "height": 25, "freq": 0.3, "value": 1 / 0.3},
        3: {"color": "#fefefe", "width": 20, "height": 35, "freq": 0.19, "value": 1 / 0.19},
        4: {"color": "gold", "width": 10, "height": 10, "freq": 0.01, "value": 1 / 0.01},
    }
    if np.sum([i["freq"] for i in types.values()]) != 1:
        raise ValueError("frequencies must add up to 1")

    def __init__(self, id, parent, port_game, coords, type):
        self.id = id
        self.parent = parent
        self.port_game = port_game
        self.type = type
        self.value = Cargo.types[self.type]["value"]
        self.no_drag = False
        self.anchor = None
        self.status = "dry"  # could be "sinking"
        self.owner = "lorry"  # could be "me" or "ship"
        self.area = self.port_game.canvas.create_rectangle(coords[0],
                                                           coords[1],
                                                           coords[2],
                                                           coords[3],
                                                           fill=Cargo.types[self.type]["color"])
        self.money_animation = None
        self.bind_dragging()

    @property
    def coords(self):
        return self.port_game.canvas.coords(self.area)

    @staticmethod
    def select_type_based_on_freq(exclude=None):
        random_float = random.random()
        if not exclude:
            exclude = []
        random_float *= sum([v["freq"] for i, v in Cargo.types.items() if i not in exclude])

        # Calculate cumulative frequencies
        cumulative_freq = 0
        cumulative_distribution = []
        for key, value in Cargo.types.items():
            if key in exclude:
                continue
            cumulative_freq += value["freq"]
            cumulative_distribution.append((key, cumulative_freq))

        # Select the type based on the random float
        for key, cum_freq in cumulative_distribution:
            if random_float < cum_freq:
                return key

        return None  # Fallback in case no type is found (shouldn't happen with proper freq values)

    def bind_dragging(self):
        self.port_game.canvas.tag_bind(self.area, "<ButtonPress-1>", self.on_drag_start)
        self.port_game.canvas.tag_bind(self.area, "<B1-Motion>", self.on_drag_move)
        self.port_game.canvas.tag_bind(self.area, "<ButtonRelease-1>", self.on_drag_stop)

    def on_drag_start(self, event):
        if isinstance(self.parent, port_game.vehicles.Lorry):
            if not self.parent.in_loading_position:
                self.no_drag = True
                return  # no unloading before parked
        self.no_drag = False
        self.anchor = (event.x - self.coords[0], event.y - self.coords[1])

    def on_drag_move(self, event):
        if self.no_drag:
            return  # wasn't allowed to start dragging

        self.port_game.canvas.tag_raise(self.area)  # stay on top of everything

        dx = event.x - self.coords[0] - self.anchor[0]
        dy = event.y - self.coords[1] - self.anchor[1]

        if isinstance(self.parent, port_game.vehicles.Lorry):
            dx = max(dx, self.parent.coords[0] - self.coords[0])
            dy = min(dy, self.parent.coords[3] - self.coords[3])
            dy = max(dy, self.parent.coords[1] - self.coords[1])
            if not overlap(self.coords, self.parent.coords):
                self.parent = self.port_game.port
                self.buy(1)
        elif isinstance(self.parent, Port):
            # dont go west of port area
            dx = max(dx, self.port_game.land_port_edge - self.coords[0])
            for iship in self.port_game.ship_queue.values():
                ship_overlap = intersection(self.coords, iship.coords)
                if ship_overlap:
                    port_overlap = intersection(self.port_game.canvas.coords(self.port_game.port.area), self.coords)
                    if (not port_overlap) or (rect_size(*ship_overlap) > rect_size(*port_overlap)):
                        self.parent = iship
                        break
        elif isinstance(self.parent, port_game.vehicles.Ship):
            port_overlap = intersection(self.port_game.canvas.coords(self.port_game.port.area), self.coords)
            if port_overlap:
                ship_overlap = intersection(self.parent.coords, self.coords)
                if (not ship_overlap) or (rect_size(*port_overlap) > rect_size(*ship_overlap)):
                    self.parent = self.port_game.port
        while self.is_collision(dx, dy):
            if dx > 0 and not self.is_collision(1, 0):
                self.move(1, 0)
                dx -= 1
            elif dx < 0 and not self.is_collision(-1, 0):
                self.move(-1, 0)
                dx += 1
            elif dy > 0 and not self.is_collision(0, 1):
                self.move(0, 1)
                dy -= 1
            elif dy < 0 and not self.is_collision(0, -1):
                self.move(0, -1)
                dy += 1
            else:
                return None

        self.move(dx, dy)

    def move(self, dx, dy):
        self.port_game.canvas.move(self.area, dx, dy)
        if self.money_animation:
            self.port_game.canvas.move(self.money_animation, dx, dy)

    def on_drag_stop(self, event=None):

        if isinstance(self.parent, Port):
            if self.will_sink():
                self.sink()

            # TODO: if now completely in ship that is accepting, parent = ship
        elif isinstance(self.parent, port_game.vehicles.Ship):
            pass
            # TODO: if now not completely in ship, parent = port

    def will_sink(self):
        supporting_rectangles = [self.port_game.canvas.coords(self.port_game.port.area)] + \
                                [i.coords for i in self.port_game.ship_queue.values() if (i.in_loading_position or i == self.parent)]
        dragged_center_x = (self.coords[0] + self.coords[2]) / 2
        dragged_center_y = (self.coords[1] + self.coords[3]) / 2

        intersect_points = []
        for i in supporting_rectangles:
            intersect = intersection(i, self.coords)
            if intersect:
                intersect_points.append((intersect[0], intersect[1]))
                intersect_points.append((intersect[2], intersect[1]))
                intersect_points.append((intersect[2], intersect[3]))
                intersect_points.append((intersect[0], intersect[3]))

        if intersect_points:
            hull = compute_convex_hull(intersect_points)
            return not point_inside_convex_hull((dragged_center_x, dragged_center_y), hull)
        return True

    def is_collision(self, dx, dy):

        def get_canvas_coords(item_id):
            coords = self.port_game.canvas.coords(item_id)
            if len(coords) == 4:
                return [(coords[0], coords[1]), (coords[2], coords[1]), (coords[2], coords[3]), (coords[0], coords[3])]
            else:
                return []

        def convex_hull_overlaps_any_rectangle(points):
            polygon = Polygon(points)

            for obstacle in list(self.port_game.cargo.values()) + list(self.port_game.ship_queue.values()):
                if isinstance(obstacle, Cargo) and obstacle.id == self.id:
                    continue
                if isinstance(obstacle, port_game.vehicles.Ship) and obstacle.in_loading_position and self.type in obstacle.wishlist:
                    continue  # allow overlap for loading
                rect_coords = get_canvas_coords(obstacle.area)
                if len(rect_coords) == 4:
                    rect = box(rect_coords[0][0], rect_coords[0][1], rect_coords[2][0], rect_coords[2][1])
                    if polygon.intersects(rect) and polygon.intersection(rect).area > 0:
                        return True

            return False

        combined_points = [(self.coords[0], self.coords[1]), (self.coords[2], self.coords[1]),
                           (self.coords[2], self.coords[3]), (self.coords[0], self.coords[3]),
                           (self.coords[0] + dx, self.coords[1] + dy), (self.coords[2] + dx, self.coords[1] + dy),
                           (self.coords[2] + dx, self.coords[3] + dy), (self.coords[0] + dx, self.coords[3] + dy)]

        convex_hull_points = compute_convex_hull(combined_points)
        return convex_hull_overlaps_any_rectangle(convex_hull_points)

    def sink(self, continued=False):
        if self.status == "sinking" and not continued:
            return None
        self.status = "sinking"
        c = self.coords
        if (c[2] - c[0]) > 2:
            self.port_game.canvas.coords(self.area, c[0] + 2, c[1], c[2], c[3])
            self.port_game.canvas.after(100, lambda: self.sink(continued=True))
        else:
            self.port_game.canvas.delete(self.area)
            self.port_game.cargo.pop(self.id)

    def init_money_animation(self, price):
        self.money_animation = self.port_game.canvas.create_text(self.coords[2] + 2, self.coords[1] - 2,
                                          text=f"{round(price)} $",
                                          fill="light green" if price >=0 else "red",
                                          font=("mono", 16),
                                          anchor="sw")
        self.port_game.root.after(500, self.lessen_money_animation)

    def lessen_money_animation(self):
        font = self.port_game.canvas.itemcget(self.money_animation, "font")
        font_size = font.split()[1]
        new_font = (font[0], int(font_size) - 2)
        if new_font[1] <= 5:
            self.port_game.canvas.delete(self.money_animation)
            self.money_animation = None
            return None
        self.port_game.canvas.itemconfig(self.money_animation, font=new_font)
        self.port_game.root.after(300, self.lessen_money_animation)

    def buy(self, factor):
        price = self.value * factor
        self.port_game.money -= price
        self.owner = "me"
        self.init_money_animation(-price)

    def sell(self, factor):
        price = self.value * factor
        self.port_game.money += price
        self.owner = "ship"
        self.init_money_animation(price)

import random

import numpy as np
from shapely import Polygon, box
from shapely.affinity import translate

import port_game.vehicles
from port_game.Port import Port
from port_game.utils import do_overlap, compute_convex_hull, point_inside_convex_hull, init_text_animation


class Cargo:
    types = {
        1: {"color": "magenta", "width": 20, "height": 15, "freq": 0.5, "value": 4 / 0.5},
        2: {"color": "darkblue", "width": 25, "height": 25, "freq": 0.3, "value": 4 / 0.3},
        3: {"color": "#fefefe", "width": 20, "height": 35, "freq": 0.19, "value": 4 / 0.19},
        4: {"color": "gold", "width": 10, "height": 10, "freq": 0.01, "value": 4 / 0.01},
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
        self.text_animation = None
        self.bind_dragging()

    @property
    def box(self):
        return box(*self.port_game.canvas.coords(self.area))

    @property
    def box_bounds(self):
        return self.box.bounds

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
            if self.port_game.money < self.value:
                self.no_drag = True
                self.init_text_animation("Not enough money", "red")
                return  # no money to buy
        self.no_drag = False
        self.anchor = (event.x - self.box_bounds[0], event.y - self.box_bounds[1])

    def on_drag_move(self, event):
        if self.no_drag:
            return  # wasn't allowed to start dragging

        self.port_game.canvas.tag_raise(self.area)  # stay on top of everything

        dx = event.x - self.box_bounds[0] - self.anchor[0]
        dy = event.y - self.box_bounds[1] - self.anchor[1]

        if isinstance(self.parent, port_game.vehicles.Lorry):
            dx = max(dx, self.parent.box_bounds[0] - self.box_bounds[0])
            dy = min(dy, self.parent.box_bounds[3] - self.box_bounds[3])
            dy = max(dy, self.parent.box_bounds[1] - self.box_bounds[1])
            if not do_overlap(self.box, self.parent.box):
                self.parent = self.port_game.port
                self.buy(1)
        elif isinstance(self.parent, Port):
            # dont go west of port area
            dx = max(dx, self.port_game.land_port_edge - self.box_bounds[0])
            for iship in self.port_game.ship_queue.values():
                ship_overlap = self.box.intersection(iship.box)
                if ship_overlap.area > 0:
                    port_overlap = self.port_game.port.box.intersection(self.box)
                    if (not port_overlap) or (ship_overlap.area > port_overlap.area):
                        self.parent = iship
                        break
        elif isinstance(self.parent, port_game.vehicles.Ship):
            port_overlap = self.port_game.port.box.intersection(self.box)
            if port_overlap:
                ship_overlap = self.parent.box.intersection(self.box)
                if (not ship_overlap) or (port_overlap.area > ship_overlap.area):
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
        if self.text_animation:
            self.port_game.canvas.move(self.text_animation, dx, dy)

    def on_drag_stop(self, event=None):

        if isinstance(self.parent, Port) or isinstance(self.parent, port_game.vehicles.Ship):
            if self.will_sink():
                self.sink()

    def will_sink(self):
        if self.status == "sinking":
            return False  # no need to compute anything anymore
        supporting_rectangles = [self.port_game.port.box] + \
                                [i.box for i in self.port_game.ship_queue.values() if (i.in_loading_position or i == self.parent)]
        dragged_center_x = (self.box_bounds[0] + self.box_bounds[2]) / 2
        dragged_center_y = (self.box_bounds[1] + self.box_bounds[3]) / 2
        intersect_points = []
        for i in supporting_rectangles:
            intersect = i.intersection(self.box)
            if intersect.area > 0:
                intersect_points.append((intersect.bounds[0], intersect.bounds[1]))
                intersect_points.append((intersect.bounds[2], intersect.bounds[1]))
                intersect_points.append((intersect.bounds[2], intersect.bounds[3]))
                intersect_points.append((intersect.bounds[0], intersect.bounds[3]))

        if intersect_points:
            hull = compute_convex_hull(intersect_points)
            return not point_inside_convex_hull((dragged_center_x, dragged_center_y), hull)
        return True

    def is_collision(self, dx, dy):

        def convex_hull_overlaps_any_rectangle(points):
            polygon = Polygon(points)

            for obstacle in list(self.port_game.cargo.values()) + list(self.port_game.ship_queue.values()):
                if isinstance(obstacle, Cargo) and obstacle.id == self.id:
                    continue
                if isinstance(obstacle, port_game.vehicles.Ship) and obstacle.in_loading_position and self.type in obstacle.wishlist:
                    continue  # allow overlap for loading
                if polygon.intersection(obstacle.box).area > 0:
                    return True

            return False

        orig_points = self.box.exterior.coords[:-1]
        shifted_points = translate(self.box, xoff=dx, yoff=dy).exterior.coords[:-1]

        combined_points = list(orig_points) + list(shifted_points)

        convex_hull_points = compute_convex_hull(combined_points)
        return convex_hull_overlaps_any_rectangle(convex_hull_points)

    def sink(self, continued=False):
        if self.status == "sinking" and not continued:
            return None
        self.status = "sinking"
        c = self.box_bounds
        if (c[2] - c[0]) > 2:
            self.port_game.canvas.coords(self.area, c[0] + 2, c[1], c[2], c[3])
            self.port_game.canvas.after(100, lambda: self.sink(continued=True))
        else:
            self.destroy()

    def buy(self, factor):
        price = self.value * factor
        self.port_game.money -= price
        self.owner = "me"
        self.text_animation = init_text_animation(self.text_animation, self.port_game, self.box_bounds[2] + 2, self.box_bounds[1] - 2, f"{round(-price)} $", "red")

    def sell(self, factor):
        price = self.value * factor
        self.port_game.money += price
        self.owner = "ship"
        self.text_animation = init_text_animation(self.text_animation, self.port_game, self.box_bounds[2] + 2, self.box_bounds[1] - 2, f"{round(price)} $", "green")

    def destroy(self):
        self.port_game.canvas.delete(self.area)
        self.port_game.cargo.pop(self.id)
import tkinter as tk
import numpy as np
from rectpack import newPacker, PackingMode
from shapely.geometry import Polygon, MultiPoint, box


def compute_convex_hull(points):
    multipoint = MultiPoint(points)
    convex_hull_polygon = multipoint.convex_hull
    return list(convex_hull_polygon.exterior.coords)


def point_inside_convex_hull(point, hull):
    x, y = point
    n = len(hull)
    inside = False
    for i in range(n):
        x1, y1 = hull[i]
        x2, y2 = hull[(i + 1) % n]
        if y1 <= y < y2 or y2 <= y < y1:
            if x > (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                inside = not inside
    return inside


def overlap(rect1, rect2):
    x0_1, y0_1, x1_1, y1_1 = rect1
    x0_2, y0_2, x1_2, y1_2 = rect2

    # Check for no overlap conditions
    if x1_1 < x0_2 or x0_1 > x1_2 or y1_1 < y0_2 or y0_1 > y1_2:
        return False
    return True


def intersection(rect1, rect2):
    # Rectangles are defined by (x1, y1, x2, y2)
    x1_r1, y1_r1, x2_r1, y2_r1 = rect1
    x1_r2, y1_r2, x2_r2, y2_r2 = rect2

    # Calculate intersection boundaries
    x_left = max(x1_r1, x1_r2)
    y_top = max(y1_r1, y1_r2)
    x_right = min(x2_r1, x2_r2)
    y_bottom = min(y2_r1, y2_r2)

    # Check if there is intersection
    if x_left < x_right and y_top < y_bottom:
        return x_left, y_bottom, x_right, y_top
    else:
        # No intersection
        return None


class Cargo:
    types = {1: {"color": "magenta", "width": 10, "height": 10},
             2: {"color": "darkblue", "width": 10, "height": 20},
             3: {"color": "#fefefe", "width": 15, "height": 30}}

    def __init__(self, id, parent, port_game, coords, type):
        self.id = id
        self.parent = parent
        self.port_game = port_game
        self.type = type
        self.no_drag = False
        self.anchor = None
        self.area = self.port_game.canvas.create_rectangle(coords[0],
                                                           coords[1],
                                                           coords[2],
                                                           coords[3],
                                                           fill=Cargo.types[self.type]["color"])
        self.bind_dragging()

    @property
    def coords(self):
        return self.port_game.canvas.coords(self.area)

    def bind_dragging(self):
        self.port_game.canvas.tag_bind(self.area, "<ButtonPress-1>", self.on_drag_start)
        self.port_game.canvas.tag_bind(self.area, "<B1-Motion>", self.on_drag_move)
        self.port_game.canvas.tag_bind(self.area, "<ButtonRelease-1>", self.on_drag_stop)

    def on_drag_start(self, event):
        if isinstance(self.parent, Lorry):
            if self.parent.diff_to_halt > 5:
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

        if isinstance(self.parent, Lorry):
            dx = max(dx, self.parent.coords[0] - self.coords[0])
            dy = min(dy, self.parent.coords[3] - self.coords[3])
            dy = max(dy, self.parent.coords[1] - self.coords[1])
            if not overlap(self.coords, self.parent.coords):
                self.parent = self.port_game.port
        elif isinstance(self.parent, Port):
            # dont go east of port area
            dx = max(dx, self.port_game.land_port_edge - self.coords[0])

        while self.is_collision(dx, dy):
            if dx > 0 and not self.is_collision(1, 0):
                self.port_game.canvas.move(self.area, 1, 0)
                dx -= 1
            elif dx < 0 and not self.is_collision(-1, 0):
                self.port_game.canvas.move(self.area, -1, 0)
                dx += 1
            elif dy > 0 and not self.is_collision(0, 1):
                self.port_game.canvas.move(self.area, 0, 1)
                dy -= 1
            elif dy < 0 and not self.is_collision(0, -1):
                self.port_game.canvas.move(self.area, 0, -1)
                dy += 1
            else:
                return None

        print('here')
        self.port_game.canvas.move(self.area, dx, dy)

    def on_drag_stop(self, event=None):

        if isinstance(self.parent, Port):
            if self.will_sink():
                self.sink()

            # TODO: if now completely in ship that is accepting, parent = ship
        elif isinstance(self.parent, Ship):
            pass
            # TODO: if now not completely in ship, parent = port

    def will_sink(self):
        supporting_rectangles = [self.port_game.canvas.coords(self.port_game.port.area)] + \
                                [i.coords for i in self.port_game.ship_queue.values()]
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

    from shapely.geometry import Polygon, box

    def is_collision(self, dx, dy):

        def get_canvas_coords(item_id):
            coords = self.port_game.canvas.coords(item_id)
            if len(coords) == 4:
                return [(coords[0], coords[1]), (coords[2], coords[1]), (coords[2], coords[3]), (coords[0], coords[3])]
            else:
                return []

        def convex_hull_overlaps_any_rectangle(points):
            polygon = Polygon(points)

            for cargo_item in self.port_game.cargo.values():
                if cargo_item.id == self.id:
                    continue
                rect_coords = get_canvas_coords(cargo_item.area)
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

    def sink(self):
        c = self.coords
        if (c[2] - c[0]) > 2:
            self.port_game.canvas.coords(self.area, c[0] + 2, c[1], c[2], c[3])
            self.port_game.canvas.after(100, self.sink)
        else:
            self.port_game.canvas.delete(self.area)
            self.port_game.cargo.pop(self.id)

class Vehicle:
    def __init__(self, id, port_game, width, length, color):
        self.id = id
        self.port_game = port_game
        self.width = width
        self.length = length
        self.color = color
        self.area = None
        self.ready_to_leave = None
        self.halt_point = None

    @property
    def my_cargo(self):
        return {key: value for key, value in self.port_game.cargo.items() if
                value.parent.id == self.id and type(value.parent) == type(self)}

    @property
    def center_h(self):
        return np.mean([self.coords[3], self.coords[1]])

    @property
    def coords(self):
        return self.port_game.canvas.coords(self.area)

    @property
    def diff_to_halt(self):
        return self.center_h - self.halt_point

    def move_vehicle(self, s_or_l):
        queue = self.port_game.lorry_queue if s_or_l == "l" else self.port_game.ship_queue
        if (self.id - 1) in queue:
            diff_to_vehicle = self.coords[1] - queue[self.id - 1].coords[3]
            diff_to_next = min(diff_to_vehicle, self.diff_to_halt)
        else:
            diff_to_next = self.diff_to_halt

        if diff_to_next > 5:
            speed = max(2, min(5, diff_to_next / 10))
            self.port_game.canvas.move(self.area, 0, -speed)
            for cargo_item in self.my_cargo.values():
                self.port_game.canvas.move(cargo_item.area, 0, -speed)
        if self.diff_to_halt <= 5:
            speed = max(2, min(5, -self.diff_to_halt / 10))
            if self.ready_to_leave:
                self.port_game.canvas.move(self.area, 0, -speed)


class Lorry(Vehicle):
    def __init__(self, id, port_game, width, length):
        super().__init__(id, port_game, width, length, 'darkgrey')

        self.ready_to_leave = False
        self.dist_to_port = 5
        self.halt_point = self.port_game.win_h / 2

        coords = (self.port_game.land_port_edge - self.dist_to_port - width,
                  self.port_game.win_h,
                  self.port_game.land_port_edge - self.dist_to_port,
                  self.port_game.win_h + length)

        self.area = self.port_game.canvas.create_rectangle(coords, fill=self.color)
        self.add_cargo([1, 2, 3])

    def add_cargo(self, types):
        packer = newPacker(mode=PackingMode.Online, rotation=True)
        packer.add_bin(self.width, self.length)

        for rect_id, itype in enumerate(types):
            packer.add_rect(Cargo.types[itype]["width"], Cargo.types[itype]["height"], rect_id)
        rect_list = packer.rect_list()

        for rect_id, itype in enumerate(types):
            if not any([rect_id == i[5] for i in rect_list]):
                continue
            cargo_id = self.port_game.cargo_id
            rect = rect_list[[i[5] for i in rect_list].index(rect_id)]
            cargo_coords = (rect[1] + self.coords[0],
                            rect[2] + self.coords[1],
                            rect[1] + rect[3] + self.coords[0],
                            rect[2] + rect[4] + self.coords[1])
            self.port_game.cargo[cargo_id] = Cargo(cargo_id, self, self.port_game, cargo_coords, itype)
            self.port_game.cargo_id += 1

    def move(self):
        self.ready_to_leave = len(self.my_cargo) == 0
        super().move_vehicle("l")


class Ship(Vehicle):
    def __init__(self, id, port_game, width, length):
        super().__init__(id, port_game, width, length, 'red')
        self.ready_to_leave = False
        self.dist_to_port = 5
        self.halt_point = self.port_game.win_h / 2
        self.area = self.port_game.canvas.create_rectangle(self.port_game.port_water_edge + self.dist_to_port,
                                                           self.port_game.win_h,
                                                           self.port_game.port_water_edge + self.dist_to_port + width,
                                                           self.port_game.win_h + length, fill=self.color)

    def move(self):
        # TODO: implement this
        no_hanging_cargo = True
        time_is_up = False
        user_clicked_go = False
        self.ready_to_leave = no_hanging_cargo and (time_is_up or user_clicked_go)
        super().move_vehicle("s")


class Port:
    def __init__(self, port_game):
        self.id = 1
        self.area = port_game.canvas.create_rectangle(port_game.land_port_edge, 0, port_game.port_water_edge,
                                                      port_game.win_h, fill="gray")


class PortGame:
    win_h = 800
    win_w = 1200
    land_port_edge = 900
    port_water_edge = 1000
    lorry_id = 0
    ship_id = 0
    cargo_id = 0

    def __init__(self, root):
        self.game_running = True

        self.root = root
        self.root.title("Port Management Game")

        self.canvas = tk.Canvas(root, width=self.win_w, height=self.win_h)
        self.canvas.pack()

        self.land = self.canvas.create_rectangle(0, 0, self.land_port_edge, self.win_h, fill="#70d476")
        self.port = Port(self)
        self.water = self.canvas.create_rectangle(self.port_water_edge, 0, self.win_w, self.win_h, fill="#365ab4")

        self.lorry_queue = {}
        self.ship_queue = {}
        self.cargo = {}

        self.create_lorry()
        self.create_ship()

        self.update_game()

    def game_over(self, message):
        pass
        # print(message)
        # self.game_running = False

    def create_lorry(self):
        if not self.game_running:
            return
        width = 40
        length = 60
        if (self.lorry_id - 1) in self.lorry_queue:
            if self.lorry_queue[self.lorry_id - 1].coords[3] > self.win_h:
                self.game_over("Lorry queue is full")
        self.lorry_queue[self.lorry_id] = Lorry(self.lorry_id, self, width, length)
        self.lorry_id += 1
        self.root.after(3000, self.create_lorry)

    def create_ship(self):
        if not self.game_running:
            return
        width = 40
        length = 80
        if (self.ship_id - 1) in self.ship_queue:
            if self.ship_queue[self.ship_id - 1].coords[3] > self.win_h:
                self.game_over("Ship queue is full")
        self.ship_queue[self.ship_id] = Ship(self.ship_id, self, width, length)
        self.ship_id += 1
        self.root.after(5000, self.create_ship)

    def update_game(self):
        if not self.game_running:
            return
        for lorry in self.lorry_queue.values():
            lorry.move()

        for ship in self.ship_queue.values():
            ship.move()

        self.root.after(50, self.update_game)


if __name__ == "__main__":
    root = tk.Tk()
    game = PortGame(root)
    root.mainloop()

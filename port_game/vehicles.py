import random

import numpy as np
from rectpack import PackingMode, newPacker

import port_game.Cargo
from port_game import Cargo


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
        self.go_btn = None

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
    def tail(self):
        return self.coords[3]

    @property
    def tip(self):
        go_c = self.port_game.canvas.coords(self.go_btn)
        return go_c[5]

    @property
    def diff_to_halt(self):
        return self.center_h - self.halt_point


    def go(self, event=None):
        if self.diff_to_halt < 10:
            self.ready_to_leave = True

    def move_vehicle(self, s_or_l):
        speed = 0

        queue = self.port_game.lorry_queue if s_or_l == "l" else self.port_game.ship_queue
        if (self.id - 1) in queue:
            diff_to_vehicle = self.tip - queue[self.id - 1].tail
            diff_to_next = min(diff_to_vehicle, self.diff_to_halt)
        else:
            diff_to_next = self.diff_to_halt

        if diff_to_next > 5:
            speed = max(2, min(5, diff_to_next / 10))
        if self.diff_to_halt <= 5:
            if self.ready_to_leave:
                speed = max(2, min(5, -self.diff_to_halt / 10))
            else:
                speed = 0
        self.port_game.canvas.move(self.area, 0, -speed)
        self.port_game.canvas.move(self.go_btn, 0, -speed)
        for cargo_item in self.my_cargo.values():
            self.port_game.canvas.move(cargo_item.area, 0, -speed)
        return speed

    def init_go_btn(self, length, color):
        self.go_btn = self.port_game.canvas.create_polygon([
            self.coords[0], self.coords[1],
            self.coords[2], self.coords[1],
            (self.coords[2] - self.coords[0]) / 2 + self.coords[0], self.coords[1] - length
        ], fill=color)


class Ship(Vehicle):
    def __init__(self, id, port_game, width, length, wishlist):
        super().__init__(id, port_game, width, length, 'red')
        self.wishlist = wishlist
        self.ready_to_leave = False
        self.dist_to_port = 5
        self.halt_point = self.port_game.win_h / 2
        self.area = self.port_game.canvas.create_rectangle(self.port_game.port_water_edge + self.dist_to_port,
                                                           self.port_game.win_h,
                                                           self.port_game.port_water_edge + self.dist_to_port + width,
                                                           self.port_game.win_h + length,
                                                           fill=self.color)

        # wishlist visuals
        self.wish_rect= []
        wish_rect_width = 10
        for idx, iwish in enumerate(self.wishlist):
            self.wish_rect.append(self.port_game.canvas.create_rectangle(
                self.coords[2] + 2 + idx * wish_rect_width,
                self.coords[1] + wish_rect_width,
                self.coords[2] + 2 + idx * wish_rect_width + wish_rect_width,
                self.coords[1],
                fill=Cargo.Cargo.types[iwish]["color"]
            ))

        super().init_go_btn(20, "#16d91c")
        self.port_game.canvas.tag_bind(self.go_btn, "<ButtonPress-1>", self.go)


    def move(self):
        # TODO: implement not leaving if hanging cargo? Time is up? Can I prevent leaving if time is up if I hang cargo?
        no_hanging_cargo = True
        time_is_up = False

        speed = super().move_vehicle("s")
        for i in self.wish_rect:
            self.port_game.canvas.move(i, 0, -speed)


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
        self.add_cargo()
        super().init_go_btn(15, "dark blue")
        self.port_game.canvas.tag_bind(self.go_btn, "<ButtonPress-1>", self.go)

    def add_cargo(self):
        if random.choice([True, False]):
            # one-type-lorry:
            types = [port_game.Cargo.Cargo.select_type_based_on_freq()] * 10
        else:
            # mixed lorry
            types = []
            for i in range(10):
                types.append(port_game.Cargo.Cargo.select_type_based_on_freq())

        packer = newPacker(mode=PackingMode.Online, rotation=True)
        packer.add_bin(self.width, self.length)

        for rect_id, itype in enumerate(types):
            packer.add_rect(port_game.Cargo.Cargo.types[itype]["width"], port_game.Cargo.Cargo.types[itype]["height"], rect_id)
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
            self.port_game.cargo[cargo_id] = port_game.Cargo.Cargo(cargo_id, self, self.port_game, cargo_coords, itype)
            self.port_game.cargo_id += 1

    def move(self):
        if len(self.my_cargo) == 0:
            self.ready_to_leave = True
        super().move_vehicle("l")

import random

import numpy as np
from rectpack import PackingMode, newPacker

import port_game.Cargo
from port_game import Cargo
from port_game.utils import overlap


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

    @property
    def in_loading_position(self):
        return abs(self.diff_to_halt) < 10

    def go(self, event=None):
        if self.in_loading_position:
            self.ready_to_leave = True

    def move_vehicle(self, s_or_l):
        speed = 0

        queue = self.port_game.lorry_queue if s_or_l == "l" else self.port_game.ship_queue
        if (self.id - 1) in queue:
            diff_to_vehicle = self.tip - queue[self.id - 1].tail
            diff_to_next = min(diff_to_vehicle, self.diff_to_halt)
        else:
            diff_to_next = self.diff_to_halt

        if diff_to_next > 5:  # in vehicle queue
            speed = max(2, min(5, diff_to_next / 10))
        if self.diff_to_halt < 5:  # in loading position or leaving
            if self.ready_to_leave:  # leaving
                speed = max(2, min(5, -self.diff_to_halt / 10))
                for cargo_item in self.my_cargo.values():
                    if s_or_l == "l" and cargo_item.owner == "lorry":
                        cargo_item.buy(0.5)  # penalty for leaving cargo
                    elif s_or_l == "s" and cargo_item.owner == "me":
                        cargo_item.sell(1.2)  # sell for profit
            else:  # staying
                speed = 0
        self.port_game.canvas.move(self.area, 0, -speed)
        self.port_game.canvas.move(self.go_btn, 0, -speed)
        for cargo_item in self.my_cargo.values():
            cargo_item.move(0, -speed)
            if s_or_l == "s" and cargo_item.will_sink() and speed != 0:
                cargo_item.sink()
                cargo_item.buy(2)

        # sink cargo that overlaps with moving ship if cargo's parent is not the ship itself
        if s_or_l == "s":
            if not self.in_loading_position:
                for cargo_item in self.port_game.port.my_cargo.values():
                    if overlap(cargo_item.coords, self.coords):
                        cargo_item.sink()

        # destroy vehicle
        if abs(self.tail < 5):
            if s_or_l == "s":
                self.port_game.ship_delete_queue.append(self.id)
            else:
                self.port_game.lorry_delete_queue.append(self.id)

        return speed

    def destroy(self):
        self.port_game.canvas.delete(self.area)
        self.port_game.canvas.delete(self.go_btn)
        for id, icargo in self.my_cargo.items():
            self.port_game.canvas.delete(icargo.area)
            self.port_game.cargo.pop(id)

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

    def destroy(self):
        for iwish in self.wish_rect:
            self.port_game.canvas.delete(iwish)
        super().destroy()
        self.port_game.ship_queue.pop(self.id)

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

    def destroy(self):
        super().destroy()
        self.port_game.lorry_queue.pop(self.id)
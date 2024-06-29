import random

import numpy as np
from rectpack import PackingMode, newPacker

from port_game.Cargo import Cargo


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

    def add_cargo(self):
        if random.choice([True, False]):
            # one-type-lorry:
            types = [Cargo.select_type_based_on_freq(random.random())] * 10
        else:
            # mixed lorry
            types = []
            for i in range(10):
                types.append(Cargo.select_type_based_on_freq(random.random()))

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

import random
import tkinter as tk

import port_game.Cargo
from port_game.vehicles import Lorry, Ship
from port_game.Port import Port


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

        self.money = 1000
        self.money_text = self.canvas.create_text(50, 50, text=f"{self.money:.2f} $", font=("mono", 16), fill="white",
                                                  anchor="nw")

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
                return None
        self.lorry_queue[self.lorry_id] = Lorry(self.lorry_id, self, width, length)
        self.lorry_id += 1
        self.root.after(3000, self.create_lorry)

    def create_ship(self):
        def random_wishlist():
            rand_type = random.choice([1, 2, 3, 4])  # ship types: accept one type of cargo, two, three, or any
            out = []
            if rand_type >= 1:
                out.append(port_game.Cargo.Cargo.select_type_based_on_freq())
            if rand_type >= 2:
                out.append(port_game.Cargo.Cargo.select_type_based_on_freq(exclude=out))
            if rand_type >= 3:
                out.append(port_game.Cargo.Cargo.select_type_based_on_freq(exclude=out))
            if rand_type == 4:
                out = [i for i in port_game.Cargo.Cargo.types]
            return sorted(out)

        if not self.game_running:
            return
        width = 40
        length = 80
        if (self.ship_id - 1) in self.ship_queue:
            if self.ship_queue[self.ship_id - 1].coords[3] > self.win_h:
                self.game_over("Ship queue is full")
                return None

        wishlist = random_wishlist()

        self.ship_queue[self.ship_id] = Ship(self.ship_id, self, width, length, wishlist)
        self.ship_id += 1
        self.root.after(10000, self.create_ship)

    def update_game(self):
        if not self.game_running:
            return
        for lorry in self.lorry_queue.values():
            lorry.move()

        for ship in self.ship_queue.values():
            ship.move()

        self.canvas.itemconfig(self.money_text, text=f"{self.money:.2f} $")

        self.root.after(50, self.update_game)

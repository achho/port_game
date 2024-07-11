from shapely import box


class Port:
    def __init__(self, port_game):
        self.id = 1
        self.port_game = port_game
        self.area = port_game.canvas.create_rectangle(port_game.land_port_edge, 0, port_game.port_water_edge,
                                                      port_game.win_h, fill="gray")

    @property
    def my_cargo(self):
        return {key: value for key, value in self.port_game.cargo.items() if type(value.parent) == type(self)}

    @property
    def box(self):
        return box(*self.port_game.canvas.coords(self.area))

    @property
    def box_bounds(self):
        return self.box.bounds
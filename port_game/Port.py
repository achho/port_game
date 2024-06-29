
class Port:
    def __init__(self, port_game):
        self.id = 1
        self.area = port_game.canvas.create_rectangle(port_game.land_port_edge, 0, port_game.port_water_edge,
                                                      port_game.win_h, fill="gray")

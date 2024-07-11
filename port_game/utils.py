from shapely import MultiPoint, Point, Polygon


def compute_convex_hull(points):
    multipoint = MultiPoint(points)
    convex_hull_polygon = multipoint.convex_hull
    return list(convex_hull_polygon.exterior.coords)


def point_inside_convex_hull(point, hull):
    point = Point(point)
    polygon = Polygon(hull)
    return polygon.contains(point)

def do_overlap(box1, box2):
    return box1.intersection(box2).area > 0


def init_text_animation(animation, port_game, x, y, text, color):
    if animation:
        port_game.canvas.delete(animation)

    animation = port_game.canvas.create_text(x, y,
                                       text=text,
                                       fill=color,
                                       font=("mono", 16),
                                       anchor="sw")
    port_game.root.after(500, lambda: lessen_text_animation(animation, port_game))
    return animation

def lessen_text_animation(animation, port_game):
    if not animation:
        return None  # could be when init was called again but lessen has been scheduled
    font = port_game.canvas.itemcget(animation, "font")
    if not font:
        return None  # could be when init was called again but lessen has been scheduled
    font_size = font.split()[1]
    new_font = (font[0], int(font_size) - 1)
    if new_font[1] <= 5:
        port_game.canvas.delete(animation)
        return None
    port_game.canvas.itemconfig(animation, font=new_font)
    port_game.root.after(150, lambda: lessen_text_animation(animation, port_game))

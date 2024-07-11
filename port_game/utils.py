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

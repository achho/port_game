from shapely import MultiPoint, box, Point, Polygon


def compute_convex_hull(points):
    multipoint = MultiPoint(points)
    convex_hull_polygon = multipoint.convex_hull
    return list(convex_hull_polygon.exterior.coords)


def point_inside_convex_hull(point, hull):
    point = Point(point)
    polygon = Polygon(hull)
    return polygon.contains(point)

def overlap(rect1, rect2):
    return box(*rect1).intersection(box(*rect2)).area > 0


def intersection(rect1, rect2):
    # Calculate the intersection of the two rectangles
    intersection = box(*rect1).intersection(box(*rect2))

    # Check if the intersection area is greater than 0
    if intersection.area > 0:
        return intersection.bounds
    else:
        return None

def rect_size(x0, y0, x1, y1):
    return box(x0, y0, x1, y1).area
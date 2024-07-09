from shapely import MultiPoint


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

def rect_size(x0, y0, x1, y1):
    return abs(x1 - x0) * abs(y1 - y0)
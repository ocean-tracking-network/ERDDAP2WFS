import math
import sys

import Geometry
import geojson
import s2sphere

DBL_EPSILON = sys.float_info.epsilon


def compute_bounds(geometry: geojson.geometry.Geometry):
    feature = s2sphere.LatLngRect()
    ret = feature

    if geometry is None:
        ret = feature

    elif isinstance(geometry, geojson.geometry.Point):
        if len(geometry['coordinates']) >= 2:
            feature = feature.from_point(s2sphere.LatLng.from_degrees(geometry['coordinates'][1],
                                                                      geometry['coordinates'][0]))

    elif isinstance(geometry, geojson.geometry.MultiPoint):
        for point in geometry['coordinates']:
            if len(point) >= 2:
                feature = feature.from_point(s2sphere.LatLng.from_degrees(point[1], point[0]))

    elif isinstance(geometry, geojson.geometry.LineString):
        ret = compute_line_bounds(geometry['coordinates'])

    elif isinstance(geometry, geojson.geometry.MultiLineString):
        for line in geometry['coordinates']:
            feature = feature.union((compute_line_bounds(line)))

    elif isinstance(geometry, geojson.geometry.Polygon):
        for ring in geometry['coordinates']:
            feature = feature.union(compute_line_bounds(ring))

        ret = expand_for_sub_regions(feature)

    elif isinstance(geometry, geojson.geometry.MultiPolygon):
        for poly in geometry['coordinates']:
            for ring in poly:
                feature = feature.union(compute_line_bounds(ring))

        ret = expand_for_sub_regions(feature)

    elif isinstance(geometry, geojson.geometry.GeometryCollection):
        for geometry_object in geometry['Geometries']:
            feature = feature.union(compute_bounds(geometry_object))

    return ret


def compute_line_bounds(line):
    rect = s2sphere.LatLngRect()
    for point in line:
        if len(point) >= 2:
            rect = rect.from_point(s2sphere.LatLng.from_degrees(point[1], point[0]))
    return rect


def encode_bbox(rect: s2sphere.LatLngRect):
    if rect.is_empty():
        return None

    rect = [rect.lo().lng().degrees,
            rect.lo().lat().degrees,
            rect.hi().lng().degrees,
            rect.hi().lat().degrees]
    return rect[0:4]


def get_tile_bounds(zoom: int, x: int, y: int):
    return s2sphere.LatLngRect.from_point_pair(unproject_web_mercator(zoom, float(x), float(y)),
                                               unproject_web_mercator(zoom, float(x + 1), float(y + 1)))


def project_web_mercator(p: s2sphere.LatLng):
    siny = math.sin(p.lat().radians)
    siny = min(max(siny, -0.9999), 0.9999)
    x = 256 * (0.5 + p.lng().degrees / 360)
    y = 256 * (0.5 - math.log((1 + siny) / (1 - siny)) / (4 * math.pi))

    return Geometry.Point(x=x, y=y)


def unproject_web_mercator(zoom: int, x: float, y: float):
    n = math.pi - 2.0 * math.pi * y / 2 ** (float(zoom))
    lat = 180.0 / math.pi * math.atan(0.5 * (math.exp(n) - math.exp(-n)))
    lng = x / 2 ** (float(zoom)) * 360.0 - 180.0

    return s2sphere.LatLng.from_degrees(lat, lng)


# Taken from the GoLang S2 library -> https://github.com/golang/geo/blob/master/s2/rect_bounder.go#L221
def expand_for_sub_regions(rect: s2sphere.LatLngRect):
    # if rect.is_empty():
    #     return rect
    #
    # lng_gap = max(0, math.pi-rect.lng().get_length()-2.5*DBL_EPSILON)
    #
    # min_abs_lat = max(rect.lat_lo().radians, -rect.lat_hi().radians)
    #
    # lat_gap_south = math.pi/2 + rect.lat_lo().radians
    # lat_gap_north = math.pi/2 - rect.lat_hi().radians
    #
    # if min_abs_lat >= 0:
    #     if 2*min_abs_lat+lng_gap < 1.345e-15:
    #         return rect
    # elif lng_gap >= math.pi/2:
    #     if lat_gap_south+lat_gap_north < 1.687e-15:
    #         return rect
    # else:
    #     if max(lat_gap_south, lat_gap_north)*lng_gap < 1.765e-15:
    #         return rect
    #
    # lat_expansion = 9*DBL_EPSILON
    # lng_expansion = 0.1
    #
    # if lng_gap <= 0:
    #     lng_expansion = math.pi
    #
    # return polar_closure(rect.expanded(s2sphere.LatLng(lat=s2sphere.Angle(lat_expansion).radians,
    #                                                    lng=s2sphere.Angle(lng_expansion).radians)))

    return rect


def polar_closure(rect: s2sphere.LatLngRect):
    if rect.lat_lo().radians == -math.pi / 2 or rect.lat_hi().radians == math.pi / 2:
        return s2sphere.LatLngRect(rect.lat(), s2sphere.SphereInterval.full())
    return rect

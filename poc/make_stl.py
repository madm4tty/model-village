#!/usr/bin/env python3
"""Proof of concept: a point in England -> EA LIDAR 1m grid -> watertight STL.

Example (York Minster, 100m square, 170mm wide print):
    python make_stl.py --lat 53.9623 --lon -1.0819 --size 100 --out minster.stl
"""
import argparse
import sys

import numpy as np
import rasterio
import requests
import trimesh
from pyproj import Transformer

EA = "https://environment.data.gov.uk/spatialdata"
PRODUCTS = {
    # First return DSM: top of trees and roofs. Usually the best looking print.
    "dsm": (f"{EA}/lidar-composite-digital-surface-model-first-return-dsm-1m/wcs",
            "df4e3ec3-315e-48aa-aaaf-b5ae74d7b2bb__Lidar_Composite_Elevation_FZ_DSM_1m"),
    # Last return DSM: laser partly penetrates trees, so canopy looks ragged.
    "dsm-last": (f"{EA}/lidar-composite-digital-surface-model-last-return-dsm-1m/wcs",
                 "9ba4d5ac-d596-445a-9056-dae3ddec0178__Lidar_Composite_Elevation_LZ_DSM_1m"),
    # DTM: bare earth, buildings and trees removed.
    "dtm": (f"{EA}/lidar-composite-digital-terrain-model-dtm-1m/wcs",
            "13787b9a-26a4-4775-8523-806d13af58fc__Lidar_Composite_Elevation_DTM_1m"),
}
BED_MM = 180.0


def bng_square(lat, lon, size_m):
    """Square in British National Grid (EPSG:27700) centred on a WGS84 point, snapped to 1m."""
    to_bng = Transformer.from_crs("EPSG:4326", "EPSG:27700", always_xy=True)
    e, n = to_bng.transform(lon, lat)
    half = size_m / 2
    return round(e - half), round(n - half), round(e + half), round(n + half)


def fetch_heights(product, e0, n0, e1, n1):
    """Ask the Environment Agency WCS for just this box, as a GeoTIFF of heights in metres."""
    url, coverage = PRODUCTS[product]
    params = [
        ("service", "WCS"), ("version", "2.0.1"), ("request", "GetCoverage"),
        ("CoverageId", coverage), ("format", "image/tiff"),
        ("subset", f"E({e0},{e1})"), ("subset", f"N({n0},{n1})"),
        ("SUBSETTINGCRS", "http://www.opengis.net/def/crs/EPSG/0/27700"),
    ]
    r = requests.get(url, params=params, timeout=120)
    r.raise_for_status()
    if not r.headers.get("content-type", "").startswith("image/tiff"):
        sys.exit(f"WCS did not return a GeoTIFF:\n{r.text[:500]}")
    with rasterio.MemoryFile(r.content) as mem, mem.open() as ds:
        heights = ds.read(1, masked=True)
        # Wholly outside the survey, the WCS returns all zeros with no nodata value set.
        no_coverage = ds.nodata is None and not heights.any()
    if no_coverage or heights.mask.all():
        sys.exit("No LIDAR coverage for this area.")
    if heights.mask.any():
        # Gaps are mostly sea or water, so flatten them to the lowest real height.
        print(f"Filling {int(heights.mask.sum())} cells with no data")
    return heights.filled(heights.min()).astype("float64")


def grid_to_solid(top_mm, px_mm):
    """Turn a 2D grid of top heights (mm) into a closed solid: surface, four walls, flat base at z=0."""
    rows, cols = top_mm.shape
    xs = np.arange(cols) * px_mm
    ys = (rows - 1 - np.arange(rows)) * px_mm  # row 0 is the northern edge
    x, y = np.meshgrid(xs, ys)
    top = np.column_stack([x.ravel(), y.ravel(), top_mm.ravel()])
    idx = np.arange(rows * cols).reshape(rows, cols)

    # Top surface: two triangles per grid cell, wound anticlockwise seen from above.
    nw, ne, sw, se = idx[:-1, :-1], idx[:-1, 1:], idx[1:, :-1], idx[1:, 1:]
    faces = [np.column_stack([nw.ravel(), sw.ravel(), se.ravel()]),
             np.column_stack([nw.ravel(), se.ravel(), ne.ravel()])]

    # Edge vertices in anticlockwise order seen from above: west, south, east, north.
    ring = np.concatenate([idx[:, 0], idx[-1, 1:], idx[-2::-1, -1], idx[0, -2:0:-1]])
    n_top = len(top)
    bottom = top[ring].copy()
    bottom[:, 2] = 0.0
    centre = [[xs[-1] / 2, ys[0] / 2, 0.0]]
    vertices = np.vstack([top, bottom, centre])

    k = np.arange(len(ring))
    k1 = np.roll(k, -1)
    t, t1 = ring[k], ring[k1]
    b, b1 = n_top + k, n_top + k1
    c = np.full_like(k, len(vertices) - 1)
    faces += [np.column_stack([t, b, b1]), np.column_stack([t, b1, t1]),  # walls
              np.column_stack([c, b1, b])]                               # base, facing down
    return trimesh.Trimesh(vertices, np.vstack(faces), process=True)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--lat", type=float, required=True)
    p.add_argument("--lon", type=float, required=True)
    p.add_argument("--size", type=float, default=100, help="side of the square in metres")
    p.add_argument("--product", choices=PRODUCTS, default="dsm")
    p.add_argument("--width", type=float, default=170, help="printed width in mm")
    p.add_argument("--exaggeration", type=float, default=1.0, help="vertical exaggeration")
    p.add_argument("--base", type=float, default=3.0, help="base thickness below the lowest point, mm")
    p.add_argument("--out", default="model.stl")
    a = p.parse_args()

    e0, n0, e1, n1 = bng_square(a.lat, a.lon, a.size)
    print(f"BNG box E {e0}-{e1}, N {n0}-{n1}")
    h = fetch_heights(a.product, e0, n0, e1, n1)
    print(f"Grid {h.shape[1]}x{h.shape[0]} cells, heights {h.min():.2f} to {h.max():.2f} m")

    mm_per_m = a.width / (h.shape[1] - 1)
    top_mm = a.base + (h - h.min()) * mm_per_m * a.exaggeration
    mesh = grid_to_solid(top_mm, mm_per_m)

    print(f"Scale 1:{1000 / mm_per_m:.0f}, one 1m cell = {mm_per_m:.2f} mm on the print")
    print(f"Model {mesh.extents[0]:.1f} x {mesh.extents[1]:.1f} x {mesh.extents[2]:.1f} mm, "
          f"{len(mesh.faces):,} triangles")
    print(f"Watertight: {mesh.is_watertight}, consistent winding: {mesh.is_winding_consistent}, "
          f"volume {mesh.volume / 1000:.1f} cm3")
    if max(mesh.extents) > BED_MM:
        print(f"WARNING: larger than the A1 mini's {BED_MM:.0f}mm build volume")
    mesh.export(a.out)
    print(f"Wrote {a.out}")


if __name__ == "__main__":
    main()

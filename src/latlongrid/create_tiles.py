import ogr
import os
import numpy as np
from fastkml import kml, styles, geometry
from shapely.geometry import Polygon

def write_shp_tiles(out_filepath, tiles):
    dest_srs = ogr.osr.SpatialReference()
    dest_srs.ImportFromEPSG(4326)
    driver = ogr.GetDriverByName("ESRI Shapefile")
    ds_out = driver.CreateDataSource(out_filepath)
    layer_out = ds_out.CreateLayer(os.path.basename(out_filepath).replace('.shp', ''), srs=dest_srs,
                                   geom_type=ogr.wkbPolygon)

    for tile_counter in range(0, tiles.shape[2]):
        fdef_out = layer_out.GetLayerDefn()
        feat = ogr.Feature(fdef_out)
        points = tiles[:, :, tile_counter]
        points = np.concatenate((points, np.array([points[0, :]])), axis=0)
        ring = ogr.Geometry(ogr.wkbLinearRing)
        for point in points:
            ring.AddPoint(float(point[0]), float(point[1]))
        poly = ogr.Geometry(ogr.wkbPolygon)
        poly.AddGeometry(ring)
        feat.SetGeometry(poly)
        layer_out.CreateFeature(feat)
        fdef_out = None
        feat = None

    ds_out = None


def write_kml_tiles(out_filepath, tiles, doc_name="doc name", doc_desc="doc description"):
    k = kml.KML()
    ns = '{http://www.opengis.net/kml/2.2}'
    d = kml.Document(ns, 'docid', doc_name, doc_desc)
    k.append(d)
    p_style = styles.PolyStyle(ns, 'id', fill=0)
    l_style = styles.LineStyle(ns, 'id', color="FF0000FF")
    sty = kml.Style(ns, 'id', styles=[p_style, l_style])

    for tile_counter in range(0, tiles.shape[2]):
        points = tiles[:, :, tile_counter]
        points = np.concatenate((points, np.array([points[0, :]])), axis=0)
        polygon_points = []
        for point in points:
            polygon_points.append((float(point[0]), float(point[1])))
        f = kml.Folder(ns, 'fid', 'f name', 'f description')
        d.append(f)
        p = kml.Placemark(ns, 'id', 'name', 'description')
        geom = geometry.Geometry()
        #geom.altitude_mode = 'clampToGround'
        geom.geometry = Polygon(polygon_points)
        p.geometry = geom
        p.append_style(sty)
        f.append(p)

    with open(out_filepath, 'w') as filehandle:
        filehandle.write(k.to_string(prettyprint=True))


# TODO: refactor
def tiling(bbox, dims):
    x_tl = bbox[0]
    y_tl = bbox[3]
    x_br = bbox[2]
    y_br = bbox[1]
    tile_nums = dims[0]*dims[1]
    tiles = np.zeros((4, 2, tile_nums))
    width = x_br - x_tl
    height = y_tl - y_br
    step_x = float(width) / dims[0]
    step_y = float(height) / dims[1]
    current_x = x_tl
    current_y = y_tl
    tile_counter = 0
    while current_y >= (y_br + step_y):
        while current_x <= (x_br - step_x):
            tile_curr = np.zeros((4, 2))
            tile_curr[0, :] = np.array([current_x, current_y])
            tile_curr[1, :] = np.array([current_x + step_x, current_y])
            tile_curr[2, :] = np.array([current_x + step_x, current_y - step_y])
            tile_curr[3, :] = np.array([current_x, current_y - step_y])
            tiles[:, :, tile_counter] = tile_curr
            current_x += step_x
            tile_counter += 1
        current_y -= step_y
        current_x = x_tl

    return tiles


def main():
    dirname = r"D:\work\data\LatLonGrid\tiles"
    tile_size = 36
    bbox = [-180, -90, 180, 90]
    dims = (int(360./tile_size), int(180./tile_size))
    tiles = tiling(bbox, dims)

    out_filepath_shp = os.path.join(dirname, "LatLon_T{}.shp".format(tile_size))
    write_shp_tiles(out_filepath_shp, tiles)

    out_filepath_kml = os.path.join(dirname, "LatLon_T{}.kml".format(tile_size))
    doc_name = "LatLon_T{}".format(tile_size)
    write_kml_tiles(out_filepath_kml, tiles, doc_name=doc_name, doc_desc='')

if __name__ == '__main__':
    main()
import ogr
import os
import numpy as np
from fastkml import kml, styles, geometry
from shapely.geometry import Polygon


def write_shp_tiles(out_filepath, tiles, land_mask_filepath):
    dest_srs = ogr.osr.SpatialReference()
    dest_srs.ImportFromEPSG(4326)
    driver = ogr.GetDriverByName("ESRI Shapefile")
    ds_out = driver.CreateDataSource(out_filepath)
    layer_out = ds_out.CreateLayer(os.path.basename(out_filepath).replace('.shp', ''), srs=dest_srs,
                                   geom_type=ogr.wkbPolygon)

    # create metadata fields
    new_field = ogr.FieldDefn('SHORTNAME', ogr.OFTString)
    layer_out.CreateField(new_field)
    new_field = ogr.FieldDefn('GRID', ogr.OFTString)
    layer_out.CreateField(new_field)
    new_field = ogr.FieldDefn('VERSION', ogr.OFTString)
    layer_out.CreateField(new_field)
    new_field = ogr.FieldDefn('ZONE', ogr.OFTString)
    layer_out.CreateField(new_field)
    new_field = ogr.FieldDefn('TILE', ogr.OFTString)
    layer_out.CreateField(new_field)
    new_field = ogr.FieldDefn('EXTENT', ogr.OFTInteger)
    layer_out.CreateField(new_field)
    new_field = ogr.FieldDefn('LLLON', ogr.OFTInteger)
    layer_out.CreateField(new_field)
    new_field = ogr.FieldDefn('LLLAT', ogr.OFTInteger)
    layer_out.CreateField(new_field)
    new_field = ogr.FieldDefn('COVERSLAND', ogr.OFTInteger)
    layer_out.CreateField(new_field)

    # read SHP land mask
    ds_mask = driver.Open(land_mask_filepath, update=False)
    layer_mask = ds_mask.GetLayer()

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
        coversland = False
        for feat_mask in layer_mask:
            if feat.geometry().Intersects(feat_mask.geometry()):
                coversland = True
                break
        layer_mask.ResetReading()
        ll_lon = int(np.min(points[:, 0]))
        ll_lat = int(np.min(points[:, 1]))
        extent = int(np.max(points[:, 0]) - np.min(points[:, 0]))
        tilename = "{:03d}_{:03d}".format(int(np.min(points[:, 0])) + 180, int(np.min(points[:, 1])) + 90)
        feat.SetField('SHORTNAME', 'LLG GL')
        feat.SetField('GRID', 'LatLon Grid')
        feat.SetField('VERSION', 'V1')
        feat.SetField('ZONE', 'Globe')
        feat.SetField('TILE', tilename)
        feat.SetField('EXTENT', extent)
        feat.SetField('LLLON', ll_lon)
        feat.SetField('LLLAT', ll_lat)
        feat.SetField('COVERSLAND', int(coversland))
        layer_out.CreateFeature(feat)
        fdef_out = None
        feat = None

    ds_out = None


def write_kml_tiles(out_filepath, tiles, land_mask_filepath, doc_name="doc name", doc_desc="doc description"):
    k = kml.KML()
    ns = '{http://www.opengis.net/kml/2.2}'
    d = kml.Document(ns, 'docid', doc_name, doc_desc)
    k.append(d)
    p_style = styles.PolyStyle(ns, 'id', fill=0)
    l_style = styles.LineStyle(ns, 'id', color="FF0000FF")
    sty = kml.Style(ns, 'id', styles=[p_style, l_style])

    # read SHP land mask
    driver = ogr.GetDriverByName("ESRI Shapefile")
    ds_mask = driver.Open(land_mask_filepath, update=False)
    layer_mask = ds_mask.GetLayer()

    for tile_counter in range(0, tiles.shape[2]):
        points = tiles[:, :, tile_counter]
        points = np.concatenate((points, np.array([points[0, :]])), axis=0)
        polygon_points = []
        for point in points:
            polygon_points.append((float(point[0]), float(point[1])))
        f = kml.Folder(ns, 'fid', 'f name', 'f description')
        d.append(f)
        # define geometry
        geom = geometry.Geometry()
        geom.geometry = Polygon(polygon_points)

        # create and add metadata
        polygon = ogr.CreateGeometryFromWkt(geom.geometry.wkt)
        coversland = False
        for feat_mask in layer_mask:
            if polygon.Intersects(feat_mask.geometry()):
                coversland = True
                break
        layer_mask.ResetReading()
        ll_lon = int(np.min(points[:, 0]))
        ll_lat = int(np.min(points[:, 1]))
        extent = int(np.max(points[:, 0]) - np.min(points[:, 0]))
        tilename = "{:03d}_{:03d}".format(int(np.min(points[:, 0])) + 180, int(np.min(points[:, 1])) + 90)
        schema_data = kml.SchemaData(ns, schema_url="#" + os.path.splitext(os.path.basename(out_filepath))[0])
        schema_data.append_data(name="GRID", value="LatLon Grid")
        schema_data.append_data(name="VERSION", value="V1")
        schema_data.append_data(name="ZONE", value="Globe")
        schema_data.append_data(name="SHORTNAME", value="LLG GL")
        schema_data.append_data(name="TILE", value=tilename)
        schema_data.append_data(name="EXTENT", value=str(extent))
        schema_data.append_data(name="LLLON", value=str(ll_lon))
        schema_data.append_data(name="LLLAT", value=str(ll_lat))
        schema_data.append_data(name="COVERSLAND", value=str(int(coversland)))
        # create placemark
        p = kml.Placemark(ns, 'id', extended_data=kml.ExtendedData(ns, elements=[schema_data]))
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
    dirname = r"D:\work\code\latlon_grid\LatLonGrid\latlongrid\grids\GL" #r"D:\work\data\LatLonGrid\tiles" #
    version = "V1"
    sub_gridname = "GL"
    tile_size = 18
    bbox = [-180, -90, 180, 90]
    dims = (int(360./tile_size), int(180./tile_size))
    tiles = tiling(bbox, dims)
    land_mask_filepath = r"R:/Datapool_processed/GIS_supportdata/World_country_boundary/world_country_admin_boundary_shapefile_with_fips_codes.shp"

    out_filepath_shp = os.path.join(dirname, "LATLON_{}_{}_T{}.shp".format(version, sub_gridname, tile_size))
    write_shp_tiles(out_filepath_shp, tiles, land_mask_filepath)

    #out_filepath_kml = os.path.join(dirname, "LATLON_{}_{}_T{}.kml".format(version, sub_gridname, tile_size))
    #doc_name = "LATLON_{}_{}_T{}".format(version, sub_gridname, tile_size)
    #write_kml_tiles(out_filepath_kml, tiles, land_mask_filepath, doc_name=doc_name, doc_desc='')

if __name__ == '__main__':
    main()
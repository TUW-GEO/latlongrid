#! /usr/bin/env python
# Copyright (c) 2018, Vienna University of Technology (TU Wien), Department of
# Geodesy and Geoinformation (GEO).
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are
# those of the authors and should not be interpreted as representing official
# policies, either expressed or implied, of the FreeBSD Project.


'''
Created on February 25, 2018
make latlongrid.dat file for LatLonGrid class
@author: Claudio Navacchi, claudio.navacchi@geo.tuwien.ac.at
'''

import os
import argparse
import pickle
from osgeo import ogr


def make_latlondata(out_dirpath, version="V1"):
    """ Make the latlongrid.dat file
    Parameters
    ----------
    out_dirpath: string
        output file directory path.

    version: string
        version of LatLonGrid system
    Returns
    -------
    int
        0 if succeeded, otherwise error code
    Notes
    -----
    latlongrid.dat is a dictionary including necessary information required by
    LatLonGrid.py class in the following structure.
    { "GL": { "projection": "projection in wkt format",
              "zone_extent": "subgrid zone geometry in wkt format",
              "coverland": {"T18": set(), # A set includes all tiles covering land
                            "T6": set(),
                            "T3": set(),
                            "T1": set(),
                            }
            }
    }
    """

    out_filepath = os.path.join(out_dirpath, "latlongrid.dat")
    if os.path.exists(out_filepath):
        raise IOError("Error: file already exist!")
    if not os.path.exists(out_dirpath):
        os.makedirs(out_dirpath)

    module_path = os.path.dirname(os.path.abspath(__file__))
    grids_path = os.path.join(module_path, "grids")

    subgrids = ["GL"]
    tilecodes = ["T1", "T3", "T6", "T18"]

    latlon_data = dict()

    for subgrid in subgrids:
        subgrid_data = dict()

        zone_fpath = os.path.join(grids_path, subgrid, "LATLON_{}_{}_T18.shp".format(version, subgrid))
        zone_boundary = load_zone_boundary(zone_fpath)
        subgrid_data["zone_extent"] = zone_boundary.ExportToWkt()

        subgrid_data["coverland"] = dict()
        for tilecode in tilecodes:
            tilepath = os.path.join(grids_path, subgrid, "LATLON_{}_{}_{}.shp".format(version, subgrid,
                                                                                                tilecode))
            tiles_coversland = load_coverland_tiles(tilepath)
            subgrid_data["coverland"][tilecode] = set(tiles_coversland)

        # Use spatial reference of T1 tile as the subgrid spatial reference
        sr_path = os.path.join(grids_path, subgrid, "LATLON_{}_{}_T1.shp".format(version, subgrid))
        sr_wkt = load_spatial_reference(sr_path)
        subgrid_data["projection"] = sr_wkt

        latlon_data[subgrid] = subgrid_data

    # Serialize latlon data by pickle with protocal=2
    with open(out_filepath, "wb") as f:
        pickle.dump(latlon_data, f, protocol=2)

    return 0


def load_zone_boundary(zone_fpath):
    driver = ogr.GetDriverByName("ESRI Shapefile")
    ds = driver.Open(zone_fpath, update=False)
    layer = ds.GetLayer()
    num_features = layer.GetFeatureCount()
    if num_features < 0:
        raise ValueError("No feature found in {}".format(zone_fpath))
    elif num_features == 1:
        f = layer.GetFeature(0)
        geom = f.GetGeometryRef().Clone()
    else:
        geom = ogr.Geometry(ogr.wkbMultiPolygon)
        for f in layer:
            geom.AddGeometry(f.GetGeometryRef().Clone())

    zone_boundary = geom.ConvexHull()
    return zone_boundary


def load_coverland_tiles(tile_fpath):
    driver = ogr.GetDriverByName("ESRI Shapefile")
    ds = driver.Open(tile_fpath, update=False)
    layer = ds.GetLayer()
    num_features = layer.GetFeatureCount()
    if num_features < 0:
        raise ValueError("No features found in {}".format(tile_fpath))

    tiles_coversland = list()
    for f in layer:
        coversland = f.GetField("COVERSLAND")
        if coversland:
            extent = int(f.GetField("EXTENT"))
            ll_lon = int(f.GetField("LLLON"))
            ll_lat = int(f.GetField("LLLAT"))
            tilename = "E{:03d}N{:03d}T{}".format(ll_lon + 180, ll_lat + 90, extent)
            tiles_coversland.append(tilename)

    return tiles_coversland


def load_spatial_reference(fpath):
    driver = ogr.GetDriverByName("ESRI Shapefile")
    ds = driver.Open(fpath, update=False)
    sr_wkt = ds.GetLayer().GetSpatialRef().ExportToWkt()
    return sr_wkt


def main():
    parser = argparse.ArgumentParser(description='Make LatLon Data File')
    parser.add_argument("outpath", help="output folder")
    parser.add_argument("-v", "--version", dest="version", nargs=1, metavar="",
                        help="LatLon Grids Version. Default is V1.")
    args = parser.parse_args()

    outpath = os.path.abspath(args.outpath)
    version = args.version[0] if args.version else "V1"
    return make_latlondata(outpath, version)


if __name__ == "__main__":
    import sys
    sys.argv.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data'))
    sys.argv.append("--version=V1")
    main()
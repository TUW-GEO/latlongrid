# Copyright (c) 2017, Vienna University of Technology (TU Wien), Department of
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
Created on March 1, 2018
Code for the LatLon Grid.
@author: Claudio Navacchi, claudio.navacchi@geo.tuwien.ac.at
'''

import os
import pickle
import copy
import itertools

import numpy as np

from pytileproj.base import TiledProjectionSystem
from pytileproj.base import TiledProjection
from pytileproj.base import TPSProjection
from pytileproj.base import TilingSystem
from pytileproj.base import Tile
from pytileproj import geometry


def _load_static_data(module_path):
    """
    load the data, raise the error if failed to load latlongrid.dat
    Parameters
    ----------
    module_path : string
        mainpath of the LatLonGrid module
    Returns
    -------
    latlondata : dict
        dictionary containing for each subgrid...
            a) the multipolygon 'zone_extent'
            b) the WKT-string 'projection'
            c) the sets for T6/T3/T1-tiles covering land 'coverland'
            d) the LatLonGrid version 'version'
    """
    latlon_data = None
    fname = os.path.join(os.path.dirname(module_path), "data", "latlongrid.dat")
    with open(fname, "rb") as f:
        latlon_data = pickle.load(f)
    return latlon_data


# TODO: what should be done with length of the strings T6 and T18, i.e. dynamic or three chars?
class LatLonGrid(TiledProjectionSystem):
    """
    Equi7Grid class object, inheriting TiledProjectionSystem() from pytileproj.
    Attributes
    ----------
    _static_data  : dict
        dictionary containing for each subgrid...
            a) the multipolygon 'zone_extent'
            b) the WKT-string 'projection'
            c) the sets for T6/T3/T1-tiles covering land 'coverland'
            d) the Equi7Grid version 'version'
    _static_subgrid_ids : list of strings
        lists the acronyms of the 7 (continental) subgrids
    _static_tilecodes : list of strings
        lists the 3 tile acronyms
    _static_sampling : list of int
        lists all allowed grid samplings
    """

    # static attribute
    _static_data = _load_static_data(__file__)
    # sub grid IDs
    _static_subgrid_ids = ["GL"]
    # supported tile widths (linked to the grid sampling)
    _static_tilecodes = ["T1", "T3", "T6", "T18"]
    # supported grid spacing ( = the pixel sampling)
    _static_sampling = [0.0001, 0.00016, 0.0002, 0.0003, 0.0004, 0.0005, 0.0006,
                        0.0008, 0.001, 0.0016, 0.002, 0.003, 0.004, 0.005, 0.006,
                        0.008, 0.01]

    def __init__(self, sampling):
        """
        Initialises an Equi7Grid class for a specified sampling.
        Parameters
        ----------
        sampling : float
            the grid sampling = size of pixels; in metres.
        """
        # check if the equi7grid.data have been loaded successfully
        if LatLonGrid._static_data is None:
            raise ValueError("cannot load LatLonGrid ancillary data!")
        # check if sampling is allowed
        if sampling not in LatLonGrid._static_sampling:
            raise ValueError("Sampling {}° is not supported!".format(sampling))

        # initializing
        super(LatLonGrid, self).__init__(sampling, tag='LatLon')
        self.core.projection = 'LatLon'

    @staticmethod
    def encode_sampling(sampling):
        """
        provides a string representing the sampling (e.g. for the tilenames)

        Parameters
        ----------
        sampling : int, float
            the grid sampling = size of pixels; in degree.
        Returns
        -------
        sampling_str : str
            string representing the sampling
        """
        if sampling < 0.001:
            sampling_scaled = int(sampling * 1e6)
            order_tag = "U"
        elif sampling < 1.:
            sampling_scaled = int(sampling * 1e3)
            order_tag = "M"
        else:
            sampling_scaled = int(sampling)
            order_tag = "D"

        sampling_str = str(sampling_scaled).rjust(3, '0') + order_tag
        if len(sampling_str) > 4:
            raise ValueError('Resolution is badly defined!')

        return sampling_str

    @staticmethod
    def decode_sampling(sampling_str):
        """
        converts the string representing the sampling (e.g. from the tilenames)
        to an integer value in metres

        Parameters
        ----------
        sampling_str : str
            string representing the sampling
        Returns
        -------
        sampling : int
            the grid sampling = size of pixels; in metres.

        """
        if len(sampling_str) != 4:
            raise ValueError('Resolution is badly defined!')
        if 'U' in sampling_str:
            scale_factor = 1e-6
        elif 'M' in sampling_str:
            scale_factor = 1e-3
        elif 'D' in sampling_str:
            scale_factor = 1.
        else:
            raise ValueError('Resolution is badly defined!')

        sampling = float(sampling_str[:-1])*scale_factor
        return sampling

    def define_subgrids(self):
        """
        Builds the grid's subgrids from a static file.
        Returns
        -------
        subgrids : dict of LatLonSubgrid
            dict of all subgrids of the grid
        """
        subgrids = dict()
        for sg in self._static_subgrid_ids:
            subgrids[sg] = LatLonSubgrid(self.core, sg)
        return subgrids

    #TODO
    def get_tiletype(self, sampling=None):
        """
        Returns the tilecode defined for the grid's sampling
        Parameters
        ----------
        sampling : int, optional
            the grid sampling = size of pixels; in metres.
        Returns
        -------
        tilecode : str
            tilecode (related the tile size of the grid)
        """

        # get the tile code of the grid instance
        if sampling is None:
            return self._get_tiletype()

        scale_factor = 1e4
        sampling_scaled = int(round(sampling * scale_factor))

        if ((sampling_scaled >= 1) and (sampling_scaled < 3)) and (1*scale_factor % sampling_scaled == 0):
            tilecode = "T1"
        elif ((sampling_scaled >= 3) and (sampling_scaled < 6)) and (3*scale_factor % sampling_scaled == 0):
            tilecode = "T3"
        elif ((sampling_scaled >= 6) and (sampling_scaled < 20)) and (6*scale_factor % sampling_scaled == 0):
            tilecode = "T6"
        elif ((sampling_scaled >= 20) and (sampling_scaled < 101)) and (18*scale_factor % sampling_scaled == 0):
            tilecode = "T18"
        else:
            msg = "Error: Given resolution %f is not supported!" % sampling
            msg += " Supported resolutions: {}".format(str(LatLonGrid._static_sampling))
            raise ValueError(msg)

        return tilecode

    def get_tilesize(self, sampling):
        """
        Return the tile size in metres defined for the grid's sampling
        Parameters
        ----------
        sampling : int
            the grid sampling = size of pixels; in metres.
        Returns
        -------
        xsize, ysize : int
            tile size in x and y direction defined for the grid's sampling
        """
        xsize = {'T18': 18, 'T6': 6, 'T3': 3, 'T1': 1}[
            self.get_tiletype(sampling)]
        ysize = {'T18': 18, 'T6': 6, 'T3': 3, 'T1': 1}[
            self.get_tiletype(sampling)]
        return xsize, ysize

    def create_tile(self, name):
        """
        shortcut to create_tile, returning a LatLonTile object
        Parameters
        ----------
        name : str
            name of the tile; e.g GL500M_E012N018T6
        Returns
        -------
        LatLonTile
            object containing info of the specified tile
        """
        return self.subgrids[name[0:2]].tilesys.create_tile(name)


class LatLonSubgrid(TiledProjection):
    """
    LatLonSubgrid class object, inheriting TiledProjection() from pytileproj.
    """

    def __init__(self, core, region):
        """
        Initialises an Equi7Subgrid class for a specified continent.
        Parameters
        ----------
        core : TPSCoreProperty
            defines core parameters of the (sub-) grid
        region : str
            acronym of the continent, e.g. 'EU' or 'SA'.
        """

        # load WKT string and extent shape
        data = LatLonGrid._static_data[region]

        _core = copy.copy(core)
        _core.tag = region
        _core.projection = TPSProjection(epsg=4326)

        # holds core parameters of the (sub-) grid
        self.core = _core

        # holds name of the subgrid
        self.name = ''.join(('LATLON_', region, LatLonGrid.encode_sampling(core.sampling)))

        # holds the extent of the subgrid in the latlon-space
        self.polygon_geog = geometry.create_geometry_from_wkt(data['zone_extent'])

        # defines the tilingsystem of the subgrid
        self.tilesys = LatLonTilingSystem(self.core, self.polygon_geog)

        super(LatLonSubgrid, self).__init__(self.core, self.polygon_geog, self.tilesys)

    def search_tiles_in_geometry(self, geom, coverland=True):
        """
        Search the tiles which are overlapping with the subgrid

        Parameters
        ----------
        geom : OGRGeometry
            A polygon geometry representing the region of interest.
        coverland : Boolean
            option to search for tiles covering land at any point in the tile

        Returns
        -------
        overlapped_tiles : list
            Return a list of the overlapped tiles' name.
            If not found, return empty list.
        """

        overlapped_tiles = list()

        # check if geom intersects subgrid
        if geom.Intersects(self.polygon_geog):
            # get intersect area with subgrid in latlon
            intersect = geom.Intersection(self.polygon_geog)
        else:
            return overlapped_tiles

        # get spatial reference of subgrid in grid projection
        grid_sr = self.projection.osr_spref

        # transform intersection geometry back to the spatial reference system
        # of the subgrid.
        # segmentise for high precision during reprojection.
        projected = intersect.GetSpatialReference().IsProjected()
        if projected == 0:
            max_segment = 0.5
        else:
            raise Warning('Please check unit of geometry before reprojection!')
        intersect = geometry.transform_geometry(intersect, grid_sr,
                                                segment=max_segment)

        # get envelope of the Geometry and cal the bounding tile of the
        envelope = intersect.GetEnvelope()
        lon_min = int(envelope[0]) // self.core.tile_xsize_m \
            * self.core.tile_xsize_m
        lon_max = (int(envelope[1]) // self.core.tile_xsize_m + 1) \
            * self.core.tile_xsize_m
        lat_min = int(envelope[2]) // self.core.tile_ysize_m * \
            self.core.tile_ysize_m
        lat_max = (int(envelope[3]) // self.core.tile_ysize_m + 1) * \
            self.core.tile_ysize_m


        # get overlapped tiles
        lonr = np.arange(
            lon_min, lon_max + self.core.tile_xsize_m, self.core.tile_xsize_m)
        latr = np.arange(
            lat_min, lat_max + self.core.tile_ysize_m, self.core.tile_ysize_m)

        for lon, lat in itertools.product(lonr, latr):
            geom_tile = geometry.extent2polygon(
                (lon, lat, lon + self.core.tile_xsize_m,
                 lat + self.core.tile_xsize_m), grid_sr)
            if geom_tile.Intersects(intersect):
                ftile = self.tilesys.point2tilename(lon, lat)
                if not coverland or self.tilesys.check_tile_covers_land(ftile):
                    overlapped_tiles.append(ftile)

        return overlapped_tiles


class LatLonTilingSystem(TilingSystem):
    """
    Equi7TilingSystem class, inheriting TilingSystem() from pytileproj.
    provides methods for queries and handling.
    """

    def __init__(self, core, polygon_geog):
        """
        Initialises an Equi7TilingSystem class for a specified continent.
        Parameters
        ----------
        core : TPSCoreProperty
            defines core parameters of the (sub-) grid
        polygon_geog : OGRGeometry
            geometry defining the extent/outline of the subgrid
        """

        super(LatLonTilingSystem, self).__init__(core, polygon_geog, 0, 0)

        self.msg1 = '"tilename" is not properly defined! Examples: ' \
                    '"{0}{1}_E012N036{2}" ' \
                    'or "E012N036{2}"'.format(self.core.tag, LatLonGrid.encode_sampling(self.core.sampling),
                                              self.core.tiletype)
        self.msg2 = 'East and North coordinates of lower-left-pixel ' \
                    'must be multiples of {}°!'.format(self.core.tile_ysize_m)
        self.msg3 = 'Tilecode must be one of T18, T6, T3, T1!'

    def round_lonlat2lowerleft(self, lon, lat):
        """
        Returns the lower-left coordinates of the tile in which the point,
        defined by x and y coordinates (in metres), is located.

        Parameters
        ----------
        lon : float
            lon (right) coordinate in the desired tile
            must to given together with lat
        lat : float
            lat (up) coordinate in the desired tile
            must to given together with lon

        Returns
        -------
        ll_lon, ll_lat: int
            lower-left coordinates of the tile
        """

        ll_lon = (lon + 180) // self.core.tile_xsize_m * self.core.tile_xsize_m - 180
        ll_lat = (lat + 90) // self.core.tile_ysize_m * self.core.tile_ysize_m - 90
        return ll_lon, ll_lat

    def create_tile(self, name=None, lon=None, lat=None):
        """
        Returns a Equi7Tile object
        Parameters
        ----------
        name : str
            name of the tile; e.g EU500M_E012N018T6 or E012N018T6
        lon : float
            x (right) coordinate of a pixel located in the desired tile
            must to given together with y
        lat : float
            y (up) coordinate of a pixel located in the desired tile
            must to given together with x
        Returns
        -------
        LatLonTile
            object containing info of the specified tile
        Notes
        -----
        either name, or x and y, must be given.
        """

        # use the x and y coordinates for specifing the tile
        if lon is not None and lat is not None and name is None:
            ll_lon, ll_lat = self.round_lonlat2lowerleft(lon, lat)
        # use the tile name for specifing the tile
        elif name is not None and lon is None and lat is None:
            ll_lon, ll_lat = self.tilename2lowerleft(name)
        else:
            raise AttributeError('"name" or "lon"&"lat" must be defined!')

        # get name of tile (assures long-form of tilename, even if short-form
        # is given)
        name = self._encode_tilename(ll_lon, ll_lat)
        # set True if land in the tile
        covers_land = self.check_tile_covers_land(tilename=name)

        return LatLonTile(self.core, name, ll_lon, ll_lat, covers_land=covers_land)

    def point2tilename(self, lon, lat, shortform=False):
        """
        Returns the name string of an Equi7Tile in which the point,
        defined by x and y coordinates (in metres), is located.
        Parameters
        ----------
        lon : float
            lon (right) coordinate in the desired tile
            must to given together with lat
        lat : float
            lat (up) coordinate in the desired tile
            must to given together with lon
        shortform : Boolean
            option for giving back the shortform of the tile name
            e.g. 'E012N018T6'.
        Returns
        -------
        str
            the tilename in longform e.g. 'EU500M_E012N018T6'
            or in shortform e.g. 'E012N018T6'.
        """
        ll_lon, ll_lat = self.round_lonlat2lowerleft(lon, lat)
        return self._encode_tilename(ll_lon, ll_lat, shortform=shortform)

    def encode_tilename(self, ll_lon, ll_lat, sampling, tilecode, shortform=False):
        """
        Encodes a tilename
        Parameters
        ----------
        ll_lon : int
            Lower-left lon coordinate.
        ll_lat : int
            Lower-left lat coordinate.
        sampling : float
            the grid sampling = size of pixels; in degree.
        tilecode : str
            tilecode
        shortform : boolean, optional
            return shortform of tilename (default: False).
        Returns
        -------
        str
            the tilename in longform e.g. 'GL001M_E012N018T1'
            or in shortform e.g. 'E012N018T1'.
        """

        # gives long-form of tilename (e.g. "EU500M_E012N018T6")
        tilename = "{}{}_E{:03d}N{:03d}{}".format(
            self.core.tag, LatLonGrid.encode_sampling(sampling),
            int(ll_lon) + 180, int(ll_lat) + 90, tilecode)

        if shortform:
            tilename = self.tilename2short(tilename)

        return tilename

    def _encode_tilename(self, ll_lon, ll_lat, shortform=False):
        """
        Encodes a tilename defined by the lower-left coordinates of the tile,
        using inherent information
        Parameters
        ----------
        ll_lon : int
            lower-left lon coordinate.
        ll_lat : int
            lower-left lat coordinate.
        shortform : boolean, optional
            return shortform of tilename (default: False).
        Returns
        -------
        str
            the tilename in longform e.g. 'GL500M_E012N018T1'
            or in shortform e.g. 'E012N018T1'.
        """
        return self.encode_tilename(ll_lon, ll_lat, self.core.sampling, self.core.tiletype, shortform=shortform)

    def tilename2short(self, longform):
        """
        Converts a tilename in longform to shortform
        e.g. 'GL001M_E012N018T6' --> 'E012N018T6'
        Parameters
        ----------
        longform : str
            longform of the tilename
        Returns
        -------
        str
            shortform of the tilename
        """
        self.check_tilename(longform)
        if len(longform) == 17:
            shortform = longform[7:]
        return shortform

    def tilename2lowerleft(self, tilename):
        """
        Return the lower-left coordinates of the tile

        Parameters
        ----------
        tilename : str
            the tilename in longform e.g. 'GL001M_E012N018T1'
            or in shortform e.g. 'E012N018T1'.
        Returns
        -------
        ll_lon, ll_lat: int
            lower-left coordinates of the tile
        """
        _, _, _, ll_lon, ll_lat, _ = self.decode_tilename(tilename)
        return ll_lon, ll_lat

    def check_tilename(self, tilename):
        """
        checks if the given tilename is valid

        Parameters
        ----------
        tilename : str
            the tilename in longform e.g. 'GL500M_E012N018T1'
            or in shortform e.g. 'E012N018T1'.
        Returns
        -------
        Boolean
            result of the check
        """

        check = False
        self.decode_tilename(tilename)
        check = True
        return check

    def decode_tilename(self, tilename):
        """
        Returns the information assigned to the tilename
        Parameters
        ----------
        tilename : str
            the tilename in longform e.g. 'GL500M_E012N018T6'
            or in shortform e.g. 'E012N018T6'.
        Returns
        -------
        subgrid_id : str
            ID acronym of the subgrid, e.g. 'GLOBAL'
        sampling : float
            the grid sampling = size of pixels; in degree.
        tile_size_m : int
            extent/size of the tile; in degree.
        ll_lon : int
            lower-left lon coordinate.
        ll_lat : int
            lower-left lat coordinate.
        tilecode : str
            tilecode (related the tile size of the grid)
        """
        tf = self.core.tile_ysize_m

        # allow short-form of tilename (e.g. "E012N018T1")
        if len(tilename) in [10, 11]:
            tile_size_d = int(tilename.split('T')[-1])
            if tile_size_d != self.core.tile_xsize_m:
                raise ValueError(self.msg1)
            ll_lon = int(tilename[1:4]) - 180
            if ll_lon % tf:
                raise ValueError(self.msg2)
            ll_lat = int(tilename[5:8]) - 90
            if ll_lat % tf:
                raise ValueError(self.msg2)
            tilecode = "T" + tilename.split('T')[-1]
            if tilecode != self.core.tiletype:
                raise ValueError(self.msg1)
            subgrid_id = self.core.tag
            sampling = self.core.sampling

        # allow long-form of tilename (e.g. "GL100U_E012N018T1")
        elif len(tilename) in [17, 18]:
            subgrid_id = tilename[0:2]
            if subgrid_id != self.core.tag:
                raise ValueError(self.msg1)
            sampling = LatLonGrid.decode_sampling(tilename[2:6])
            if not np.isclose(sampling, self.core.sampling):
                raise ValueError(self.msg1)
            tile_size_d = int(tilename.split('T')[-1])
            if tile_size_d != self.core.tile_xsize_m:
                raise ValueError(self.msg1)
            ll_lon = int(tilename[8:11]) - 180
            if ll_lon % tf:
                raise ValueError(self.msg2)
            ll_lat = int(tilename[12:15]) - 90
            if ll_lat % tf:
                raise ValueError(self.msg2)
            tilecode = "T" + tilename.split('T')[-1]
            if tilecode != self.core.tiletype:
                raise ValueError(self.msg1)

        # wrong length
        else:
            raise ValueError(self.msg1)

        return subgrid_id, sampling, tile_size_d, ll_lon, ll_lat, tilecode

    def find_overlapping_tilenames(self, tilename,
                                   target_sampling=None,
                                   target_tiletype=None):
        """
        finds the "family tiles", which share a congruent or partial overlap,
        but with different resolution and tilecode
        Parameters
        ----------
        tilename : str
            the tilename in longform e.g. 'GL500M_E012N018T6'
            or in shortform e.g. 'E012N018T6'.
        target_sampling : int
            the sampling of the target grid system
        target_tiletype : string
            tilecode string
        Returns
        -------
        list
            list of found tiles
            for smaller tiles: tiles contained in tile with 'tilename'
            for larger tiles: the tile overlap the with 'tilename'
        Notes
        -----
        Either the sampling or tilecode should be given.
        But if both are given, the sampling will be used.
        """

        # return tilenames in shortform or longform?
        if target_sampling is None:
            shortform = True
        else:
            shortform = False

        # check search input
        if target_sampling is not None and target_tiletype is None:
            sampling = target_sampling
        if target_sampling is None and target_tiletype is not None:
            if target_tiletype == 'T1':
                sampling = 0.0001
            elif target_tiletype == 'T3':
                sampling = 0.0003
            elif target_tiletype == 'T6':
                sampling = 0.0006
            elif target_tiletype == 'T6':
                sampling = 0.002
            else:
                raise ValueError(self.msg3)
        if target_sampling is not None and target_tiletype is not None:
            sampling = target_sampling

        # grid of the searched tiles
        target_grid = LatLonGrid(sampling=sampling)
        target_tiletype = target_grid.core.tiletype
        target_tilesize = target_grid.core.tile_xsize_m

        # features of the input tile(name)
        _, src_sampling, src_tilesize_d, src_ll_lon, src_ll_lat, src_tiletype = \
            self.decode_tilename(tilename)

        # overlapping tiles
        family_tiles = list()

        # for larger tiles
        if target_tiletype >= src_tiletype:
            t_east = (src_ll_lon + 180) // target_tilesize * target_tilesize - 180
            t_north = (src_ll_lat + 90) // target_tilesize * target_tilesize - 90
            name = target_grid.subgrids[self.core.tag]. \
                tilesys.encode_tilename(t_east, t_north,
                                        sampling,
                                        target_tiletype,
                                        shortform=shortform)
            family_tiles.append(name)

        # for smaller tiles
        else:
            n = int(src_tilesize_d // target_tilesize)
            for lon, lat in itertools.product(range(n), range(n)):
                s_east = (src_ll_lon + lon * target_tilesize)
                s_north = (src_ll_lat + lat * target_tilesize)
                name = target_grid.subgrids[self.core.tag]. \
                    tilesys.encode_tilename(s_east, s_north,
                                            sampling,
                                            target_tiletype,
                                            shortform=shortform)
                family_tiles.append(name)

        return family_tiles

    def check_tile_covers_land(self, tilename=None):
        """
        checks if a tile covers land
        Parameters
        ----------
        tilename : str
            the tilename in longform e.g. 'EU500M_E012N018T6'
        Returns
        -------
        Boolean
        """
        land_tiles = self.list_tiles_covering_land()
        if self.check_tilename(tilename):
            tilename = self.tilename2short(tilename)
            return tilename in land_tiles

    def list_tiles_covering_land(self):
        """
        Returns a list of all tiles in the subgrid covering land
        Returns
        -------
        list
            list containing land tiles
        """

        land_tiles = LatLonGrid._static_data[
            self.core.tag]["coverland"][self.core.tiletype]
        return list(land_tiles)


class LatLonTile(Tile):
    """
    The LatLonTile class, inheriting Tile() from pytileproj.
    A tile in the LatLonGrid system, holding characteristics of the tile.
    """

    def __init__(self, core, name, ll_lon, ll_lat, covers_land):
        super(LatLonTile, self).__init__(core, name, ll_lon, ll_lat)
        self.covers_land = covers_land

    @property
    def shortname(self):
        return self.name[7:]
# Copyright (c) 2016,Vienna University of Technology,
# Department of Geodesy and Geoinformation
# All rights reserved.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL VIENNA UNIVERSITY OF TECHNOLOGY, DEPARTMENT OF
# GEODESY AND GEOINFORMATION BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
# BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER
# IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


"""
Tests for the LatLonGrid().
"""

import unittest
import numpy.testing as nptest

from latlongrid.latlongrid import LatLonGrid
from pytileproj.geometry import setup_test_geom_spitzbergen
from pytileproj.geometry import setup_geom_kamchatka


def assert_tuples(tuple_1, tuple_2):
    for i in range(len(tuple_1)):
        if type(tuple_1[i]) == float:
            nptest.assert_allclose(tuple_1[i], tuple_2[i])
        else:
            assert tuple_1[i] == tuple_2[i]


class TestLatLonGrid(unittest.TestCase):

    def test_ij2xy(self):
        """
        Tests tile indices to lonlat coordination in the subgrid projection
        """
        latlon_grid = LatLonGrid(0.0001)
        lon_should = -71.9667
        lat_should = -1.0444
        tile = latlon_grid.GL.tilesys.create_tile(lon=-71.3456, lat=-1.5432)
        lon, lat = tile.ij2xy(333, 444)
        nptest.assert_allclose(lon_should, lon)
        nptest.assert_allclose(lat_should, lat)

    def test_xy2ij(self):
        """
        Tests lonlat to tile array indices.
        """
        latlon_grid = LatLonGrid(0.0001)
        column_should = 333
        row_should = 444
        tile = latlon_grid.GL.tilesys.create_tile(lon=-71.3456, lat=-1.5432)
        column, row = tile.xy2ij(-71.9667, -1.0444)
        nptest.assert_allclose(column_should, column)
        nptest.assert_allclose(row_should, row)

    def test_decode_tilename(self):
        """
        Tests the decoding of tilenames.
        """
        latlon_grid_coarse = LatLonGrid(0.01)
        latlon_grid_fine = LatLonGrid(0.0001)

        assert_tuples(latlon_grid_coarse.GL.tilesys.decode_tilename('GL010M_E072N036T18'),
                             ('GL', 0.01, 18, -108, -54, 'T18'))
        assert_tuples(latlon_grid_fine.GL.tilesys.decode_tilename('GL100U_E194N135T1'),
                             ('GL', 0.0001, 1, 14, 45, 'T1'))

        with nptest.assert_raises(ValueError) as excinfo:
            latlon_grid_fine.GL.tilesys.decode_tilename('E018N018T18')
        assert str(excinfo.exception).startswith('"tilename" is not properly defined!')

    def test_find_overlapping_tilenames(self):
        """
        Tests search for tiles which share the same extent_m but
        with different resolution and tilecode.
        """
        latlon_grid_coarse = LatLonGrid(0.0006)
        latlon_grid_fine = LatLonGrid(0.0003)

        tiles1_should = ['GL300U_E012N042T3', 'GL300U_E012N045T3', 'GL300U_E015N042T3', 'GL300U_E015N045T3']
        tiles1 = latlon_grid_coarse.GL.tilesys.find_overlapping_tilenames('GL600U_E012N042T6', target_sampling=0.0003)
        assert sorted(tiles1) == sorted(tiles1_should)

        tiles2_should = ['E012N042T3', 'E012N045T3', 'E015N042T3', 'E015N045T3']
        tiles2 = latlon_grid_coarse.GL.tilesys.find_overlapping_tilenames('E012N042T6', target_tiletype='T3')
        assert sorted(tiles2) == sorted(tiles2_should)

        tiles3_should = ['GL600U_E012N042T6']
        tiles3 = latlon_grid_fine.GL.tilesys.find_overlapping_tilenames('E015N042T3', target_sampling=0.0006)
        assert sorted(tiles3) == sorted(tiles3_should)

        tiles4_should = ['E012N042T6']
        tiles4 = latlon_grid_fine.GL.tilesys.find_overlapping_tilenames('E015N045T3', target_tiletype='T6')
        assert sorted(tiles4) == sorted(tiles4_should)

    def test_search_tiles_lon_lat_extent(self):
        """
        Tests searching for tiles with input of lon lat extent
        """
        latlon_grid = LatLonGrid(0.0006)
        tiles = latlon_grid.search_tiles_in_roi(extent=[0, 30, 10, 40], coverland=True)
        tiles_all = latlon_grid.search_tiles_in_roi(extent=[-179.9, -89.9, 179.9, 89.9], coverland=True)
        desired_tiles = ["GL600U_E180N120T6", "GL600U_E186N120T6",
                         "GL600U_E180N126T6", "GL600U_E186N126T6"]

        assert len(tiles_all) == 995
        assert sorted(tiles) == sorted(desired_tiles)

    def test_search_tiles_lon_lat_extent_by_points(self):
        """
        Tests searching for tiles with input of lon lat points
        """
        latlon_grid = LatLonGrid(0.0006)
        tiles = latlon_grid.search_tiles_in_roi(
            extent=[(0, 40), (10, 40), (10, 30), (0, 30)],
            coverland=True)

        desired_tiles = ["GL600U_E180N120T6", "GL600U_E186N120T6",
                         "GL600U_E180N126T6", "GL600U_E186N126T6"]

        assert sorted(tiles) == sorted(desired_tiles)

    def test_search_tiles_spitzbergen(self):
        """
        Tests the tile searching over Spitzbergen in the polar zone; ROI defined
        by a 4-corner polygon over high latitudes (is much curved on the globe).
        """

        grid = LatLonGrid(0.0006)

        spitzbergen_geom = setup_test_geom_spitzbergen()
        spitzbergen_geom_tiles = sorted(['GL600U_E186N162T6', 'GL600U_E192N162T6', 'GL600U_E198N162T6',
                                         'GL600U_E204N162T6', 'GL600U_E210N162T6', 'GL600U_E186N168T6',
                                         'GL600U_E192N168T6', 'GL600U_E198N168T6', 'GL600U_E204N168T6',
                                         'GL600U_E210N168T6', 'GL600U_E216N168T6'])
        tiles = sorted(grid.search_tiles_in_roi(spitzbergen_geom,
                                                coverland=False))

        assert sorted(tiles) == sorted(spitzbergen_geom_tiles)

        spitzbergen_geom_tiles = sorted(['GL600U_E192N162T6', 'GL600U_E198N162T6', 'GL600U_E204N162T6',
                                         'GL600U_E186N168T6', 'GL600U_E192N168T6', 'GL600U_E198N168T6',
                                         'GL600U_E204N168T6', 'GL600U_E210N168T6'])
        tiles = sorted(grid.search_tiles_in_roi(spitzbergen_geom,
                                                coverland=True))

        assert sorted(tiles) == sorted(spitzbergen_geom_tiles)

    def test_search_tiles_kamchatka(self):
        """
        Tests the tile searching over Kamchatka in far east Sibiria;

        This test is especially nice, as it contains also a tile that covers both,
        the ROI and the continental zone, but the intersection of the tile and
        the ROI is outside of the zone.

        Furthermore, it also covers zones that consist of a multipolygon, as it
        is located at the 180deg/dateline.
        """

        grid = LatLonGrid(0.0006)

        kamchatka_geom = setup_geom_kamchatka()
        kamchatka_geom_tiles = sorted(["GL600U_E342N144T6", "GL600U_E348N144T6", "GL600U_E354N144T6"])
        tiles = sorted(grid.search_tiles_in_roi(kamchatka_geom, coverland=False))

        assert sorted(tiles) == sorted(kamchatka_geom_tiles)

    def test_identify_tiles_overlapping_xybbox(self):
        """
        Tests identification of tiles covering a bounding box
        given in lonlat coordinats
        """

        latlon_grid_coarse = LatLonGrid(0.01)
        latlon_grid_fine = LatLonGrid(0.0006)

        tiles1_should = ["GL010M_E180N090T18", "GL010M_E180N108T18",
                         "GL010M_E180N126T18"]

        tiles2_should = ["GL600U_E186N132T6", "GL600U_E186N138T6",
                         "GL600U_E192N132T6", "GL600U_E192N138T6"]

        tiles1 = latlon_grid_coarse.GL.tilesys.identify_tiles_overlapping_lonlatbbox([0, 0, 10, 40])

        tiles2 = latlon_grid_fine.GL.tilesys.identify_tiles_overlapping_lonlatbbox([8.9047, 46.4158, 17.2373, 49.1299])

        assert sorted(tiles1) == sorted(tiles1_should)
        assert sorted(tiles2) == sorted(tiles2_should)

    def test_get_covering_tiles(self):
        """
        Tests the search for co-locating tiles of other type.
        """

        latlon_grid_coarse = LatLonGrid(0.0006)
        latlon_grid_fine = LatLonGrid(0.0003)

        fine_tiles = ['GL300U_E177N084T3', 'GL300U_E177N087T3',
                      'GL300U_E180N084T3', 'GL300U_E180N087T3']

        target_tiletype = latlon_grid_coarse.get_tiletype()
        target_sampling = latlon_grid_coarse.core.sampling

        # invoke the results as tile name in short form
        coarse_tiles_shortform = latlon_grid_fine.GL.tilesys.get_covering_tiles(fine_tiles,
                                                                      target_tiletype=target_tiletype)

        # invoke the results as tile name in long form
        coarse_tiles_longform = latlon_grid_fine.GL.tilesys.get_covering_tiles(fine_tiles,
                                                                     target_sampling=target_sampling)

        assert sorted(coarse_tiles_shortform) == ['E174N084T6', 'E180N084T6']
        assert sorted(coarse_tiles_longform) == ['GL600U_E174N084T6', 'GL600U_E180N084T6']

if __name__ == '__main__':
    unittest.main()
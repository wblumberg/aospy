"""model.py: Model class of aospy for storing attributes of a GCM."""
from __future__ import print_function
import glob
import os

import numpy as np
import xray

from .__config__ import (LAT_STR, LON_STR, PHALF_STR, PFULL_STR, PLEVEL_STR,
                         LAT_BOUNDS_STR, LON_BOUNDS_STR)
from .constants import r_e
from .io import get_data_in_direc_repo
from .utils import dict_name_keys, level_thickness, to_radians


class Model(object):
    """Parameters of local data associated with a single climate model."""
    def __init__(self, name='', description='', proj=False, grid_file_paths=(),
                 data_in_direc=False, data_in_dir_struc=False,
                 data_in_dur=False, data_in_start_date=False,
                 data_in_end_date=False, default_date_range=False, runs={},
                 default_runs={}, load_grid_data=False, repo_version=False):
        self.name = name
        self.description = description
        self.proj = proj

        self.grid_file_paths = grid_file_paths
        self.repo_version = repo_version

        self.data_in_direc = data_in_direc
        self.data_in_dir_struc = data_in_dir_struc
        self.data_in_dur = data_in_dur
        self.data_in_start_date = data_in_start_date
        self.data_in_end_date = data_in_end_date
        self.default_date_range = default_date_range

        self.runs = dict_name_keys(runs)
        [setattr(run, 'parent', self) for run in self.runs.values()]
        if default_runs:
            self.default_runs = dict_name_keys(default_runs)
        else:
            self.default_runs = {}

        self.grid_data_is_set = False
        if load_grid_data:
            self.set_grid_data()
            self.grid_data_is_set = True

    def __str__(self):
        return 'Model instance "' + self.name + '"'

    __repr__ = __str__

    def find_data_in_direc_repo(self, run_name='amip', var_name='ta',
                                direc_sub='mon/atmos/Amon/r1i1p1'):
        """Find the netCDF files used to populate grid attrs for a GFDL repo"""
        direc = os.path.join(self.data_in_direc, run_name, direc_sub)
        direc_full = get_data_in_direc_repo(direc, var_name,
                                            version=self.repo_version)
        # Some repos have all variables in the same directory.
        files = glob.glob(os.path.join(direc_full, var_name + '_*.nc'))
        if len(files) == 0:
            files = glob.glob(os.path.join(direc_full, var_name,
                                           var_name + '_*.nc'))
        # Others have subdirectories for each variable.
        if len(files) > 0:
            files.sort()
            return files
        else:
            raise IOError("Specified files don't exist for var name '%s' "
                          "in directory '%s" % (var_name, direc_full))

        return glob.glob(os.path.join(direc_full, var_name + '_*.nc'))

    def _get_grid_files(self):
        """Get the files holding grid data for an aospy object."""
        datasets = []
        for path in self.grid_file_paths:
            try:
                ds = xray.open_dataset(path, decode_times=False)
            except TypeError:
                ds = xray.open_mfdataset(path, decode_times=False)
            datasets.append(ds)
        return tuple(datasets)

    @staticmethod
    def _get_grid_attr(grid_objs, attr_name):
        """Get attribute from the grid_objs file(s)."""
        for xds in grid_objs:
            try:
                return getattr(xds, attr_name)
            except AttributeError:
                pass

    @staticmethod
    def _rename_coords(ds):
        """
        Renames all coordinates within a Dataset or DataArray so that they
        match the internal names.
        """
        primary_attrs = {
            LAT_STR:         ('lat', 'latitude', 'LATITUDE', 'y', 'yto'),
            LAT_BOUNDS_STR:    ('latb', 'lat_bnds', 'lat_bounds'),
            LON_STR:         ('lon', 'longitude', 'LONGITUDE', 'x', 'xto'),
            LON_BOUNDS_STR:    ('lonb', 'lon_bnds', 'lon_bounds'),
            PLEVEL_STR:      ('level', 'lev', 'plev'),
            PHALF_STR:       ('phalf',),
            PFULL_STR:       ('pfull',)
            }
        if isinstance(ds, (xray.DataArray, xray.Dataset)):
            for name_int, names_ext in primary_attrs.items():
                # Check if coord is in dataset already.
                ds_coord_name = set(names_ext).intersection(set(ds.coords))
                if ds_coord_name:
                    # Rename to the aospy internal name.
                    ds = ds.rename({list(ds_coord_name)[0]: name_int})
        return ds

    def _set_mult_grid_attr(self):
        """
        Set multiple attrs from grid file given their names in the grid file.
        """
        grid_attrs = {
            LAT_STR:         ('lat', 'latitude', 'LATITUDE', 'y', 'yto'),
            LAT_BOUNDS_STR:    ('latb', 'lat_bnds', 'lat_bounds'),
            LON_STR:         ('lon', 'longitude', 'LONGITUDE', 'x', 'xto'),
            LON_BOUNDS_STR:    ('lonb', 'lon_bnds', 'lon_bounds'),
            PLEVEL_STR:      ('level', 'lev', 'plev'),
            # 'time':        ('time', 'TIME'),
            # 'time_st':     ('average_T1',),
            # 'time_end':    ('average_T2',),
            # 'time_dur':    ('average_DT',),
            # 'time_bounds': ('time_bounds', 'time_bnds'),
            # 'year':        ('yr', 'year'),
            # 'month':       ('mo', 'month'),
            # 'day':         ('dy', 'day'),
            'sfc_area':    ('area', 'sfc_area'),
            'zsurf':       ('zsurf',),
            'land_mask':   ('land_mask',),
            'pk':          ('pk',),
            'bk':          ('bk',),
            PHALF_STR:     ('phalf',),
            PFULL_STR:     ('pfull',),
            # 'nrecords':    ('nrecords',),
            # 'idim':        ('idim',),
            # 'fill_value':  ('fill_value')
        }
        grid_objs = self._get_grid_files()
        for name_int, names_ext in grid_attrs.items():
            for name in names_ext:
                grid_attr = self._get_grid_attr(grid_objs, name)
                if np.any(grid_attr):
                    # Rename coordinates to aospy's internal names.
                    renamed_attrs = self._rename_coords(grid_attr)
                    setattr(self, name_int, renamed_attrs)
                    break

    @staticmethod
    def bounds_from_array(arr, bounds_name):
        """Get the bounds of an array given its center values.

        E.g. if lat-lon grid center lat/lon values are known, but not the
        bounds of each grid box.  The algorithm assumes that the bounds
        are simply halfway between each pair of center values.
        """
        bounds_interior = np.diff(arr)
        bound_0 = arr[0] - (bounds_interior[0] - arr[0])
        bound_last = arr[-1] + (arr[-1] - bounds_interior[-1])
        bounds = xray.concat([bound_0, bounds_interior, bound_last])
        return bounds.rename(bounds_name)

    @staticmethod
    def diff_bounds(bounds, coord):
        """Get grid spacing by subtracting upper and lower bounds."""
        try:
            return bounds[:, 1] - bounds[:, 0]
        except IndexError:
            diff = np.diff(bounds, axis=0)
            return xray.DataArray(diff, dims=coord.dims, coords=coord.coords)

    @classmethod
    def grid_sfc_area(cls, lon, lat, lon_bounds=None, lat_bounds=None):
        """Calculate surface area of each grid cell in a lon-lat grid."""
        # Compute the bounds if not given.
        if lon_bounds is None:
            lon_bounds = cls.bounds_from_array(lon, LON_BOUNDS_STR)
        if lat_bounds is None:
            lat_bounds = cls.bounds_from_array(lat, LAT_BOUNDS_STR)
        # Compute the surface area.
        dlon = to_radians(cls.diff_bounds(lon_bounds, lon))
        sinlat_bounds = np.sin(to_radians(lat_bounds))
        dsinlat = np.abs(cls.diff_bounds(sinlat_bounds, lat))
        sfc_area = dlon*dsinlat*(r_e**2)
        # Rename the coordinates such that they match the actual lat / lon.
        try:
            sfc_area = sfc_area.rename({LAT_BOUNDS_STR: LAT_STR,
                                        LON_BOUNDS_STR: LON_STR})
        except ValueError:
            pass
        # Clean up: correct names and dimension order.
        sfc_area = sfc_area.rename('sfc_area')
        sfc_area[LAT_STR] = lat
        sfc_area[LON_STR] = lon
        return sfc_area.transpose()

    def set_grid_data(self):
        """Populate the attrs that hold grid data."""
        if self.grid_data_is_set:
            return
        self._set_mult_grid_attr()
        if not np.any(getattr(self, 'sfc_area', None)):
            try:
                sfc_area = self.grid_sfc_area(self.lon, self.lat,
                                              self.lon_bounds, self.lat_bounds)
            except AttributeError:
                sfc_area = self.grid_sfc_area(self.lon, self.lat)
            self.sfc_area = sfc_area
        # print('\n\n', 'sfc_area', self.sfc_area, '\n\n')
        try:
            self.levs_thick = level_thickness(self.level)
        except AttributeError:
            self.level = None
            self.levs_thick = None
        self.grid_data_is_set = True

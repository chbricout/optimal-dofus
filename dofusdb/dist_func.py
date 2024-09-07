from typing import Dict, Callable
import dofusdb.model as mod
import numpy as np
import itertools
import pandas as pd
from numba import njit


def mean_all_manhattan(subarea_a: mod.SubArea, subarea_b: mod.SubArea) -> int:
    dist = 0
    i = 0
    for map_a, map_b in itertools.product(subarea_a.maps, subarea_b.maps):
        dist += np.sum(np.abs(map_a.coord - map_b.coord))
        i += 1
    return dist / i


def max_all_manhattan(subarea_a: mod.SubArea, subarea_b: mod.SubArea) -> int:
    max_dist = 0

    for map_a, map_b in itertools.product(subarea_a.maps, subarea_b.maps):
        dist = np.sum(np.abs(map_a.coord - map_b.coord))
        if dist > max_dist:
            max_dist = dist
    return max_dist


def mean_manhattan_to_grav(subarea_a: mod.SubArea, subarea_b: mod.SubArea) -> int:
    """This distance is ORIENTED, considered as travel from a to b"""
    dist = 0
    i = 0
    for map_a in subarea_a.maps:
        dist += np.sum(np.abs(subarea_b.gravity_center - map_a.coord))
        i += 1
    return dist / i


def grav_to_grav_manhattan(subarea_a: mod.SubArea, subarea_b: mod.SubArea) -> int:
    return np.sum(np.abs(subarea_a.gravity_center - subarea_b.gravity_center))


def mean_all_eucl(subarea_a: mod.SubArea, subarea_b: mod.SubArea) -> int:
    dist = 0
    i = 0
    for map_a, map_b in itertools.product(subarea_a.maps, subarea_b.maps):
        dist += np.sqrt(np.sum((map_a.coord - map_b.coord) ** 2))
        i += 1
    return dist / i


def max_all_eucl(subarea_a: mod.SubArea, subarea_b: mod.SubArea) -> int:
    max_dist = 0

    for map_a, map_b in itertools.product(subarea_a.maps, subarea_b.maps):
        dist = np.sqrt(np.sum((map_a.coord - map_b.coord) ** 2))
        if dist > max_dist:
            max_dist = dist
    return max_dist


def grav_to_grav_eucl(subarea_a: mod.SubArea, subarea_b: mod.SubArea) -> int:
    return np.sqrt(np.sum((subarea_a.gravity_center - subarea_b.gravity_center) ** 2))


def mean_eucl_to_grav(subarea_a: mod.SubArea, subarea_b: mod.SubArea) -> int:
    """This distance is ORIENTED, considered as travel from a to b"""
    dist = 0
    i = 0
    for map_a in subarea_a.maps:
        dist += np.sqrt(np.sum((subarea_b.gravity_center - map_a.coord) ** 2))
        i += 1
    return dist / i


def compute_distance_df(
    subarea_dict: Dict[str, mod.SubArea],
    dist_func: Callable[[mod.SubArea, mod.SubArea], int],
    is_sym=False,
    index_id=False,
) -> pd.DataFrame:
    zones_name = [name for name in subarea_dict.keys()]
    if index_id:
        index = [sub.idx for sub in subarea_dict.values()]
    else:
        index = zones_name  # assure fix order

    dist_df = pd.DataFrame(columns=index, index=index)

    iterator = (
        itertools.product(zones_name, repeat=2)
        if not is_sym
        else itertools.combinations_with_replacement(zones_name, 2)
    )

    for from_sub, to_sub in iterator:
        if index_id:
            from_id = subarea_dict[from_sub].idx
            to_id = subarea_dict[to_sub].idx
        else:
            from_id = from_sub
            to_id = to_sub

        if subarea_dict[from_sub].worldMapId == subarea_dict[to_sub].worldMapId:

            dist_df.loc[from_id, to_id] = dist_func(
                subarea_dict[from_sub], subarea_dict[to_sub]
            )
            if is_sym:
                dist_df.loc[to_id, from_id] = dist_df.loc[from_id, to_id]
        else:
            dist_df.loc[from_id, to_id] = 10000
            dist_df.loc[to_id, from_id] = 10000

    return dist_df

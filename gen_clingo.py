"""Module pour créer le code ASP et executer clingo"""
from typing import List, Dict
import clingo
import pandas as pd
import dofusdb.sql_loader as loader
import dofusdb.dist_func as dist
import dofusdb.model as mod
import dofusdb.graph_creator as grapher
import itertools
import json
from json import JSONEncoder

db = loader.database("dofusdb.sqlite")


def compute_dist() -> pd.DataFrame:
    subarea_dict_sql = db.load_all_subarea()
    dist_all = dist.compute_distance_df(
        subarea_dict_sql, dist.grav_to_grav_eucl, is_sym=True, index_id=True
    )
    return dist_all


def get_zones(quests: Dict[int, mod.Quest]) -> str:
    dist_mat = compute_dist()
    dist_asp = ""
    subarea_ids = set()
    for quest in quests.values():
        subarea_ids.update(quest.get_subareas())
    subarea_ids.discard(-1)

    for zones in subarea_ids:
        dist_asp += f"zone({zones}).\n"

    for from_id, to_id in itertools.product(subarea_ids, repeat=2):
        dist_asp += (
            f"distance({from_id}, {to_id}, {int(dist_mat.loc[from_id, to_id])}).\n"
        )
    return dist_asp


def get_quests(quests: Dict[int, mod.Quest]) -> Dict[int, mod.Objective]:
    quest_asp = ""
    num_obj = 0
    for quest in quests.values():
        quest_asp += f"quest({quest.idx}).\n"
        for req in quest.requested_quests:
            quest_asp += f"precond({quest.idx}, {req}).\n"
        for obj in quest.objectives:
            quest_asp += f"objective({obj.idx}, {quest.idx}, {obj.sub_area}).\n"
            num_obj += 1
    quest_asp = f"#const n_step={num_obj}.\n" + quest_asp
    return quest_asp


def asp_plan(quests: Dict[int, mod.Quest]) -> List[Dict[int, mod.Objective]]:
    """fonction planificateur utilisant ASP"""

    asp_code = ""
    with open("plan.lp", "r") as file_asp:
        asp_base = file_asp.readlines()
        asp_code = convert_to_asp(quests)

        for line in asp_base:
            asp_code += line

    ctl = clingo.Control(
        [
            "-n 0",
            "-t4",
            
        ]
    )
    ctl.add("base", [], asp_code)
    ctl.ground([("base", [])])
    possible_path=[]
    with ctl.solve(yield_=True) as handle:
        print(handle)
        valid_model = 0
        for model in handle:
            print(f'reached optimality : {model.optimality_proven}')
            print(f"cout actuel : {model.cost}\n")
            if model.optimality_proven:
                chemin = {}
                print(model)
                for atom in model.symbols(atoms=True):
                    if atom.match("do", 2):
                        id_obj, id_quest = atom.arguments[0].arguments
                        for obj in quests[id_quest.number].objectives:
                            if obj.idx == id_obj.number:
                                chemin[atom.arguments[1].number - 1] = obj
                possible_path.append(chemin)

                valid_model+=1
        chemin = {}
        for atom in model.symbols(atoms=True):
            if atom.match("do", 2):
                id_obj, id_quest = atom.arguments[0].arguments
                for obj in quests[id_quest.number].objectives:
                    if obj.idx == id_obj.number:
                        chemin[atom.arguments[1].number - 1] = obj
        possible_path.append(chemin)
            
        return possible_path


def convert_to_asp(quests: Dict[int, mod.Quest]) -> str:
    """Fonction qui convertit nos quetes / objectif en regles ASP"""
    print("create quests")
    asp_code = get_quests(quests)
    print("create zones")

    asp_code += get_zones(quests)
    print("finish gen")
    return asp_code


class MyEncoder(JSONEncoder):
    def default(self, obj):
        return obj.__dict__ 

if __name__ == "__main__":
    quests = db.load_quest_from_category(19)

    paths = asp_plan(quests)
    to_json = []
    for i,path in enumerate(paths):
        dot = grapher.graph_from_quests_for_asp("optimal", quests, path)
        dot.render(f"path_to_incarnam/path_{i}")

        temp_path={}
        for i, obj in path.items():
            temp_path[i]=obj.__dict__()
        to_json.append(temp_path)

    json_paths =json.dumps(to_json)
    with open('path_to_incarnam/paths.json', "w+") as file:
        file.write(json_paths)
from __future__ import annotations

import dofusdb.model as mod
from typing import Dict
import json
import requests as rq


def load_quest_from_category(
    category_id: int, limit: int = 100, lang: str = "fr"
) -> Dict[int, mod.Quest]:
    """Load every quest in a quest category"""
    raw_answer = rq.get(
        f"https://api.dofusdb.fr/quests?categoryId={category_id}&$limit={limit}&$select[]=id"
    )
    quests_json = json.loads(raw_answer.content)
    quests = {el["id"]: load_quest(el["id"], lang) for el in quests_json["data"]}
    if quests_json["total"] > quests_json["limit"]:
        skip = len(quests)
        while len(quests_json["data"]) > 0:
            raw_answer = rq.get(
                f"https://api.dofusdb.fr/quests?categoryId={category_id}&$skip={skip}&$select[]=id"
            )
            quests_json = json.loads(raw_answer.content)
            for el in quests_json["data"]:
                quests[el["id"]] = load_quest(el["id"], lang)
            skip = len(quests)
    return quests


def load_all_quests(lang: str = "fr") -> Dict[int, mod.Quest]:
    """Load every quest in a quest category"""
    raw_answer = rq.get(f"https://api.dofusdb.fr/quests?$select[]=id")
    quests_json = json.loads(raw_answer.content)
    quests = {el["id"]: load_quest(el["id"], lang) for el in quests_json["data"]}
    if quests_json["total"] > quests_json["limit"]:
        skip = len(quests)
        while len(quests_json["data"]) > 0:
            raw_answer = rq.get(
                f"https://api.dofusdb.fr/quests?$skip={skip}&$select[]=id"
            )
            quests_json = json.loads(raw_answer.content)
            for el in quests_json["data"]:
                quests[el["id"]] = load_quest(el["id"], lang)
            skip = len(quests)
    return quests


def load_quest_from_achievement(achievement_id: int) -> Dict[int, mod.Quest]:
    """Load every quest for an achievement, achievement itself is represented as a Quest"""
    achievement = load_achievement(achievement_id)
    quests = {achievement.idx: achievement}
    for r_id in achievement.requested_quests:
        quests[r_id] = load_quest(r_id)

    return quests


def load_quest_and_required(
    quest_id: int, quests_dict: Dict[int, mod.Quest], lang: str = "fr"
):
    """Load a specific quest and any quest required to start."""
    quests_dict[quest_id] = load_quest(quest_id, lang)

    for requested_id in quests_dict[quest_id].requested_quests:
        if requested_id and not requested_id in quests_dict:
            load_quest_and_required(requested_id, quests_dict, lang)


def load_following_quests(
    quest: mod.Quest, quests_dict: Dict[int, mod.Quest], lang: str = "fr"
):
    """Load any quest that are related (forward) to the provided one"""
    following_r = rq.get(
        f"https://api.dofusdb.fr/quests?$skip=0&$select[]=id&startCriterion[$regex]=Qf={quest.idx}($|\)|\|)&lang=fr"
    )
    following_json = json.loads(following_r.content)
    required = {el["id"]: load_quest(el["id"], lang) for el in following_json["data"]}
    for idx, req_quest in required.items():
        if not idx in quests_dict:
            quests_dict[idx] = req_quest
            load_following_quests(quest, quests_dict)


def load_quest(quest_id: int, lang: str = "fr") -> mod.Quest:
    """Load a quest from dofus db"""
    raw_answer = rq.get(f"https://api.dofusdb.fr/quests/{quest_id}")

    quest_json = json.loads(raw_answer.content)
    return mod.quest_from_json(quest_json, lang)


def load_achievement(achievement_id: int) -> mod.Quest:
    """Load an quest achievement as a Quest"""
    raw_answer = rq.get(f"https://api.dofusdb.fr/achievements/{achievement_id}")
    quests_json = json.loads(raw_answer.content)
    return mod.quest_achievement_from_json(quests_json)


def load_subarea(subarea_id: int) -> mod.SubArea:
    raw_answer = rq.get(
        f"https://api.dofusdb.fr/subareas/{subarea_id}?$select[]=id&$select[]=name&$select[]=bounds&$select[]=mapIds"
    )
    subarea_json = json.loads(raw_answer.content)
    subarea_json["maps"] = []
    for map_id in subarea_json["mapIds"]:
        raw_maps = rq.get(
            f"https://api.dofusdb.fr/map-positions/{map_id}?$select[]=id&$select[]=posX&$select[]=posY&$select[]=worldMap"
        )
        subarea_json["maps"].append(json.loads(raw_maps.content))
    return mod.sub_area_from_json(subarea_json)


def load_all_subarea() -> Dict[str, mod.SubArea]:
    subarea_dict = {}
    skip = 0
    loaded = 1
    while loaded != 0:
        raw_answer = rq.get(
            f"https://api.dofusdb.fr/subareas?$skip={skip}&$select[]=id&$select[]=name&$select[]=bounds&$select[]=mapIds"
        )
        data_json = json.loads(raw_answer.content)["data"]
        for subarea_json in data_json:
            subarea_json["maps"] = []
            for map_id in subarea_json["mapIds"]:
                raw_maps = rq.get(
                    f"https://api.dofusdb.fr/map-positions/{map_id}?$select[]=id&$select[]=posX&$select[]=posY&$select[]=worldMap"
                )
                subarea_json["maps"].append(json.loads(raw_maps.content))
            subarea_dict[subarea_json["name"]["fr"]] = mod.sub_area_from_json(
                subarea_json
            )
        loaded = len(data_json)
        skip += loaded
    return subarea_dict


def load_all_subarea_local(sub_file: str, map_file: str) -> Dict[str, mod.SubArea]:
    subarea_dict = {}
    raw_answer = open(sub_file)
    data_json = json.loads(raw_answer.content)["data"]
    for subarea_json in data_json:
        subarea_json["maps"] = []
        for map_id in subarea_json["mapIds"]:
            raw_maps = rq.get(
                f"https://api.dofusdb.fr/map-positions/{map_id}?$select[]=id&$select[]=posX&$select[]=posY&$select[]=worldMap"
            )
            subarea_json["maps"].append(json.loads(raw_maps.content))
        subarea_dict[subarea_json["name"]["fr"]] = mod.sub_area_from_json(subarea_json)
    return subarea_dict

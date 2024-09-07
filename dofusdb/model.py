from __future__ import annotations
from typing import Set, List, Tuple, Any
import re
from dataclasses import dataclass
from enum import Enum
import numpy as np
from numpy.typing import ArrayLike
import sqlite3
import json


class CritTypes(Enum):
    QUEST = "Quest"
    CLASS = "Class"
    POSITION = "Position"
    LEVEL_MIN = "Level min"
    ALIGN_LEVEL_MIN = "Minimum alignment level"
    ALIGN = "Alignement"

    @staticmethod
    def parseCrit(crit_type: str) -> CritTypes:
        match crit_type:
            case "Qf":
                return CritTypes.QUEST
            case "PG":
                return CritTypes.CLASS
            case "Pm":
                return CritTypes.POSITION
            case "PL":
                return CritTypes.LEVEL_MIN
            case "Pa":
                return CritTypes.ALIGN_LEVEL_MIN
            case "Ps":
                return CritTypes.ALIGN


@dataclass
class Position:
    coordinate: Tuple[int, int]
    sub_area_id: int
    area_id: int


@dataclass
class SubArea:
    idx: int
    name: str
    maps: List[Map]
    bound: Bound
    worldMapId: int = 0

    @property
    def gravity_center(self):
        return self.bound.gravity_center


class Bound:
    x: int
    y: int
    width: int
    height: int
    gravity_center: ArrayLike

    def __init__(
        self, x: int, y: int, width: int, height: int, gravity_center: ArrayLike = None
    ) -> None:
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        if gravity_center == None:
            self.gravity_center = np.array([x + width / 2, y + height / 2])
        else:
            self.gravity_center = gravity_center


@dataclass
class Map:
    idx: int
    world_map: int  # indicate on which world the map is (Incarnam, Srambad, etc)
    pos_x: int
    pos_y: int

    @property
    def coord(self) -> ArrayLike:
        return np.array([self.pos_x, self.pos_y])


@dataclass
class Criterion:
    """Criterions requested for a quest, linked by logical 'and'"""

    crit_type: CritTypes
    crit_value: int
    negated: bool = False

    def __hash__(self):
        return hash((self.crit_type, self.crit_value, self.negated))

    def __str__(self):
        match self.crit_type:
            case CritTypes.CLASS:
                return f"Classe = {self.crit_value}"
            case CritTypes.POSITION:
                return f"Position = {self.crit_value}"
            case CritTypes.LEVEL_MIN:
                return f"Niveau > {self.crit_value}"
            case CritTypes.ALIGN_LEVEL_MIN:
                return f"Niveau d'alignement > {self.crit_value}"
            case CritTypes.ALIGN:
                return f"Alignement {'!' if self.negated else ''}= {self.crit_value}"
            case CritTypes.QUEST:
                return str(self.crit_value)
        return "strange"


@dataclass
class LogicalGroup:
    criterions: List[LogicalGroup | Criterion]
    link_type: str  # 'or' or 'and'

    @property
    def quest_ids(self) -> Set[int]:
        ids = set()
        for elements in self.criterions:
            if isinstance(elements,LogicalGroup):
                ids = ids.union(elements.quest_ids)
            elif elements.crit_type == CritTypes.QUEST and not elements.negated:
                ids.add(elements.crit_value)
        return ids.difference(set([None]))

    def is_class_dependent(self):
        """return True if one criterion is class dependent"""
        for element in self.criterions:
            if isinstance(element,LogicalGroup):
                if element.is_class_dependent():
                    return True
            elif element.crit_type == CritTypes.CLASS and element.crit_value is not None:
                return True
        return False

    def get_class_dependent_quests(self) -> Set[int]:
        quests_ids = set()
        for element in self.criterions:
            if type(element) == LogicalGroup and element.is_class_dependent():
                if element.main_op == "or":
                    quests_ids = quests_ids.union(element.get_class_dependent_quests())
                elif element.main_op == "and":
                    quests_ids.add(element.quest_ids)
        quests_ids.discard(None)
        return quests_ids

    def is_class_cluster(self) -> bool:
        """return True if the quest corresponding to the group merge multiple class dependent quests"""
        return self.link_type == "or" and self.is_class_dependent()

    def get_class_cluster(self) -> LogicalGroup:
        if self.link_type == "or":
            for element in self.criterions:
                if isinstance(element,LogicalGroup) :
                    if element.is_class_cluster():
                        return element
                    elif element.link_type == "and" and element.is_class_dependent():
                        return self
                elif (
                    isinstance(element,Criterion) and element.crit_type == CritTypes.CLASS and element.crit_value != None
                ):
                    return self

    def remove_quests(self, quest_ids: Set[int]):
        for element in self.criterions.copy():
            if isinstance(element,LogicalGroup) :
                if len(element.quest_ids.intersection(quest_ids))>0:
                    self.criterions.remove(element)
            elif (
                element.crit_type == CritTypes.QUEST and element.crit_value in quest_ids
            ):
                self.criterions.remove(element)
    


@dataclass
class Quest:
    """Representation of dofus quests for our graph"""

    name: str
    idx: int
    criterions_group: LogicalGroup
    objectives: List[Objective]

    quest_type: str = ""

    @property
    def requested_quests(self) -> Set[int]:
        quests = self.criterions_group.quest_ids
        quests.discard(None)

        return quests

    def get_subareas(self) -> Set[int]:
        sub_areas = set()
        for objective in self.objectives:
            sub_areas.add(objective.sub_area)
        sub_areas.discard(None)
        return sub_areas

    def get_class_cluster(self) -> LogicalGroup:
        return self.criterions_group.get_class_cluster()


@dataclass
class Objective:
    """Represents individual objectives"""

    idx: int
    type_id: int
    parameters: List[int]
    sub_area: int
    text: str

    def __dict__(self):
        return {
            "idx": self.idx,
            "type_id": self.type_id,
            "parameters": self.parameters,
            "sub_area": self.sub_area,
            "text": self.text,
        }


def determine_root_logical_operator(criterion_str: str):
    operator = ""
    parenthese_count = 0
    split_by_group = set()
    buff = ""
    for letter in criterion_str:
        match letter:
            case "(":
                parenthese_count += 1
            case ")":
                parenthese_count -= 1
            case "|":
                if parenthese_count == 0:
                    operator = "or"
                    split_by_group.add(buff)
                    buff = ""
            case "&":
                if parenthese_count == 0:
                    operator = "and"
                    split_by_group.add(buff)
                    buff = ""

        if parenthese_count > 0 or not letter in "|&":
            buff += letter
    split_by_group.add(buff)
    return operator, split_by_group


def parse_objectives(steps, lang="fr") -> List[Objective]:
    objs = []
    for step in steps:
        for objective in step["objectives"]:
            params = []
            for name, p in objective["parameters"].items():
                if "parameter" in name:
                    params.append(int(p))

            text = ""
            for el in objective["text"]:
                if type(el) == str:
                    text += el
                elif type(el) == int:
                    text += str(el)
                elif "name" in el:
                    if isinstance(el["name"], dict):
                        if not lang in el['name']:
                            print(f"missing langage {lang} for quest {el['name']}")
                            first_lang = [*el['name'].keys()][0]
                            text += f"{el['name'][first_lang]} (type: {el['type']})"
                        else:
                            text += f"{el['name'][lang]} (type: {el['type']})"
                    else:
                        text += f"{el['name']} (type: {el['type']})"
            sub_area = None
            if "map" in objective:
                sub_area = int(objective["map"]["subAreaId"])
            objs.append(
                Objective(
                    int(objective["id"]),
                    int(objective["typeId"]),
                    params,
                    sub_area,
                    text,
                )
            )

    return objs


def objective_from_sql(obj_list: sqlite3.Cursor) -> List[Objective]:
    objs = []

    for objective in obj_list:
        params = []
        for i in range(5, 10):
            if objective[i] != -1:
                params.append(objective[i])

        objs.append(
            Objective(
                objective[0],
                objective[1],
                params,
                objective[3],
                objective[2],
            )
        )
    return objs


def criterion_from_str(criterion_str: str) -> LogicalGroup:
    criterion_list = []
    # first we want to detect the "root" logical operator
    main_op, groups = determine_root_logical_operator(criterion_str=criterion_str)

    for crit_group in groups:
        # boolean interpretation of empty string is false
        if crit_group[0] == "(" and "|" in crit_group:
            criterion_list.append(criterion_from_str(crit_group[1:-1]))
        else:
            criterion_list_raw = filter(
                bool, re.findall(r"\(?([\d=>!\w\&]*)\)?\|?", crit_group)
            )
            for criterion_raw in criterion_list_raw:
                criterion = filter(
                    bool, re.findall(r"(\w+)([=>!])(\d+)?", criterion_raw)
                )
                crit_group = [
                    Criterion(
                        crit_type=CritTypes.parseCrit(crit_type),
                        crit_value=int(crit_value),
                        negated=symbole == "!",
                    )
                    for crit_type, symbole, crit_value in criterion
                    if CritTypes.parseCrit(crit_type) != None
                ]
                if len(crit_group) > 0:
                    criterion_list.append(
                        LogicalGroup(
                            crit_group,
                            link_type="and",
                        )
                    )

    return LogicalGroup(criterion_list, link_type=main_op)


def quest_from_json(data: Any, pos_data: Any = None, lang: str = "fr") -> Quest:
    """Create Quest object from dofusdb json"""

    return Quest(
        data["name"][lang],
        data["id"],
        criterion_from_str(data["startCriterion"]),
        parse_objectives(data["steps"]),
    )


def quest_from_sql(
    quest_row: Tuple[int, str, str, int], objectives: List[Objective]
) -> Quest:
    return Quest(
        quest_row[1],
        quest_row[0],
        criterion_from_str(quest_row[2]),
        objectives,
    )


def quest_achievement_from_json(data: Any) -> Quest:
    """Create a achievement quest object from dofusdb json"""
    criterions = set()
    for obj in data["objectives"]:
        new_crit = Criterion(CritTypes.QUEST, int(obj["readableCriterion"][0][1]["id"]))
        criterions.add(new_crit)
    return Quest(
        name=data["name"]["fr"],
        idx=data["id"] * 1000,
        criterions_group=LogicalGroup(criterions, "and"),
        quest_type="Achievement",
        objectives=[],
    )


def bound_from_json(data: Any):
    center_x = data["x"] + (data["width"] / 2)
    center_y = data["y"] + (data["height"] / 2)
    return Bound(
        data["x"],
        data["y"],
        data["width"],
        data["height"],
        np.array([center_x, center_y]),
    )


def map_from_json(data: Any) -> Map:
    return Map(data["id"], data["worldMap"], data["posX"], data["posY"])


def sub_area_from_json(data: Any) -> SubArea:
    maps = []
    for map_json in data["maps"]:
        maps.append(map_from_json(map_json))
    return SubArea(
        data["id"], data["name"]["fr"], maps, bound_from_json(data["bounds"])
    )


def map_from_sql(data: Tuple) -> Map:
    return Map(data[0], data[4], data[1], data[2])


def sub_area_from_sql(data: Tuple) -> SubArea:
    return SubArea(
        data[0], data[1], [], Bound(data[3], data[4], data[5], data[6]), data[7]
    )

from __future__ import annotations

from graphviz import Digraph
import dofusdb.model as mod
import dofusdb.api_loader as al
import dofusdb.graph_creator as gc
from typing import Set, Dict, List
from functools import reduce


def complete_quest_dict(quests_dict: Dict[int, mod.Quest]):
    """Complete the dictionary with every related quest (backward and forward)"""
    added = 1
    len_before = len(quests_dict)
    already_complete = set()
    while added != 0:
        added = 0
        to_complete = quests_dict.keys()
        load_required(quests_dict, already_complete)
        added += len(quests_dict) - len_before

        len_before = len(quests_dict)
        load_following(quests_dict, already_complete)
        added += len(quests_dict) - len_before
        already_complete.union(to_complete)
        print(f"add {added} quest(s)")


def load_required(
    quests_dict: Dict[int, mod.Quest],
    already_complete: Set[int] = set(),
    lang: str = "fr",
):
    """Load any quest required to do all quests in the dictionary"""
    for quest in list(quests_dict.values()):
        if quest.idx not in already_complete:
            for requested_id in quest.requested_quests:
                if not requested_id in quests_dict:
                    al.load_quest_and_required(requested_id, quests_dict, lang)


def load_following(
    quests_dict: Dict[int, mod.Quest], already_complete: Set[int] = set()
):
    """Load any quest linked (forward) to quests in the dictionnary"""
    for quest in list(quests_dict.values()):
        if quest.idx not in already_complete:
            al.load_following_quests(quest, quests_dict)


def remove_inferable_link(quests_dict: Dict[int, mod.Quest]):
    for idx, quest in quests_dict.items():
        for r_id in quest.requested_quests:
            if len(find_longest_path(idx, r_id, quests_dict, [idx])) != 2:
                quest.criterions_group.remove_quests(set([r_id]))


def find_longest_path(
    start_quest: int, end_quest: int, quests_dict: Dict[int, mod.Quest], path: List[int]
) -> List[int]:
    possible_paths = [[]]
    for quest in quests_dict[start_quest].requested_quests:
        if quest == end_quest:
            possible_paths.append(path + [end_quest])
        else:
            possible_paths.append(
                find_longest_path(
                    start_quest=quest,
                    end_quest=end_quest,
                    quests_dict=quests_dict,
                    path=path + [quest],
                )
            )

    max_path = []
    len_max = 0
    for act_path in possible_paths:
        if len(act_path) > len_max:
            max_path = act_path
            len_max = len(max_path)
    return max_path


def detects_quests_with_class_cluster(quests: Dict[int, mod.Quest]) -> Set[int]:
    """Find quest with class dependent required quest"""
    roots = set()
    for idx, quest in quests.items():
        if quest.criterions_group.is_class_cluster():
            roots.add(idx)
    return roots


def prepend_non_dectected_clusters(quests: Dict[int, mod.Quest], detected: Set[int]):
    print(  list(map(lambda x: quests[x].requested_quests, detected)))
    already_detected = reduce(
        set.union, map(lambda x: quests[x].requested_quests, detected)
    ).union(detected)
    detected_for_requested = dict()
    for idx, quest in quests.items():
        if quest.criterions_group.is_class_dependent() and not idx in already_detected:
            for r_id in quest.criterions_group.get_class_dependent_quests():
                if r_id in detected_for_requested:
                    detected_for_requested[r_id].add(idx)
                else:
                    detected_for_requested[r_id] = set([idx])
    for idx, quest_set in detected_for_requested.items():
        quests[idx * 1000] = mod.Quest(
            "artificial quest for class detection",
            idx * 1000,
            mod.LogicalGroup(
                criterions=[mod.Criterion(q, 1, None) for q in quest_set],
                link_type="or",
            ),
            quest_type="artificial",
            objectives=[]
        )
        detected.add(idx * 1000)


def replace_class_dependent_quests(quests: Dict[int, mod.Quest]):
    root_quests = detects_quests_with_class_cluster(quests)
    prepend_non_dectected_clusters(quests, root_quests)

    for quest_id in root_quests:
        to_merge = quests[quest_id].get_class_cluster().quest_ids
        first_ant = to_merge.pop()
        old_crit = quests[first_ant].criterions_group.quest_ids
        new_quest = mod.Quest(
            name="class quest",
            idx=first_ant,
            criterions_group=mod.LogicalGroup(criterions=[mod.Criterion(crit_type=mod.CritTypes.QUEST, crit_value=x) for x in old_crit], link_type="and"),
            quest_type="substitute",
            objectives=[]
        )
        quests[first_ant] = new_quest
        if quests[quest_id].quest_type == "artificial":
            del quests[quest_id]
        else:
            print("removing")
            quests[quest_id].criterions_group.remove_quests(to_merge)

        for to_del in to_merge:
            del quests[to_del]

        quests[quest_id].criterions_group = mod.LogicalGroup(criterions=[mod.Criterion(crit_type=mod.CritTypes.QUEST, crit_value=first_ant)], link_type="and")



def determine_path(
    quest_id: int,
    lang: str = "fr",
    group_criterion: bool = True,
    render_as: str = "svg",
    with_steps: bool = False,
    color_quest=True,
) -> tuple[dict[int, mod.Quest], Digraph]:
    """Determine every required quests to start a specific quest, print path in a graph"""
    quests_dict = {quest_id: al.load_quest(quest_id, lang)}

    load_required(quests_dict, lang=lang)
    remove_inferable_link(quests_dict)
    path = f"path-to-{quest_id}{'-grouped' if group_criterion else ''}{'-steps' if with_steps else ''}{'-colored' if color_quest else ''}"
    dot=None
    if with_steps:
        dot=gc.graph_from_quests_with_objectives(
            path, quests_dict, group_criterion=group_criterion, render_as=render_as
        )
    else:
        dot=gc.graph_from_quests(
            path,
            quests_dict,
            group_criterion=group_criterion,
            render_as=render_as,
            color_quest=color_quest,
        )

    return quests_dict, dot

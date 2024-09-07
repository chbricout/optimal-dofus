from __future__ import annotations
import dofusdb.model as mod
from typing import Dict
from graphviz import Digraph
import itertools
from numpy import random

COLORSCHEME = [
    "black",
    "aliceblue",
    "antiquewhite",
    "aqua",
    "aquamarine",
    "azure",
    "beige",
    "bisque",
    "blanchedalmond",
    "blue",
    "blueviolet",
    "brown",
    "burlywood",
    "cadetblue",
    "chartreuse",
    "chocolate",
    "coral",
    "cornflowerblue",
    "cornsilk",
    "crimson",
    "cyan",
    "darkblue",
    "darkcyan",
    "darkgoldenrod",
    "darkgray",
    "darkgreen",
    "darkkhaki",
    "darkmagenta",
    "darkolivegreen",
    "darkorange",
    "darkorchid",
    "darkred",
    "darksalmon",
    "darkseagreen",
    "darkslateblue",
    "darkslategray",
    "darkturquoise",
    "darkviolet",
    "deeppink",
    "deepskyblue",
    "dimgray",
    "dodgerblue",
    "firebrick",
    "floralwhite",
    "forestgreen",
    "fuchsia",
    "gainsboro",
    "ghostwhite",
    "gold",
    "goldenrod",
    "gray",
    "green",
    "greenyellow",
    "honeydew",
    "hotpink",
    "indianred",
    "indigo",
    "ivory",
    "khaki",
    "lavender",
    "lavenderblush",
    "lawngreen",
    "lemonchiffon",
    "lightblue",
    "lightcoral",
    "lightcyan",
    "lightgoldenrodyellow",
    "lightgray",
    "lightgreen",
    "lightpink",
    "lightsalmon",
    "lightseagreen",
    "lightskyblue",
    "lightslategray",
    "lightsteelblue",
    "lightyellow",
    "lime",
    "limegreen",
    "linen",
    "magenta",
    "maroon",
    "mediumaquamarine",
    "mediumblue",
    "mediumorchid",
    "mediumpurple",
    "mediumseagreen",
    "mediumslateblue",
    "mediumspringgreen",
    "mediumturquoise",
    "mediumvioletred",
    "midnightblue",
    "mintcream",
    "mistyrose",
    "moccasin",
    "navajowhite",
    "navy",
    "oldlace",
    "olive",
    "olivedrab",
    "orange",
    "orangered",
    "orchid",
    "palegoldenrod",
    "palegreen",
    "paleturquoise",
    "palevioletred",
    "papayawhip",
    "peachpuff",
    "peru",
    "pink",
    "plum",
    "powderblue",
    "purple",
    "red",
    "rosybrown",
    "royalblue",
    "saddlebrown",
    "salmon",
    "sandybrown",
    "seagreen",
    "seashell",
    "sienna",
    "silver",
    "skyblue",
    "slateblue",
    "slategray",
    "snow",
    "springgreen",
    "steelblue",
    "tan",
    "teal",
    "thistle",
    "tomato",
    "turquoise",
    "violet",
    "wheat",
    "yellow",
    "yellowgreen",
]


def graph_from_quests(
    graph_name: str,
    quests_dict: Dict[int, mod.Quest],
    group_criterion: bool = True,
    color_quest=True,
    render_as: str | None = "svg",
) -> Digraph:
    """Build a precedence graph from quests dictionary"""
    dot = Digraph(comment=graph_name)

    colors = {}
    if color_quest:
        colors = create_color_dict_from_quests(quests_dict)
    for quest in quests_dict.values():
        name = (
            quest.quest_type + ": " + quest.name
            if quest.quest_type != ""
            else quest.name
        )
        color = "black"
        width = "1"
        subareas = quest.get_subareas()
        if color_quest and len(subareas) > 0:
            try:
                sub = subareas.pop()
                color = COLORSCHEME[colors[sub]]
            except Exception as _   :
                print(f"Sub id {sub}")
                print(f"colors len {len(colors)}")
                print(f"COLORSCHEME len {len(COLORSCHEME)}")

            width = "4"
        dot.node(str(quest.idx), name, color=color, penwidth=width)

        add_logical_group_to_graph(
            quest.idx,
            quest.criterions_group,
            0,
            dot,
            quests_dict,
            group_criterion=group_criterion,
        )

    if render_as is not None:
        dot.format = render_as
        dot.render(graph_name)
    return dot


def graph_from_quests_with_objectives(
    graph_name: str,
    quests_dict: Dict[int, mod.Quest],
    group_criterion: bool = True,
    color_quest=True,
    render_as: str = "svg",
):
    dot = Digraph(comment=graph_name)
    dot.attr(compound="true")

    objectives_edges = {}
    colors = {}
    if color_quest:
        colors = create_color_dict_from_quests(quests_dict)

    for quest in quests_dict.values():
        name = (
            quest.quest_type + ": " + quest.name
            if quest.quest_type != ""
            else quest.name
        )
        color = "black"
        width = "1"
        if color_quest:
            width = "4"
        with dot.subgraph(name=f"cluster_{quest.idx}") as c:
            c.attr(label=name)
            last = ""
            for obj in quest.objectives:
                key = (obj.type_id, tuple(obj.parameters), obj.text)
                if not key in objectives_edges:
                    objectives_edges[key] = [f"obj({obj.idx})"]
                else:
                    objectives_edges[key].append(f"obj({obj.idx})")

                if color_quest:
                    color = COLORSCHEME[colors[obj.sub_area]]
                c.node(f"obj({obj.idx})", obj.text, color=color, penwidth=width)
                if last != "":
                    c.edge(last, f"obj({obj.idx})", style="dotted")
                last = f"obj({obj.idx})"

        add_logical_group_to_graph_cluster(
            f"cluster_{quest.idx}",
            quest.idx,
            quest.criterions_group,
            0,
            dot,
            quests_dict,
            group_criterion=group_criterion,
        )

    for type_id, list_obj in objectives_edges.items():
        if len(list_obj) > 1:
            dot.node(f"typeobj{hash(type_id)}", f"obj:{type_id[2]}", shape="rectangle")
            for obj in list_obj:
                dot.edge(obj, f"typeobj{hash(type_id)}", style="dotted")
    if render_as is not None:
        dot.format = render_as
        dot.render(graph_name)
    return dot


def add_logical_group_to_graph(
    parent_id: int,
    group: mod.LogicalGroup,
    width: int,
    dot: Digraph,
    quests_dict: Dict[int, mod.Quest],
    group_criterion: bool = True,
):
    link_req_to_node = str(parent_id)
    if (
        not parent_id in quests_dict
        and group.link_type != ""
        and len(group.criterions) > 1
    ) or group.link_type == "or":
        dot.node(
            f"{group.link_type}{parent_id}-{width}", group.link_type, shape="diamond"
        )
        dot.edge(f"{group.link_type}{parent_id}-{width}", link_req_to_node)
        link_req_to_node = f"{group.link_type}{parent_id}-{width}"

    i = 0
    for criterion in group.criterions:
        if isinstance(criterion, mod.LogicalGroup):
            add_logical_group_to_graph(
                link_req_to_node,
                criterion,
                i,
                dot,
                quests_dict,
                group_criterion=group_criterion,
            )
            i += 1
        else:
            if criterion.crit_type is mod.CritTypes.QUEST:
                if not criterion.negated:
                    dot.edge(str(criterion.crit_value), link_req_to_node)
            else:
                if group_criterion:
                    dot.node(
                        f"{criterion.crit_type}-{criterion.crit_value}{criterion.negated}",
                        str(criterion),
                        shape="rectangle",
                    )
                    dot.edge(
                        f"{criterion.crit_type}-{criterion.crit_value}{criterion.negated}",
                        link_req_to_node,
                        contraint="false",
                    )
                else:
                    dot.node(
                        f"{link_req_to_node}{criterion.crit_type}-{criterion.crit_value}{criterion.negated}",
                        str(criterion),
                        shape="rectangle",
                    )
                    dot.edge(
                        f"{link_req_to_node}{criterion.crit_type}-{criterion.crit_value}{criterion.negated}",
                        link_req_to_node,
                        contraint="false",
                    )


def add_logical_group_to_graph_cluster(
    original_cluster: str,
    parent_id: int,
    group: mod.LogicalGroup,
    width: int,
    dot: Digraph,
    quests_dict: Dict[int, mod.Quest],
    group_criterion: bool = True,
):
    link_req_to_node = str(parent_id)
    parent_is_cluster = parent_id in quests_dict
    if parent_is_cluster:
        link_req_to_node = f"obj({quests_dict[parent_id].objectives[0].idx})"
    if (
        not parent_id in quests_dict
        and group.link_type != ""
        and len(group.criterions) > 1
    ) or group.link_type == "or":
        dot.node(
            f"{group.link_type}{parent_id}-{width}", group.link_type, shape="diamond"
        )
        dot.edge(
            f"{group.link_type}{parent_id}-{width}",
            link_req_to_node,
            lhead=original_cluster,
        )
        link_req_to_node = f"{group.link_type}{parent_id}-{width}"

    i = 0
    for criterion in group.criterions:
        if isinstance(criterion, mod.LogicalGroup):
            add_logical_group_to_graph_cluster(
                original_cluster,
                link_req_to_node,
                criterion,
                i,
                dot,
                quests_dict,
                group_criterion=group_criterion,
            )
            i += 1
        else:
            if criterion.crit_type is mod.CritTypes.QUEST:
                if not criterion.negated:
                    if True:
                        dot.edge(
                            f"obj({quests_dict[criterion.crit_value].objectives[-1].idx})",
                            link_req_to_node,
                            ltail=f"cluster_{criterion.crit_value}",
                            lhead=original_cluster,
                            minlen="2",
                        )
                    else:
                        dot.edge(
                            f"obj({quests_dict[criterion.crit_value].objectives[-1].idx})",
                            link_req_to_node,
                            ltail=f"cluster_{criterion.crit_value}",
                        )
            else:
                if group_criterion:
                    dot.node(
                        f"{criterion.crit_type}-{criterion.crit_value}{criterion.negated}",
                        str(criterion),
                        shape="rectangle",
                    )
                    if True:
                        dot.edge(
                            f"{criterion.crit_type}-{criterion.crit_value}{criterion.negated}",
                            link_req_to_node,
                            contraint="false",
                            lhead=original_cluster,
                        )
                    else:
                        dot.edge(
                            f"{criterion.crit_type}-{criterion.crit_value}{criterion.negated}",
                            link_req_to_node,
                            contraint="false",
                        )
                else:
                    dot.node(
                        f"{link_req_to_node}{criterion.crit_type}-{criterion.crit_value}{criterion.negated}",
                        str(criterion),
                        shape="rectangle",
                    )
                    if True:
                        dot.edge(
                            f"{link_req_to_node}{criterion.crit_type}-{criterion.crit_value}{criterion.negated}",
                            link_req_to_node,
                            contraint="false",
                            lhead=original_cluster,
                        )

                    else:
                        dot.edge(
                            f"{link_req_to_node}{criterion.crit_type}-{criterion.crit_value}{criterion.negated}",
                            link_req_to_node,
                            contraint="false",
                        )


def create_color_dict_from_quests(quests: Dict[int, mod.Quest]):
    colors = {None: 0}
    i = 0
    for q in quests.values():
        for sub_area in q.get_subareas():
            if not sub_area is None and not sub_area in colors:
                colors[sub_area] = i
                i += 1
    return colors


def graph_from_quests_for_asp(
    graph_name: str,
    quests_dict: Dict[int, mod.Quest],
    plan: Dict[mod.Objective],
    color_quest=True,
    render_as: str = "svg",
) -> Digraph:
    dot = Digraph(comment=graph_name)
    dot.attr(compound="true")

    objectives_edges = {}
    colors = {}
    if color_quest:
        colors = create_color_dict_from_quests(quests_dict)

    for quest in quests_dict.values():
        name = (
            quest.quest_type + ": " + quest.name
            if quest.quest_type != ""
            else quest.name
        )
        for prereq in quest.requested_quests:
            dot.edge(
                f"obj({quests_dict[prereq].objectives[-1].idx})",
                f"obj({quest.objectives[0].idx})",
                lhead=f"cluster_{quest.idx}",
                ltail=f"cluster_{prereq}",
                style="dotted",
                arrowhead=None,
            )
        color = "black"
        width = "1"
        if color_quest:
            width = "4"
        with dot.subgraph(name=f"cluster_{quest.idx}") as c:
            c.attr(label=name)
            last = ""
            for obj in quest.objectives:
                key = (obj.type_id, tuple(obj.parameters), obj.text)
                if not key in objectives_edges:
                    objectives_edges[key] = [f"obj({obj.idx})"]
                else:
                    objectives_edges[key].append(f"obj({obj.idx})")

                if color_quest:
                    color = COLORSCHEME[colors[obj.sub_area]]
                c.node(f"obj({obj.idx})", obj.text, color=color, penwidth=width)
                if last != "":
                    c.edge(last, f"obj({obj.idx})", style="dotted", arrowhead="none")
                last = f"obj({obj.idx})"
    for start, end in itertools.pairwise(range(len(plan))):
        dot.edge(f"obj({plan[start].idx})", f"obj({plan[end].idx})")
    
    if render_as is not None:
        dot.format = render_as
    return dot

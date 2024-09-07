import dofusdb.model as mod

from typing import Dict
import json
import sqlite3


class database:
    def __init__(self, path):
        self.conn = sqlite3.connect(path)

    def load_all_subarea(self) -> Dict[str, mod.SubArea]:
        subarea_dict = {}

        curr = self.conn.execute(
            'SELECT id, "name.fr", mapIds, "bounds.x", "bounds.y", "bounds.width", "bounds.height", worldmapId FROM subareas'
        )

        for subarea_sql in curr:
            subarea = mod.sub_area_from_sql(subarea_sql)
            maps = self.conn.execute(
                f"SELECT * FROM maps where subAreaId={subarea.idx}"
            )
            for map_row in maps:
                subarea.maps.append(mod.map_from_sql(map_row))
            subarea_dict[subarea.name] = subarea
        return subarea_dict

    def load_all_quest(self) -> Dict[int, mod.Quest]:
        quests_req = self.conn.execute(
            'SELECT id, "name.fr", startCriterion, categoryId FROM quests'
        )
        return self.load_quest_from_req(quests_req)

    def load_quest_from_category(self, category_id: int) -> Dict[int, mod.Quest]:
        quests_req = self.conn.execute(
            f'SELECT id, "name.fr", startCriterion, categoryId FROM quests WHERE categoryId={category_id}'
        )

        return self.load_quest_from_req(quests_req)

    def load_quest_from_req(self, quests_req: sqlite3.Cursor) -> Dict[int, mod.Quest]:
        quests_dict = {}

        for quest in quests_req:
            obj_req = self.conn.execute(
                f'SELECT "index", typeId, text, subAreaId, questId, "parameters.parameter0", "parameters.parameter1", "parameters.parameter2", "parameters.parameter3", "parameters.parameter4" FROM objectives WHERE questId={quest[0]}'
            )
            quests_dict[quest[0]] = mod.quest_from_sql(
                quest, mod.objective_from_sql(obj_req)
            )
        return quests_dict

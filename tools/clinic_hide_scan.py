#!/usr/bin/env python3
"""Farida's clinic dressing -> reference/clinic_hide.json (D134).

D137: the dressing is DELETED for good by ArchiveXL (tools/gen_xl.py emits the
'delete' lists as streaming sector nodeDeletions). The D134 runtime hide only
stopped drawing it: collision stayed, and instanced meshes ignored ToggleNode.
D139: the q304 props (QuestPrefabRefHash != 0) are deleted too. The runtime hide
left them drawn, floating where their tables had been, and the user chose an empty
room over keeping Phantom Liberty's q304 dressing. 'hide' lists stay, empty.

Indexes are node SETUP indexes (nodeData), which is what GetNodeSetup(i) takes.
Instanced meshes have one setup per copy, so selection is per setup and a copy
outside the room is never touched. The class of every setup is stored so the
runtime can refuse a sector that another mod or a patch has changed.

    clinic_hide_scan.py <dir with the two sectors serialised to .json>
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "reference", "clinic_hide.json")
DEPOT = "base\\worlds\\03_night_city\\_compiled\\default\\ep1\\"
SECTORS = [("78", "interior_-60_-78_0_0"), ("77", "interior_-60_-77_0_0"), ("ext", "exterior_-30_-39_0_0")]
# D141: the exterior sector carries the whole clinic's lights, fog and doors, so it
# is never box-scanned; only these named q303/q304 props are deleted from it.
# D142: the two blank wall plates the CAUTION decals were painted on. They are
# architecture, so KEEP_PATH keeps them; this setup is both copies and nothing else.
FORCE = {"interior_-60_-78_0_0": {499}}
# D145: the redesign keeps the counter under ac_terminal_pc (22: industrial_table_i).
# D146: the bench under ac_case (531) goes again - the glue draws one central table instead.
KEEP_I = {"interior_-60_-77_0_0": {22}}
NAMED = {"exterior_-30_-39_0_0": {"{q304_farida_faceplate_buyers_guide}", "laptop_1", "q304_farida_shop_sign",
                                   # D144: the lit faceplate jar, its 5 lights and nitrogen fog
                                   "faceplate_tank", "{L_Face_Jar_Back}", "{L_Face_Jar_Bottom_Right}", "{L_Face_Jar_Main}",
                                   "{L_Face_Jar_Bottom_Left}", "{L_Face_Jar_Top}", "StaticParticleNode", "e_liquid_nitrogen_1m_slow"}}
# The room, as D133 measured it (+0.5 m), west edge moved to -1919.5 (D137): the
# sink, IV stand, fridges and medical rack stand past the measured wall line.
BOX = (-1919.5, -1899.0, -2480.2, -2460.7, 23.5, 29.0)
# Kept: the room itself, what makes it render and sound right, and its lights.
KEEP_CLASS = {"worldStaticOccluderMeshNode", "worldStaticSoundEmitterNode", "worldStaticDecalNode"}
KEEP_PATH = ("\\architecture\\", "\\decoration\\lighting\\", "ventilation_shaft_", "wall_vent_")
# Lighting meshes that are really furniture: the surgery lamp arms and desk lamps carry no light.
HIDE_ANYWAY = ("surgery_lamp_", "lab_lamp_", "lamp_desk_", "desk_lamp_",
               # D140: the CAUTION signs are decals, but they read as signage the user wants gone.
               "industrial_lettering_")
# A worldInstancedMeshNode is ONE setup for every copy, placed at the origin with the
# copies in a transform buffer, so its position says nothing. Its buffer bbox does:
# hiding it hides every copy, so take it only when that bbox ends within SLACK of the room.
SLACK = 1.5


def res(n):
    for k in ("mesh", "entityTemplate", "material"):
        v = n.get(k)
        if isinstance(v, dict):
            return v.get("DepotPath", {}).get("$value", "") or ""
    return ""


def main(src):
    out = {"_about": __doc__.strip().splitlines()[0], "box": BOX, "sectors": []}
    for tag, name in SECTORS:
        root = json.load(open(f"{src}/{name}.streamingsector.json"))["Data"]["RootChunk"]
        nd, nodes = root["nodeData"]["Data"], root["nodes"]
        hide, delete, kept = [], [], 0
        for i, e in enumerate(nd):
            n = nodes[e["NodeIndex"]]["Data"]
            if name in NAMED:
                nm = n.get("debugName", {}).get("$value", "")
                if nm in NAMED[name]:
                    delete.append({"i": i, "cls": n["$type"], "name": nm, "res": res(n)})
                continue
            if n["$type"] == "worldInstancedMeshNode":
                b = n["buffer"]["Unknown1"][0]
                lo, hi = b["Min"], b["Max"]
                if not (BOX[0] - SLACK <= lo["X"] and hi["X"] <= BOX[1] + SLACK and BOX[2] - SLACK <= lo["Y"]
                        and hi["Y"] <= BOX[3] + SLACK and BOX[4] - SLACK <= lo["Z"] and hi["Z"] <= BOX[5] + SLACK):
                    continue
            else:
                p = e["Position"]
                if not (BOX[0] <= p["X"] <= BOX[1] and BOX[2] <= p["Y"] <= BOX[3] and BOX[4] <= p["Z"] <= BOX[5]):
                    continue
            cls, path = n["$type"], res(n)
            if i in KEEP_I.get(name, ()):
                kept += 1
                continue
            if i not in FORCE.get(name, ()) and not any(k in path for k in HIDE_ANYWAY) and (cls in KEEP_CLASS or any(k in path for k in KEEP_PATH)):
                kept += 1
                continue
            row = {"i": i, "cls": cls, "name": n.get("debugName", {}).get("$value", ""), "res": path}
            # D139: q304's props (QuestPrefabRefHash != 0) go too; see the docstring.
            delete.append(row)
        refs = [r.get("$value") if isinstance(r, dict) else r for r in root.get("nodeRefs", [])]
        out["sectors"].append({"tag": tag, "path": DEPOT + name + ".streamingsector",
                               "setups": len(nd), "vanilla_refs": refs, "hide": hide, "delete": delete})
        print(f"{name}: {len(nd)} setups, {len(delete)} to delete, {len(hide)} quest props to hide, {kept} kept in the room, {len(refs)} vanilla refs")
    json.dump(out, open(OUT, "w"), indent=1)
    print("->", os.path.normpath(OUT))


if __name__ == "__main__":
    main(sys.argv[1])

#!/usr/bin/env python3
"""
Generate a Gliffy swim-lane flowchart (.gliffy) from dynamically defined lanes.

Usage:
    python create-diagram.py --diagram-name TEXT --lanes-json FILE
      [--confluence-steps-json FILE]
"""

import argparse
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------
LANE_LABEL_W   = 80
BOX_W, BOX_H   = 130, 55
DIA_W, DIA_H   = 120, 75
TERM_W, TERM_H = 100, 40
CONN_W, CONN_H = 36, 36    # row-wrap connector circle
SUB_W,  SUB_H  = 60, 60    # subprocess / lane-entry circle
H_GAP          = 18
V_ROW_GAP      = 140
EXC_V_GAP      = 22
LANE_V_PAD     = 45
CONTENT_X      = LANE_LABEL_W + 20
STEPS_PER_ROW  = 7
LAYER_ID       = "layer0"
MASTER_EXTRA_H = 40         # extra height for loop-back arrow

# ---------------------------------------------------------------------------
# Gliffy UIDs — confirmed from real .gliffy files
# ---------------------------------------------------------------------------
U_PROCESS    = "com.gliffy.shape.flowchart.flowchart_v1.default.process"
U_DECISION   = "com.gliffy.shape.flowchart.flowchart_v1.default.decision"
U_TERMINATOR = "com.gliffy.shape.flowchart.flowchart_v1.default.start_end"
U_CIRCLE     = "com.gliffy.shape.basic.basic_v1.default.circle"
U_RECT       = "com.gliffy.shape.basic.basic_v1.default.rectangle"
U_LINE       = "com.gliffy.shape.basic.basic_v1.default.line"

# Confirmed UID→TID mappings from real Gliffy files.
# NOTE: circle uses ellipse.basic_v1 (NOT circle.basic_v1 which doesn't exist)
_TID_MAP = {
    "com.gliffy.shape.basic.basic_v1.default.rectangle":           "com.gliffy.stencil.rectangle.basic_v1",
    "com.gliffy.shape.basic.basic_v1.default.round_rectangle":     "com.gliffy.stencil.round_rectangle.basic_v1",
    "com.gliffy.shape.basic.basic_v1.default.circle":              "com.gliffy.stencil.ellipse.basic_v1",
    "com.gliffy.shape.flowchart.flowchart_v1.default.process":     "com.gliffy.stencil.rectangle.basic_v1",
    "com.gliffy.shape.flowchart.flowchart_v1.default.decision":    "com.gliffy.stencil.diamond.basic_v1",
    "com.gliffy.shape.flowchart.flowchart_v1.default.start_end":   "com.gliffy.stencil.start_end.flowchart_v1",
    "com.gliffy.shape.flowchart.flowchart_v1.default.connector":   "com.gliffy.stencil.ellipse.basic_v1",
    "com.gliffy.shape.basic.basic_v1.default.line":                None,
}


def get_tid(uid: str) -> str | None:
    return _TID_MAP.get(uid)


# ---------------------------------------------------------------------------
# Colors: (fill, stroke, font-color)
# ---------------------------------------------------------------------------
C_PROCESS    = ("#dae8fc", "#6c8ebf", "#000000")
C_DECISION   = ("#fff2cc", "#d6b656", "#000000")
C_START      = ("#d5e8d4", "#82b366", "#000000")
C_END        = ("#f8cecc", "#b85450", "#b85450")
C_EXCEPTION  = ("#f8cecc", "#b85450", "#b85450")
C_STOP       = ("#f8cecc", "#b85450", "#b85450")
C_CONNECTOR  = ("#FF8000", "#d36000", "#ffffff")   # orange: row connectors + subprocess circles

LINE_COLOR     = "#555555"
LINE_LOOP_CLR  = "#d36000"   # orange dashed for loop-back
LINE_EXC_COLOR = "#b85450"

LANE_PALETTE = [
    ("#eef4ff", "#7aa3cc"),
    ("#efffef", "#7abf7a"),
    ("#fff5f0", "#cc9988"),
    ("#fffbee", "#c9b458"),
    ("#f5eeff", "#9980c9"),
    ("#efffff", "#58b5b5"),
]

# ---------------------------------------------------------------------------
# Step classifiers
# ---------------------------------------------------------------------------
DECISION_RE = re.compile(
    r"\b(check|verif|if\s+there|if\s+any|any\s+active|are\s+there|"
    r"whether|found|exists?|has\s+active|active\s+\w+\s+code)\b",
    re.IGNORECASE,
)
EXCEPTION_ONLY_RE = re.compile(
    r"^(exception|escalat|raise|send\s+(exception|details))",
    re.IGNORECASE,
)


def classify(text: str) -> str:
    if EXCEPTION_ONLY_RE.search(text.strip()):
        return "exception"
    if DECISION_RE.search(text):
        return "decision"
    return "process"


def split_decision(text: str) -> tuple[str, str | None]:
    for pattern in [
        r"\.\s*[Ii]f\s+there\s+is\s+any[,.].*",
        r"\.\s*[Ee]xception.*",
        r",?\s*[Ee]xception\s+the\s+process.*",
    ]:
        m = re.search(pattern, text)
        if m:
            return text[:m.start()].strip(" .,"), text[m.start():].strip(" .,")
    return text, None


def shorten(text: str, max_len: int = 55) -> str:
    return (text[:max_len - 3] + "...") if len(text) > max_len else text


def extract_subprocess_label(step: str) -> str:
    """Extract short lane name from '[Subprocess] ... (LaneName)' step."""
    s = step.replace("[Subprocess]", "").strip()
    m = re.search(r"\(([^)]+)\)", s)
    return m.group(1) if m else (s.split()[0] if s else "Sub")


# ---------------------------------------------------------------------------
# Gliffy JSON builder
# ---------------------------------------------------------------------------

class Gliffy:
    def __init__(self):
        self._bg:    list[dict] = []
        self._lines: list[dict] = []
        self._nodes: list[dict] = []
        self._id: int = 0

    def _nid(self) -> int:
        v = self._id; self._id += 1; return v

    def _text_child(self, w: int, h: int, text: str, font_color: str) -> dict:
        return {
            "x": 0.0, "y": 0.0, "rotation": 0.0, "id": self._nid(),
            "uid": None,
            "width": float(w), "height": float(h),
            "lockAspectRatio": False, "lockShape": False,
            "order": "auto", "hidden": False,
            "flipHorizontal": False, "flipVertical": False,
            "graphic": {
                "type": "Text",
                "Text": {
                    "tid": None,
                    "valign": "middle",
                    "overflow": "none",
                    "vposition": "none",
                    "hposition": "none",
                    "type": "fixed",
                    "lineTValue": None, "linePerpValue": None,
                    "cardinalityType": None,
                    "html": (
                        f'<p style="text-align:center;">'
                        f'<span style="font-family:Arial;font-size:10px;'
                        f'color:{font_color};">{text}</span></p>'
                    ),
                    "paddingLeft": 5, "paddingRight": 5,
                    "paddingBottom": 5, "paddingTop": 5,
                    "outerPaddingLeft": 6, "outerPaddingRight": 6,
                    "outerPaddingBottom": 2, "outerPaddingTop": 6,
                }
            },
            "children": [],
            "layerId": LAYER_ID,
            "constraints": {"constraints": []},
        }

    def _make(self, uid: str, x: int, y: int, w: int, h: int,
              fill: str, stroke: str, font_color: str,
              text: str, rotation: int = 0,
              stroke_w: float = 1.5) -> dict:
        node_id = self._nid()
        return {
            "x": float(x), "y": float(y), "rotation": float(rotation),
            "id": node_id,
            "uid": uid,
            "width": float(w), "height": float(h),
            "lockAspectRatio": False, "lockShape": False,
            "order": node_id, "hidden": False,
            "flipHorizontal": False, "flipVertical": False,
            "graphic": {
                "type": "Shape",
                "Shape": {
                    "tid": get_tid(uid),
                    "strokeWidth": stroke_w,
                    "strokeColor": stroke,
                    "fillColor": fill,
                    "gradient": False, "dashStyle": None,
                    "dropShadow": False, "state": 0,
                    "shadowX": 0.0, "shadowY": 0.0,
                    "opacity": 1.0,
                }
            },
            "children": [self._text_child(w, h, text, font_color)] if text else [],
            "layerId": LAYER_ID,
            "linkMap": [],
        }

    def node(self, uid: str, x: int, y: int, w: int, h: int,
             fill: str, stroke: str, font_color: str, text: str) -> int:
        s = self._make(uid, x, y, w, h, fill, stroke, font_color, text)
        self._nodes.append(s)
        return s["id"]

    def bg_rect(self, x: int, y: int, w: int, h: int,
                fill: str, stroke: str, stroke_w: float = 2.0,
                text: str = "", font_color: str = "#333333",
                rotation: int = 0) -> int:
        s = self._make(U_RECT, x, y, w, h, fill, stroke, font_color,
                       text, rotation=rotation, stroke_w=stroke_w)
        s["order"] = 0
        self._bg.append(s)
        return s["id"]

    def line(self, src_id: int, dst_id: int,
             src_px: float, src_py: float,
             dst_px: float, dst_py: float,
             color: str = LINE_COLOR, label: str = "",
             dashed: bool = False) -> int:
        line_id = self._nid()
        children = []
        if label:
            lbl_id = self._nid()
            children = [{
                "x": 0.0, "y": 0.0, "rotation": 0.0, "id": lbl_id,
                "uid": None, "width": 60.0, "height": 20.0,
                "lockAspectRatio": False, "lockShape": False,
                "order": "auto", "hidden": False,
                "flipHorizontal": False, "flipVertical": False,
                "graphic": {
                    "type": "Text",
                    "Text": {
                        "tid": None, "valign": "top",
                        "overflow": "none", "vposition": "none", "hposition": "none",
                        "type": "fixed",
                        "lineTValue": 0.5, "linePerpValue": None,
                        "cardinalityType": None,
                        "html": (
                            f'<p><span style="font-family:Arial;font-size:9px;'
                            f'color:{color};">{label}</span></p>'
                        ),
                        "paddingLeft": 2, "paddingRight": 2,
                        "paddingBottom": 2, "paddingTop": 2,
                        "outerPaddingLeft": 6, "outerPaddingRight": 6,
                        "outerPaddingBottom": 2, "outerPaddingTop": 6,
                    }
                },
                "children": [],
                "layerId": LAYER_ID,
                "constraints": {"constraints": []},
            }]
        s = {
            "x": 0.0, "y": 0.0, "rotation": 0.0, "id": line_id,
            "uid": U_LINE,
            "width": 10.0, "height": 10.0,
            "lockAspectRatio": False, "lockShape": False,
            "order": 0, "hidden": False,
            "flipHorizontal": False, "flipVertical": False,
            "graphic": {
                "type": "Line",
                "Line": {
                    "strokeWidth": 1.5, "strokeColor": color,
                    "fillColor": "none",
                    "dashStyle": "8.0,4.0" if dashed else None,
                    "startArrow": 0, "endArrow": 1,
                    "startArrowRotation": "auto",
                    "endArrowRotation": "auto",
                    "ortho": False,
                    "interpolationType": "linear",
                    "cornerRadius": None,
                    "controlPath": [[0.0, 0.0], [10.0, 0.0]],
                    "lockSegments": {},
                }
            },
            "constraints": {
                "constraints": [],
                "startConstraint": {
                    "type": "StartPositionConstraint",
                    "StartPositionConstraint": {
                        "nodeId": src_id, "px": src_px, "py": src_py,
                    }
                },
                "endConstraint": {
                    "type": "EndPositionConstraint",
                    "EndPositionConstraint": {
                        "nodeId": dst_id, "px": dst_px, "py": dst_py,
                    }
                },
            },
            "children": children,
            "layerId": LAYER_ID,
            "linkMap": [],
        }
        self._lines.append(s)
        return line_id

    def free_line(self, control_path: list[list[float]],
                  color: str = LINE_COLOR, dashed: bool = False,
                  label: str = "") -> int:
        """Unconstrained line using absolute-coordinate control path."""
        line_id = self._nid()
        children = []
        if label:
            lbl_id = self._nid()
            children = [{
                "x": 0.0, "y": 0.0, "rotation": 0.0, "id": lbl_id,
                "uid": None, "width": 50.0, "height": 18.0,
                "lockAspectRatio": False, "lockShape": False,
                "order": "auto", "hidden": False,
                "flipHorizontal": False, "flipVertical": False,
                "graphic": {
                    "type": "Text",
                    "Text": {
                        "tid": None, "valign": "top",
                        "overflow": "none", "vposition": "none", "hposition": "none",
                        "type": "fixed", "lineTValue": 0.15, "linePerpValue": None,
                        "cardinalityType": None,
                        "html": (
                            f'<p><span style="font-family:Arial;font-size:9px;'
                            f'color:{color};">{label}</span></p>'
                        ),
                        "paddingLeft": 2, "paddingRight": 2,
                        "paddingBottom": 2, "paddingTop": 2,
                        "outerPaddingLeft": 6, "outerPaddingRight": 6,
                        "outerPaddingBottom": 2, "outerPaddingTop": 6,
                    }
                },
                "children": [], "layerId": LAYER_ID,
                "constraints": {"constraints": []},
            }]
        # controlPath is relative to line x,y; set line at first point
        ox, oy = control_path[0]
        rel_path = [[p[0] - ox, p[1] - oy] for p in control_path]
        s = {
            "x": float(ox), "y": float(oy), "rotation": 0.0, "id": line_id,
            "uid": U_LINE, "width": 10.0, "height": 10.0,
            "lockAspectRatio": False, "lockShape": False,
            "order": 0, "hidden": False,
            "flipHorizontal": False, "flipVertical": False,
            "graphic": {
                "type": "Line",
                "Line": {
                    "strokeWidth": 1.5, "strokeColor": color,
                    "fillColor": "none",
                    "dashStyle": "8.0,4.0" if dashed else None,
                    "startArrow": 0, "endArrow": 1,
                    "startArrowRotation": "auto", "endArrowRotation": "auto",
                    "ortho": False, "interpolationType": "linear",
                    "cornerRadius": None,
                    "controlPath": rel_path,
                    "lockSegments": {},
                }
            },
            "constraints": {"constraints": []},
            "children": children, "layerId": LAYER_ID, "linkMap": [],
        }
        self._lines.append(s)
        return line_id

    def all_objects(self) -> list[dict]:
        return self._bg + self._lines + self._nodes

    def to_gliffy(self, title: str) -> dict:
        all_o = self.all_objects()
        x2s = [s["x"] + s["width"]  for s in all_o] + [800.0]
        y2s = [s["y"] + s["height"] for s in all_o] + [400.0]
        xs  = [s["x"] for s in all_o] + [0.0]
        ys  = [s["y"] for s in all_o] + [0.0]
        w = int(max(x2s)) + 80
        h = int(max(y2s)) + 80
        return {
            "contentType": "application/gliffy+json",
            "version": "1.3",
            "metadata": {
                "title": title,
                "revision": 0,
                "exportBorder": False,
                "loadPosition": "default",
                "libraries": [
                    "com.gliffy.libraries.basic.basic_v1.default",
                    "com.gliffy.libraries.flowchart.flowchart_v1.default",
                ],
                "lastSerialized": 1,
                "analyticsProduct": "",
            },
            "embeddedResources": {"index": 0, "resources": []},
            "stage": {
                "background": "#FFFFFF",
                "width": w, "height": h,
                "maxWidth": 5000, "maxHeight": 5000,
                "exportBorder": False,
                "gridOn": True, "snapToGrid": True,
                "drawingGuidesOn": True, "pageBreaksOn": False,
                "printGridOn": False, "printPaper": "LETTER",
                "printShrinkToFit": False, "printPortrait": False,
                "autoFit": True,
                "fitBB": {
                    "min": {"x": int(min(xs)), "y": int(min(ys))},
                    "max": {"x": int(max(x2s)), "y": int(max(y2s))},
                },
                "viewportType": "default",
                "nodeIndex": self._id,
                "shapeStyles": {}, "lineStyles": {}, "textStyles": {},
                "themeData": None,
                "layers": [{
                    "guid": LAYER_ID, "order": 0, "name": "Layer 0",
                    "active": True, "locked": False,
                    "visible": True, "nodeIndex": 100,
                }],
                "objects": all_o,
            },
        }


# ---------------------------------------------------------------------------
# Height calculators
# ---------------------------------------------------------------------------

def master_lane_height(subprocess_count: int) -> int:
    """Master is a single row; extra height below for loop-back arrow."""
    return 2 * LANE_V_PAD + DIA_H + MASTER_EXTRA_H


def subprocess_lane_height(steps: list[str]) -> int:
    n_rows = max(1, -(-len(steps) // STEPS_PER_ROW))
    h = 2 * LANE_V_PAD + BOX_H + max(0, n_rows - 1) * V_ROW_GAP
    has_exc = any(
        split_decision(s)[1] is not None
        for s in steps if classify(s) == "decision"
    )
    if has_exc:
        h += EXC_V_GAP + BOX_H + EXC_V_GAP + TERM_H + 10
    return h


# ---------------------------------------------------------------------------
# Master lane builder
# ---------------------------------------------------------------------------

def build_master_lane(g: Gliffy, system_name: str,
                      subprocess_names: list[str],
                      lane_top: int) -> dict:
    """
    Auto-build the Master orchestration lane.
    Flow: START → Check availability → Inserter → [subprocesses]
          → More work? → No: audit report → END
                       → Yes: loop-back (drawn separately)
    Returns node positions needed for the loop-back arrow.
    """
    row_cy = lane_top + LANE_V_PAD + DIA_H // 2
    cur_x  = CONTENT_X

    # START
    prev_id = g.node(U_TERMINATOR, cur_x, row_cy - TERM_H // 2,
                     TERM_W, TERM_H, *C_START, "START")
    cur_x += TERM_W + H_GAP

    # Check system availability
    avail_id = g.node(U_DECISION, cur_x, row_cy - DIA_H // 2,
                      DIA_W, DIA_H, *C_DECISION,
                      shorten(f"Check {system_name} availability"))
    g.line(prev_id, avail_id, 1.0, 0.5, 0.0, 0.5)
    # Unavailable → STOP (drops below)
    exc_y   = row_cy + DIA_H // 2 + EXC_V_GAP
    stop_id = g.node(U_TERMINATOR, cur_x + (DIA_W - TERM_W) // 2,
                     exc_y, TERM_W, TERM_H, *C_STOP, "STOP")
    g.line(avail_id, stop_id, 0.5, 1.0, 0.5, 0.0, LINE_EXC_COLOR, "Unavailable")
    cur_x += DIA_W + H_GAP
    prev_id = avail_id

    # Inserter subprocess call — record position for loop-back
    ins_x, ins_y = cur_x, row_cy - SUB_H // 2
    ins_id = g.node(U_CIRCLE, ins_x, ins_y, SUB_W, SUB_H,
                    *C_CONNECTOR, "Inserter")
    g.line(prev_id, ins_id, 1.0, 0.5, 0.0, 0.5, LINE_COLOR, "Available")
    cur_x  += SUB_W + H_GAP
    prev_id = ins_id

    # Subprocess lane calls
    for name in subprocess_names:
        sid = g.node(U_CIRCLE, cur_x, row_cy - SUB_H // 2,
                     SUB_W, SUB_H, *C_CONNECTOR, shorten(name, 18))
        g.line(prev_id, sid, 1.0, 0.5, 0.0, 0.5)
        cur_x  += SUB_W + H_GAP
        prev_id = sid

    # "More work available?" decision — record position for loop-back
    mw_x, mw_y = cur_x, row_cy - DIA_H // 2
    mw_id = g.node(U_DECISION, mw_x, mw_y, DIA_W, DIA_H,
                   *C_DECISION, "More work available?")
    g.line(prev_id, mw_id, 1.0, 0.5, 0.0, 0.5)
    cur_x  += DIA_W + H_GAP

    # No → Create audit report → END
    audit_id = g.node(U_PROCESS, cur_x, row_cy - BOX_H // 2,
                      BOX_W, BOX_H, *C_PROCESS, "Create audit report")
    g.line(mw_id, audit_id, 1.0, 0.5, 0.0, 0.5, LINE_COLOR, "No")
    cur_x += BOX_W + H_GAP

    end_id = g.node(U_TERMINATOR, cur_x, row_cy - TERM_H // 2,
                    TERM_W, TERM_H, *C_END, "END")
    g.line(audit_id, end_id, 1.0, 0.5, 0.0, 0.5)

    return {"ins_x": ins_x, "ins_y": ins_y,
            "mw_x":  mw_x,  "mw_y":  mw_y}


def add_loop_back(g: Gliffy, master_info: dict) -> None:
    """
    Draw the dashed 'Yes' loop-back from 'More work?' bottom
    down → left → up to Inserter circle bottom.
    """
    ins_cx     = master_info["ins_x"] + SUB_W / 2
    ins_bottom = master_info["ins_y"] + SUB_H
    mw_cx      = master_info["mw_x"]  + DIA_W / 2
    mw_bottom  = master_info["mw_y"]  + DIA_H
    loop_y     = mw_bottom + 22

    g.free_line(
        [[mw_cx, mw_bottom], [mw_cx, loop_y], [ins_cx, loop_y], [ins_cx, ins_bottom]],
        color=LINE_LOOP_CLR, dashed=True, label="Yes",
    )


# ---------------------------------------------------------------------------
# Inserter lane (Lane 2) — always auto-generated
# ---------------------------------------------------------------------------

def build_inserter_lane(g: Gliffy, inserter_source: str, lane_top: int) -> None:
    layout_subprocess_lane(
        g,
        steps=[f"Get work from {inserter_source}", "Insert record to database"],
        lane_top=lane_top,
        entry_label="Inserter",
    )


# ---------------------------------------------------------------------------
# Generic subprocess lane layout (Lane 3+)
# ---------------------------------------------------------------------------

def layout_subprocess_lane(g: Gliffy, steps: list[str],
                            lane_top: int, entry_label: str) -> None:
    """
    Entry orange circle → steps (with row wrapping) → Return to Master orange circle.
    """
    row_cy    = lane_top + LANE_V_PAD + BOX_H // 2
    cur_x     = CONTENT_X
    row_count = 0
    conn_num  = 1

    classified: list[tuple[str, str, str | None]] = []
    for step in steps:
        kind = classify(step)
        if kind == "decision":
            cond, exc = split_decision(step)
            classified.append(("decision", shorten(cond), shorten(exc) if exc else None))
        else:
            classified.append((kind, shorten(step), None))

    # Entry circle
    prev_id = g.node(U_CIRCLE, cur_x, row_cy - SUB_H // 2,
                     SUB_W, SUB_H, *C_CONNECTOR, shorten(entry_label, 18))
    cur_x += SUB_W + H_GAP

    for kind, label, exc_label in classified:
        # Row wrap
        if row_count >= STEPS_PER_ROW:
            out_id = g.node(U_CIRCLE, cur_x, row_cy - CONN_H // 2,
                            CONN_W, CONN_H, *C_CONNECTOR, str(conn_num))
            g.line(prev_id, out_id, 1.0, 0.5, 0.0, 0.5)
            row_cy += V_ROW_GAP
            in_id = g.node(U_CIRCLE, cur_x, row_cy - CONN_H // 2,
                           CONN_W, CONN_H, *C_CONNECTOR, str(conn_num))
            g.line(out_id, in_id, 0.5, 1.0, 0.5, 0.0)
            conn_num += 1
            prev_id = in_id
            cur_x   += CONN_W + H_GAP
            row_count = 0

        if kind == "decision":
            sid = g.node(U_DECISION, cur_x, row_cy - DIA_H // 2,
                         DIA_W, DIA_H, *C_DECISION, label)
            g.line(prev_id, sid, 1.0, 0.5, 0.0, 0.5, LINE_COLOR, "Yes")
            if exc_label:
                exc_y  = row_cy + DIA_H // 2 + EXC_V_GAP
                exc_id = g.node(U_PROCESS, cur_x, exc_y,
                                BOX_W, BOX_H, *C_EXCEPTION, exc_label)
                g.line(sid, exc_id, 0.5, 1.0, 0.5, 0.0, LINE_EXC_COLOR, "No")
                stp_id = g.node(U_TERMINATOR,
                                cur_x + (BOX_W - TERM_W) // 2,
                                exc_y + BOX_H + EXC_V_GAP,
                                TERM_W, TERM_H, *C_STOP, "STOP")
                g.line(exc_id, stp_id, 0.5, 1.0, 0.5, 0.0, LINE_EXC_COLOR)
            prev_id = sid
            cur_x  += DIA_W + H_GAP

        elif kind == "exception":
            sid = g.node(U_PROCESS, cur_x, row_cy - BOX_H // 2,
                         BOX_W, BOX_H, *C_EXCEPTION, label)
            g.line(prev_id, sid, 1.0, 0.5, 0.0, 0.5)
            prev_id = sid
            cur_x  += BOX_W + H_GAP

        else:
            sid = g.node(U_PROCESS, cur_x, row_cy - BOX_H // 2,
                         BOX_W, BOX_H, *C_PROCESS, label)
            g.line(prev_id, sid, 1.0, 0.5, 0.0, 0.5)
            prev_id = sid
            cur_x  += BOX_W + H_GAP

        row_count += 1

    # Return to Master circle
    ret_id = g.node(U_CIRCLE, cur_x, row_cy - SUB_H // 2,
                    SUB_W, SUB_H, *C_CONNECTOR, "→ Master")
    g.line(prev_id, ret_id, 1.0, 0.5, 0.0, 0.5)


# ---------------------------------------------------------------------------
# Diagram assembly
# ---------------------------------------------------------------------------

def build_diagram(diagram_name: str, system_name: str,
                  inserter_source: str,
                  subprocess_lanes: list[dict]) -> dict:
    g = Gliffy()

    sub_names  = [l["name"] for l in subprocess_lanes]
    master_h   = master_lane_height(len(sub_names))
    inserter_h = subprocess_lane_height(["get work", "insert"])
    sub_hs     = [subprocess_lane_height(l["steps"]) for l in subprocess_lanes]

    tops: list[int] = []
    y = 0
    for h in [master_h, inserter_h] + sub_hs:
        tops.append(y); y += h
    total_h = y

    # Master lane width
    master_w = (CONTENT_X + TERM_W + H_GAP + DIA_W + H_GAP
                + (1 + len(sub_names)) * (SUB_W + H_GAP)
                + DIA_W + H_GAP + BOX_W + H_GAP + TERM_W + 100)

    # Subprocess lane row width: entry circle + STEPS_PER_ROW steps + return circle
    sub_row_w = (CONTENT_X + (SUB_W + H_GAP)
                 + STEPS_PER_ROW * (max(BOX_W, DIA_W) + H_GAP)
                 + (SUB_W + H_GAP) + 60)

    diagram_w = max(master_w, sub_row_w)

    # Pool outline
    g.bg_rect(0, 0, diagram_w, total_h, "none", "#555555", stroke_w=2.5)

    # Lane backgrounds + rotated labels
    all_lanes   = [{"name": "Master"}, {"name": "Inserter"}] + \
                  [{"name": l["name"]} for l in subprocess_lanes]
    all_heights = [master_h, inserter_h] + sub_hs

    for i, (lane, h, top) in enumerate(zip(all_lanes, all_heights, tops)):
        bg_fill, bg_stroke = LANE_PALETTE[i % len(LANE_PALETTE)]
        g.bg_rect(0, top, diagram_w, h, bg_fill, bg_stroke)
        g.bg_rect(0, top, LANE_LABEL_W, h, "#e0e0e0", "#555555", stroke_w=1.0)
        lbl_w = max(h - 10, 60)
        lbl_h = LANE_LABEL_W - 10
        g.bg_rect(
            LANE_LABEL_W // 2 - lbl_w // 2, top + h // 2 - lbl_h // 2,
            lbl_w, lbl_h, "none", "none", stroke_w=0.0,
            text=lane["name"], font_color="#333333", rotation=270,
        )

    # Build content
    master_info = build_master_lane(g, system_name, sub_names, tops[0])
    build_inserter_lane(g, inserter_source, tops[1])
    for lane, top in zip(subprocess_lanes, tops[2:]):
        layout_subprocess_lane(g, lane["steps"], top, entry_label=lane["name"])
    add_loop_back(g, master_info)

    return g.to_gliffy(diagram_name)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--diagram-name", required=True)
    p.add_argument("--config-json",  required=True,
                   help="JSON: {system_name, inserter_source, subprocess_lanes:[{name, steps}]}")
    p.add_argument("--confluence-steps-json", default="",
                   help="Steps JSON from fetch-steps.py")
    p.add_argument("--confluence-lane-name", default="",
                   help="Subprocess lane name to inject Confluence steps into")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    with open(args.config_json, encoding="utf-8") as f:
        cfg = json.load(f)

    system_name      = cfg.get("system_name", "System")
    inserter_source  = cfg.get("inserter_source", "work source")
    subprocess_lanes = cfg.get("subprocess_lanes", [])

    if not subprocess_lanes:
        print("Error: No subprocess_lanes defined.", file=sys.stderr); sys.exit(1)

    if args.confluence_steps_json:
        with open(args.confluence_steps_json, encoding="utf-8") as f:
            raw = [s.strip() for s in json.load(f).get("steps", []) if s.strip()]
        target = args.confluence_lane_name
        for lane in subprocess_lanes:
            if (not target and lane.get("confluence_lane")) or lane["name"] == target:
                lane["steps"] = raw; break

    for lane in subprocess_lanes:
        if not lane.get("steps"):
            print(f"Error: Lane '{lane.get('name','?')}' has no steps.",
                  file=sys.stderr); sys.exit(1)

    diagram = build_diagram(args.diagram_name, system_name,
                            inserter_source, subprocess_lanes)

    safe = re.sub(r"[^\w\- ]", "_", args.diagram_name).strip()
    out  = Path.home() / "Downloads" / f"{safe}.gliffy"
    out.write_text(json.dumps(diagram, indent=2), encoding="utf-8")

    print(json.dumps({
        "diagram_name":    args.diagram_name,
        "diagram_file":    str(out),
        "system_name":     system_name,
        "inserter_source": inserter_source,
        "subprocess_lanes": [
            {"name": l["name"], "steps": len(l["steps"])} for l in subprocess_lanes
        ],
        "status": "saved",
    }, indent=2))
    print(f"\nSaved: {out}", file=sys.stderr)


if __name__ == "__main__":
    main()

"""FreeCAD regression tests for the parameterized neck and its connections.

Run with a Python interpreter that can import FreeCAD and Part. The macro's
geometry is executed without its GUI, export or TechDraw side effects.
"""

import ast
import math
from pathlib import Path
import unittest


MACRO = Path(__file__).resolve().parents[1] / "dewar_xb200_long_neck.py"


def build_geometry(overrides=None, section=False):
    """Override INPUT assignments, so all derived dimensions are recomputed."""
    tree = ast.parse(MACRO.read_text(encoding="utf-8"), filename=str(MACRO))
    overrides = dict(overrides or {})
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in overrides:
                node.value = ast.copy_location(ast.Constant(overrides.pop(name)), node.value)
    if overrides:
        raise AssertionError("Unknown macro parameters: %s" % sorted(overrides))
    # Include parameter / geometry validation, but never create documents.
    stop = next(i for i, node in enumerate(tree.body)
                if isinstance(node, ast.If) and isinstance(node.test, ast.Name)
                and node.test.id == "SECTION_VIEW")
    body = tree.body[:stop + 1] if section else tree.body[:stop]
    namespace = {"__name__": "dewar_parameter_test"}
    exec(compile(ast.fix_missing_locations(ast.Module(body=body, type_ignores=[])),
                 str(MACRO), "exec"), namespace)
    return namespace


class DewarParameterTests(unittest.TestCase):
    def check_geometry(self, p):
        for name, shape, color in p["parts"]:
            self.assertTrue(shape.isValid(), name)
            self.assertEqual(len(shape.Solids), 1, name)
        pts = p["inner_pts"]
        crest = p["NECK_BORE_R"] + p["RIB_AMPL"]
        self.assertEqual(pts[0], (crest, p["z_c0"]))
        self.assertEqual(pts[-1], (crest, p["z_nt"]))
        self.assertEqual(len(pts), 2 * p["n_rib"] + 1)
        self.assertTrue(all(a[1] < b[1] for a, b in zip(pts, pts[1:])))
        self.assertEqual(min(r for r, z in pts), p["NECK_BORE_R"])
        # Every flank is angled; there are no cylindrical dwell bands or cuffs.
        for (ra, za), (rb, zb) in zip(pts, pts[1:]):
            dr, dz = rb - ra, zb - za
            self.assertAlmostEqual(abs(dr), p["RIB_AMPL"])
            self.assertAlmostEqual(dz, p["pitch"] / 2.0)
            normal_wall = p["rib_radial_wall"] * dz / math.hypot(dr, dz)
            self.assertAlmostEqual(normal_wall, p["RIB_WALL"])
        # The cone wall angle matches the requested RIB_ANGLE.
        self.assertAlmostEqual(
            math.degrees(math.atan(2.0 * p["RIB_AMPL"] / p["pitch"])),
            p["RIB_ANGLE"], delta=2.0)
        for face in p["neck_corrug"].Faces:
            self.assertNotEqual(type(face.Surface).__name__, "Cylinder")
        self.assertAlmostEqual(p["neck_corrug"].BoundBox.ZMax, p["z_nt"], places=5)
        self.assertTrue(any(type(f.Surface).__name__ == "Cone"
                            and f.BoundBox.ZMax >= p["z_nt"] - 1e-6
                            for f in p["neck_corrug"].Faces))
        self.assertNotIn("COLLAR_LEN", p)
        self.assertAlmostEqual(p["NECK_OUT_R_IN"] - p["NECK_CORRUG_OUT_R"],
                               p["NECK_GAP"])
        # Width parametrisation: jacket and skirt follow the vessel radius.
        self.assertAlmostEqual(p["JAC_R_OUT"],
                               p["VES_R_IN"] + p["VES_T"] + p["RADIAL_GAP"] + p["JAC_T"])
        self.assertAlmostEqual(p["SKIRT_R"], p["JAC_R_OUT"] - p["SKIRT_INSET"])
        # Both tube bottoms are flush with the curved cavity surfaces, with
        # no material extending into either body cavity below the joint.
        for tube, cavity in (("neck_corrug", "ves_cavity"),
                             ("neck_outer", "jac_cavity")):
            self.assertLess(p[tube].common(p[cavity]).Volume, 1e-5, tube)
        lowest_inner_head = p["z_v1"] + p["VES_HEAD_D"] - p["cap_height"](
            p["VES_R_IN"], p["VES_HEAD_D"], p["NECK_CORRUG_OUT_R"])
        highest_inner_head = p["z_v1"] + p["VES_HEAD_D"] - p["cap_height"](
            p["VES_R_IN"], p["VES_HEAD_D"], p["NECK_BORE_R"])
        outer_bottom = p["z_ja"] - p["cap_height"](
            p["jac_r_in"], p["JAC_HEAD_D"], p["NECK_OUT_R_OUT"])
        self.assertGreaterEqual(p["neck_corrug"].BoundBox.ZMin, lowest_inner_head - 1e-6)
        self.assertLessEqual(p["neck_corrug"].BoundBox.ZMin, highest_inner_head + 1e-6)
        self.assertAlmostEqual(p["neck_outer"].BoundBox.ZMin, outer_bottom, places=5)
        self.assertLessEqual(p["cork_len"], p["CORK_LEN"])
        self.assertGreaterEqual(p["zc"] - p["cork_len"],
                                p["z_cork_limit"] - 1e-8)
        for name in ("neck_corrug", "neck_outer", "ves_shell"):
            self.assertLess(p["cork"].common(p[name]).Volume, 1e-5, name)
        # Profile-matched vessel and flange openings must have no metal overlap.
        for name in ("ves_shell", "neck_outer"):
            self.assertLess(p[name].common(p["neck_envelope"]).Volume, 1e-5, name)
        self.assertLess(p["neck_corrug"].common(p["ves_shell"]).Volume, 1e-5)
        self.assertLess(p["neck_corrug"].common(p["neck_outer"]).Volume, 1e-5)
        # The internal floor is flat and horizontal so boxes stand upright.
        cavity_bottom = p["z_vb"] + p["VES_T"]
        bottom_faces = [f for f in p["ves_cavity"].Faces
                        if abs(f.BoundBox.ZMin - cavity_bottom) < 1e-6]
        self.assertTrue(bottom_faces, "no flat internal floor found")
        for f in bottom_faces:
            self.assertEqual(type(f.Surface).__name__, "Plane")
            self.assertAlmostEqual(f.BoundBox.ZMin, cavity_bottom, places=5)
            self.assertAlmostEqual(f.BoundBox.ZMax, cavity_bottom, places=5)
        # The raised flat-bottomed vessel must clear the curved jacket cavity.
        self.assertLess(p["ves_outer"].common(p["jac_cavity"]).Volume, 1e-5)
        for first, second in (("ves_shell", "neck_corrug"),
                              ("neck_corrug", "neck_outer"),
                              ("jac_shell", "neck_outer"),
                              ("skirt", "jac_shell"),
                              ("stud", "jac_shell"), ("stud", "ves_shell")):
            joined = p[first].fuse(p[second]).removeSplitter()
            self.assertTrue(joined.isValid(), (first, second))
            self.assertEqual(len(joined.Solids), 1, (first, second))

    def test_valid_parameter_combinations(self):
        scenarios = [
            {},
            {"VES_R_IN": 320.0},
            {"VES_R_IN": 260.0},
            {"NECK_BORE_R": 80.0},
            {"NECK_BORE_R": 200.0},
            {"NECK_BORE_R": 250.0},
            {"NECK_LENGTH": 120.0},
            {"NECK_LENGTH": 250.0},
            {"NECK_LENGTH": 800.0},
            {"RIB_AMPL": 10.0, "RIB_ANGLE": 60.0},
            {"RIB_AMPL": 2.0, "RIB_ANGLE": 15.0},
            {"RIB_ANGLE": 70.0},
            {"RIB_AMPL": 12.0},
            {"RIB_WALL": 3.0},
            {"RIB_WALL": 0.75},
            {"VES_T": 8.0, "JAC_T": 10.0},
            {"VES_T": 0.5, "JAC_T": 0.5},
            {"NECK_GAP": 0.5},
            {"FLANGE_T": 12.0},
            {"FLANGE_T": 1.0},
            {"NECK_BORE_R": 80.0, "NECK_LENGTH": 120.0, "RIB_AMPL": 8.0},
            {"NECK_BORE_R": 250.0, "NECK_LENGTH": 200.0, "RIB_AMPL": 10.0},
            {"CORK_LEN": 1000.0},
            {"CORK_LIFT": 400.0},
        ]
        for changes in scenarios:
            with self.subTest(parameters=changes):
                print("Testing %s" % (changes or "defaults"), flush=True)
                p = build_geometry(changes)
                self.check_geometry(p)
                if "RIB_WALL" not in changes:
                    self.assertEqual(p["RIB_WALL"], p["VES_T"])

    def test_incompatible_inputs_are_rejected(self):
        scenarios = [
            {"NECK_BORE_R": 300.0},
            {"NECK_BORE_R": 4.0},
            {"NECK_LENGTH": 20.0},
            {"NECK_LENGTH": float("nan")},
            {"NECK_GAP": 0.0},
            {"RIB_ANGLE": 0.0},
            {"RIB_ANGLE": 90.0},
            {"RIB_WALL": 0.0},
            {"FLANGE_T": 1000.0},
            {"TARGET_VOLUME_L": 1.0},
            {"VES_HEAD_D": 300.0},
            {"CORK_CLEARANCE": -0.5},
            {"CORK_KNOB_R": 3.0},
            {"CORK_LIFT": -1.0},
            {"CORK_TIP_CLEARANCE": 1000.0},
            {"RADIAL_GAP": 0.0},
            {"SKIRT_INSET": 0.0},
        ]
        for changes in scenarios:
            with self.subTest(parameters=changes):
                with self.assertRaises(ValueError):
                    build_geometry(changes)

    def test_section_tracks_a_very_long_neck(self):
        p = build_geometry({"NECK_LENGTH": 6500.0, "RIB_ANGLE": 5.0}, section=True)
        self.check_geometry(p)
        for name, shape, color in p["parts"]:
            self.assertLessEqual(shape.BoundBox.YMax, 1e-6, name)


if __name__ == "__main__":
    unittest.main(verbosity=2)

# -*- coding: utf-8 -*-
"""Diagnostic: build the macro geometry, then measure how much of each wire
pokes outside the jacket outer envelope near its top end."""
import math
import traceback

import Part

try:
    path = r"C:\prj\cryonics\dewars\Dewar_Karnauhov\dewar_xb200_long_neck.py"
    src = open(path).read()
    src = src.split("#                              DOCUMENT")[0]
    g = {"__name__": "__diag__"}
    exec(compile(src, "dewar_macro", "exec"), g)

    jac_outer = g["jac_outer"]
    jac_r_in = g["jac_r_in"]
    wires = g["wires"]
    z_v0 = g["z_v0"]
    JAC_R_OUT = g["JAC_R_OUT"]

    inside = Part.makeCylinder(JAC_R_OUT, 3000.0, g["VEC"](0, 0, z_v0 - 500))
    core = Part.makeCylinder(jac_r_in, 3000.0, g["VEC"](0, 0, z_v0 - 500))
    skin_band = inside.cut(core)          # wall band jac_r_in..JAC_R_OUT
    outside = Part.makeCylinder(JAC_R_OUT + 100.0, 3000.0,
                                g["VEC"](0, 0, z_v0 - 500)).cut(inside)
    for i, w in enumerate(wires):
        print("Wire%d valid=%s solids=%d" % (i + 1, w.isValid(), len(w.Solids)))
        print("   pokes OUTSIDE jacket envelope vol = %.4f mm3"
              % w.cut(inside).Volume)
        print("   inside skin band vol = %.1f mm3" % w.common(skin_band).Volume)
        bb = w.BoundBox
        rmax = 0.0
        for v in w.Vertexes:
            rmax = max(rmax, math.hypot(v.X, v.Y))
        print("   zmax=%.1f (z_j1=%.1f)  rmax=%.2f (jac_out=%.2f)"
              % (bb.ZMax, g["z_j1"], rmax, JAC_R_OUT))
except Exception:
    print(traceback.format_exc())

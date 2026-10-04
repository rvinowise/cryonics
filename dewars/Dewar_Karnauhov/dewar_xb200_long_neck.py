# -*- coding: utf-8 -*-
"""
FreeCAD macro: 240 L LN2 storage dewar, similar to the Soviet ХБ-200 class
vessels, but with

  * a much LONGER NECK (less heat leak -> lower LN2 boil-off),
  * a CORRUGATED ("accordion") INNER NECK TUBE made only of alternating
    conical rings (parametrised cone angle and protrusion), giving the
    metal wall a longer conduction path,
  * a LONG BOTTLE-CORK-LIKE STOPPER (tapered plug + head + knob),
  * a DISHED (rounded) inner-vessel BOTTOM head like the other heads, so
    the bottom is not overloaded by a flat plate under LN2 pressure,
  * a separate FLAT FLOOR sheet resting on the dished bottom (on a small
    central support pad and at its welded rim) so boxes stand upright,
  * 8 thin SUPPORT WIRES inside the vacuum instead of a solid support
    column: 4 from the jacket roof (around the neck hole) down to the
    vessel, 4 from the jacket bottom up to the vessel bottom, evenly
    spread every 90 degrees.

Usage
-----
  FreeCAD GUI : Macro -> Macros... -> select this file -> Execute
                (or open it in the FreeCAD editor and press "Execute macro")
  Console     : exec(open(r"path/to/dewar_xb200_long_neck.py").read())
  Headless    : FreeCADCmd dewar_xb200_long_neck.py

The Z axis is the vertical axis of the dewar, Z = 0 is the floor.
All dimensions are in millimetres.

Change the input parameters below, not the derived radii or joint heights.
VES_R_IN drives the overall width: the jacket and skirt follow it, and a
wider vessel is automatically shorter because the volume is fixed. The
shell openings, profile-matched joints, flange and cork follow the neck
bore and length automatically. RIB_ANGLE and RIB_AMPL set the corrugation's
cone angle and radial protrusion (both lengthen the heat path). CORK_LEN is
the requested maximum; the plug is shortened when necessary to keep its tip
clear of the vessel. Impossible parameter combinations raise ValueError
before document updates.

RIB_WALL is the true thickness perpendicular to each conical face, not a
radial offset. Its default follows VES_T; this is NOT a structural rating.
Sharp folds are a CAD idealization: a manufactured bellows needs bend radii,
material / weld specifications and load, pressure, buckling and fatigue checks.
Increasing wall thickness increases conduction; extra metal volume alone
does not reduce the steady-state heat leak. The stopper must remain vented.

Structure (bodies of revolution about Z, except the support wires)
-------------------------------------------------------------------
  Skirt        - support ring under the outer jacket
  Jacket       - outer shell (vacuum jacket) with dished heads
  InnerVessel  - inner LN2 vessel with dished heads on BOTH ends; the
                 cavity volume above the floor hits TARGET_VOLUME_L
  Floor        - flat internal floor sheet (with a central support pad)
                 standing on the dished bottom so boxes stand still
  SupportWires - 8 thin rods in the vacuum: WireTop1..4 hang from the
                 jacket roof around the neck hole down to the vessel's
                 upper head, WireBot1..4 rise from the jacket bottom
                 head up to the vessel's bottom head
  NeckOuter    - outer neck tube + top flange with a profile-matched seat
  NeckCorrug   - corrugated (accordion) inner neck tube
  Cork         - long tapered stopper

The space between the jacket and the inner vessel / between the two neck
tubes is the vacuum (+ insulation) space.

Set SECTION_VIEW = True to cut away half of the model and look inside.
"""

import math

import FreeCAD as App
import Part

# ============================================================================
#                              PARAMETERS (mm)
# ============================================================================
TARGET_VOLUME_L = 240.0      # nominal LN2 capacity of the inner vessel

# ---- inner vessel (the WIDTH driver) ---------------------------------------
# VES_R_IN sets the overall width: the jacket and skirt follow it. A wider
# vessel is automatically shorter because the volume is fixed.
VES_R_IN = 360.0             # inner radius of the LN2 vessel  (D = 600)
VES_T = 2.0                  # wall thickness of the inner vessel
VES_HEAD_D = 100.0           # depth of the dished heads (inner side)

# ---- internal floor (flat sheet standing on the dished vessel bottom) -------
FLOOR_T = 3.0                # thickness of the flat internal floor sheet
FLOOR_PAD_R = 40.0           # radius of the central pad that carries the
                             # floor on the dished bottom head

# ---- outer jacket ----------------------------------------------------------
JAC_T = 2.5                  # jacket wall thickness
JAC_HEAD_D = 110.0           # depth of the dished heads (inner side)
RADIAL_GAP = 65.5            # vacuum gap, jacket cavity <-> vessel (side)
GAP_BOTTOM = 45.0            # vacuum gap between the BOTTOM HEAD APEXES
                             # of the jacket cavity and the vessel
GAP_TOP = 60.0               # vacuum gap, jacket cavity <-> vessel (top)

# ---- skirt / stand ---------------------------------------------------------
SKIRT_H = 45.0               # height of the jacket apex above the floor
SKIRT_INSET = 100.0          # skirt outer radius inset from the jacket radius
SKIRT_T = 6.0                # wall thickness of the skirt ring

# ---- support wires ----------------------------------------------------------
WIRE_R = 4.0                 # radius of the thin vessel support wires

# ---- neck ------------------------------------------------------------------
NECK_LENGTH = 520.0          # from the top of the inner vessel to the flange
                             # (a real ХБ-200 has ~ 250-300 -> "longer neck")
NECK_BORE_R = 150.0          # smallest radius of the bore (D = 300)
NECK_GAP = 40.0              # vacuum gap between the corrugated tube and the
                             # outer neck tube (keeps the two neck walls apart)
NECK_OUT_T = 2.0             # wall of the outer neck tube
FLANGE_OVERHANG = 13.0       # flange overhang beyond the outer tube wall
FLANGE_T = 8.0               # thickness of the top flange
NECK_JOINT_MARGIN = 2.0      # clearance above heads / construction-cut margin

# ---- corrugated (accordion) inner neck tube --------------------------------
RIB_AMPL = 35.0               # radial protrusion of the rings (longer heat path)
RIB_ANGLE = 55.0             # cone wall angle from horizontal, degrees
                             # (steeper = longer heat path per ring)
RIB_WALL = VES_T             # NORMAL thickness; draft default follows vessel
                             # set explicitly to override, after stress analysis

# ---- cork / stopper --------------------------------------------------------
CORK_LEN = 330.0             # maximum plug length; shortened for a short neck
CORK_CLEARANCE = 0.5         # radial clearance to the narrowest neck bore
CORK_TAPER = 2.0             # radial reduction from the plug top to its tip
CORK_TIP_CLEARANCE = 5.0     # axial clearance above the vessel head
CORK_HEAD_H = 24.0           # height of the head
CORK_KNOB_R = 20.0           # radius of the grip knob
CORK_KNOB_H = 22.0           # height of the knob
CORK_LIFT = 0.0              # lift the cork out of the neck (0 = inserted)

# ---- misc ------------------------------------------------------------------
SECTION_VIEW = True          # cut away the y>0 half to see the inside
EXPORT_STEP = ""             # e.g. r"C:\temp\dewar.step" ; "" = do not export

# ============================================================================
#                              HELPERS
# ============================================================================
VEC = App.Vector


def V(x, z):
    """Point in the XZ plane (the revolve profile plane)."""
    return VEC(x, 0.0, z)


def revolve_profile(wire):
    """Revolve a closed wire lying in the XZ plane around the Z axis."""
    face = Part.Face(wire)
    return face.revolve(VEC(0, 0, 0), VEC(0, 0, 1), 360)


def polygon_solid(pts):
    """Solid of revolution from a list of (r, z) points (closed polygon)."""
    pl = [V(r, z) for r, z in pts]
    pl.append(pl[0])
    return revolve_profile(Part.makePolygon(pl))


def cap_arc(r, z0, d, up):
    """Spherical dished head: arc from (r, z0) to the axis apex."""
    s = 1.0 if up else -1.0
    big_r = (r * r + d * d) / (2.0 * d)
    cz = z0 + s * (d - big_r)
    phi = math.asin(r / big_r)
    mid = V(big_r * math.sin(phi / 2.0), cz + s * big_r * math.cos(phi / 2.0))
    return Part.Arc(V(r, z0), mid, V(0.0, z0 + s * d)).toShape()


def capsule(r, z0, z1, d0, d1):
    """Cylinder (r) between junction heights z0..z1 with dished heads
    of depth d0 (bottom) and d1 (top)."""
    e_bot = cap_arc(r, z0, d0, up=False)
    e_cyl = Part.makeLine(V(r, z0), V(r, z1))
    e_top = cap_arc(r, z1, d1, up=True)
    e_axis = Part.makeLine(V(0.0, z1 + d1), V(0.0, z0 - d0))
    wire = Part.Wire([e_bot, e_cyl, e_top, e_axis])
    return revolve_profile(wire)


def cap_height(r, d, rr):
    """Height of a dished head surface above its apex at radius rr
    (head defined by base radius r and depth d)."""
    big_r = (r * r + d * d) / (2.0 * d)
    return big_r - math.sqrt(big_r * big_r - rr * rr)


# Tiny axial hole radius. Revolving a profile that touches the Z axis
# creates degenerate apex faces, and some OCC versions then silently miss
# the intersection in booleans with such a tool. Trimming tools below are
# therefore revolved with a 0.001 mm axial hole instead (far below any
# manufacturing tolerance and invisible in the model).
EPS_R = 1.0e-3


def dome_region(r, z0, d, skirt=50.0):
    """Region UNDER the top dished head surface (exact sphere) above
    z0 - skirt, revolved with a tiny EPS_R axial hole (see EPS_R)."""
    big_r = (r * r + d * d) / (2.0 * d)
    cz = z0 + d - big_r                       # sphere centre (below dome)
    t0 = math.asin(EPS_R / big_r)
    t1 = math.asin(r / big_r)
    tm = 0.5 * (t0 + t1)
    arc = Part.Arc(
        V(r, z0),
        V(big_r * math.sin(tm), cz + big_r * math.cos(tm)),
        V(EPS_R, cz + math.sqrt(big_r * big_r - EPS_R * EPS_R))).toShape()
    wire = Part.Wire([
        Part.makeLine(V(EPS_R, z0 - skirt),
                      V(EPS_R, cz + math.sqrt(big_r * big_r - EPS_R * EPS_R))),
        arc,
        Part.makeLine(V(r, z0), V(r, z0 - skirt)),
        Part.makeLine(V(r, z0 - skirt), V(EPS_R, z0 - skirt)),
    ])
    return revolve_profile(wire)


def capsule_surface_hit(pr, pz, ur, uz, r_cyl, z0, z1, d):
    """First hit parameter t > 0 of the 2D ray (pr, pz) + t*(ur, uz) on the
    OUTER surface of a capsule (cylinder radius r_cyl between z0..z1 with
    dished heads of depth d), or None. Used to anchor the support wires
    exactly on the vessel surface without piercing the convex vessel."""
    hits = []
    # cylindrical wall
    if abs(ur) > 1.0e-12:
        t = (r_cyl - pr) / ur
        if t > 0 and z0 <= pz + t * uz <= z1:
            hits.append(t)
    # top and bottom head spheres
    big_r = (r_cyl * r_cyl + d * d) / (2.0 * d)
    for cz, z_lo, z_hi in ((z1 + d - big_r, z1, z1 + d),
                           (z0 - d + big_r, z0 - d, z0)):
        b = 2.0 * (pr * ur + (pz - cz) * uz)
        c = pr * pr + (pz - cz) ** 2 - big_r * big_r
        disc = b * b - 4.0 * c
        if disc >= 0.0:
            root = math.sqrt(disc)
            for t in ((-b - root) / 2.0, (-b + root) / 2.0):
                if t > 0 and z_lo <= pz + t * uz <= z_hi:
                    hits.append(t)
    return min(hits) if hits else None


def cylinder(r, z0, z1):
    return Part.makeCylinder(r, z1 - z0, VEC(0, 0, z0), VEC(0, 0, 1))


def cap_volume(r, d):
    return math.pi * d * (3.0 * r * r + d * d) / 6.0


def require(condition, message):
    """Reject incompatible dimensions before creating document objects."""
    if not condition:
        raise ValueError(message)


# Basic input checks also protect the spherical-cap formulae from invalid
# square roots and the revolve profiles from zero / negative dimensions.
for parameter in (
        "TARGET_VOLUME_L", "VES_R_IN", "VES_T", "VES_HEAD_D",
        "FLOOR_T", "FLOOR_PAD_R",
        "JAC_T", "JAC_HEAD_D", "RADIAL_GAP", "GAP_BOTTOM", "GAP_TOP",
        "SKIRT_H", "SKIRT_INSET", "SKIRT_T", "NECK_LENGTH", "NECK_BORE_R",
        "NECK_GAP", "NECK_OUT_T", "FLANGE_OVERHANG", "FLANGE_T",
        "NECK_JOINT_MARGIN", "RIB_AMPL", "RIB_ANGLE", "RIB_WALL", "CORK_LEN",
        "CORK_CLEARANCE", "CORK_TAPER", "CORK_TIP_CLEARANCE", "CORK_HEAD_H",
        "CORK_KNOB_R", "CORK_KNOB_H", "WIRE_R"):
    require(math.isfinite(globals()[parameter]) and globals()[parameter] > 0.0,
            "%s must be finite and greater than zero" % parameter)
require(math.isfinite(CORK_LIFT) and CORK_LIFT >= 0.0,
        "CORK_LIFT must be finite and non-negative")
require(0.0 < RIB_ANGLE < 90.0,
        "RIB_ANGLE must be between 0 and 90 degrees")
require(VES_HEAD_D <= VES_R_IN,
        "VES_HEAD_D must not exceed VES_R_IN")
require(FLOOR_PAD_R < VES_R_IN,
        "FLOOR_PAD_R must be smaller than VES_R_IN")
require(2.0 * WIRE_R < min(GAP_TOP, GAP_BOTTOM),
        "The support wires must be thinner than the head gaps")
require(CORK_HEAD_H > 5.0 and CORK_KNOB_H > 10.0,
        "The cork head / knob heights must allow their chamfers")
require(CORK_KNOB_R > 4.0,
        "CORK_KNOB_R must exceed the knob's 4 mm top chamfer")


# ============================================================================
#                              GEOMETRY
# ============================================================================
# ---- inner vessel dimensions: cylinder length for the required volume -----
# The usable volume is the cavity ABOVE the flat floor sheet: cylinder +
# top head + the part of the dished bottom head not filled by the floor
# support pad. The floor sheet itself and the pad are subtracted so that
# TARGET_VOLUME_L is the volume available for LN2 and boxes.
v_target = TARGET_VOLUME_L * 1.0e6                                # mm^3
v_heads = 2.0 * cap_volume(VES_R_IN, VES_HEAD_D)              # both heads
floor_disk_vol = math.pi * VES_R_IN ** 2 * FLOOR_T             # floor sheet
pad_h = cap_height(VES_R_IN, VES_HEAD_D, FLOOR_PAD_R)
floor_pad_vol = (math.pi * FLOOR_PAD_R ** 2 * VES_HEAD_D
                 - cap_volume(FLOOR_PAD_R, pad_h))
ves_cyl_h = ((v_target - v_heads - floor_disk_vol - floor_pad_vol)
             / (math.pi * VES_R_IN ** 2))
require(ves_cyl_h > 0.0,
        "TARGET_VOLUME_L must exceed the volume of the heads, the floor "
        "sheet and the floor support pad")

# ---- derived widths: jacket and skirt follow the vessel radius -------------
JAC_R_OUT = VES_R_IN + VES_T + RADIAL_GAP + JAC_T
SKIRT_R = JAC_R_OUT - SKIRT_INSET
require(JAC_HEAD_D <= JAC_R_OUT - JAC_T,
        "JAC_HEAD_D must not exceed the jacket cavity radius")
require(0.0 < SKIRT_T < SKIRT_R < JAC_R_OUT,
        "The skirt requires SKIRT_T < SKIRT_R < JAC_R_OUT")

# ---- vertical layout (Z) ---------------------------------------------------
z_jb = SKIRT_H                                  # jacket outer bottom apex
jac_d_out = JAC_HEAD_D + JAC_T                  # outer head depth
z_jac_cav_bot = z_jb + JAC_T                    # jacket cavity bottom apex

jac_r_in = JAC_R_OUT - JAC_T
ves_r_out = VES_R_IN + VES_T
ves_d_out = VES_HEAD_D + VES_T
# Dished vessel bottom: GAP_BOTTOM is the apex-to-apex clearance between
# the jacket cavity bottom head and the vessel outer bottom head. At the
# vessel's outer radius the (much shallower) jacket head leaves a larger
# clearance automatically.
z_vb = z_jac_cav_bot + GAP_BOTTOM               # vessel outer bottom apex
z_v0 = z_vb + ves_d_out                 # vessel cylinder bottom junction
z_v1 = z_v0 + ves_cyl_h                 # vessel cylinder top junction
z_va = z_v1 + ves_d_out                         # vessel outer top apex

z_ja = z_va + GAP_TOP                           # jacket cavity top apex
z_j0 = z_jb + jac_d_out                         # jacket cylinder bottom junction
z_j1 = z_ja - JAC_HEAD_D                        # jacket cylinder top junction
z_jat = z_ja + JAC_T                            # jacket outer top apex

z_nt = z_va + NECK_LENGTH                       # top of neck flange

# ---- continuous conical neck: fitted pitch and true sheet thickness --------
# Start the construction profile at the head's cylinder junction, safely
# inside the vessel cavity. The curved cavity trims away all hidden rings;
# the finished bellows has only conical faces all the way to the mouth.
z_c0 = z_v1
z_c1 = z_nt
c_len = z_c1 - z_c0
# Nominal pitch follows the requested cone angle and ring protrusion; the
# actual pitch is then fitted to an integer number of rings.
rib_pitch_nominal = 2.0 * RIB_AMPL / math.tan(math.radians(RIB_ANGLE))
n_rib = max(1, int(round(c_len / rib_pitch_nominal)))
pitch = c_len / n_rib
# A constant radial offset of t * sqrt(1 + slope^2) gives normal thickness t
# on BOTH alternating cone slopes. Symmetric sharp folds use mitered corners.
rib_slope = 2.0 * RIB_AMPL / pitch
rib_radial_wall = RIB_WALL * math.hypot(1.0, rib_slope)
NECK_CORRUG_OUT_R = NECK_BORE_R + RIB_AMPL + rib_radial_wall
NECK_OUT_R_IN = NECK_CORRUG_OUT_R + NECK_GAP
NECK_OUT_R_OUT = NECK_OUT_R_IN + NECK_OUT_T
FLANGE_R = NECK_OUT_R_OUT + FLANGE_OVERHANG
CORK_R_TOP = NECK_BORE_R - CORK_CLEARANCE
CORK_R_BOT = CORK_R_TOP - CORK_TAPER
CORK_HEAD_R = FLANGE_R + 2.0
require(NECK_CORRUG_OUT_R < VES_R_IN,
        "The corrugated neck opening must be smaller than VES_R_IN")
require(NECK_OUT_R_OUT < jac_r_in,
        "The outer neck opening must be smaller than the jacket cavity radius")
require(CORK_R_BOT > 2.0,
        "The neck bore is too small for the cork clearance, taper and tip")
require(CORK_HEAD_R - 5.0 > CORK_KNOB_R + 6.0,
        "The cork knob and its chamfer must fit on the cork head")

# ---- derived outer tube / flange heights and stopper fit ------------------
z_start = (z_ja - cap_height(jac_r_in, JAC_HEAD_D, NECK_OUT_R_OUT)
           - NECK_JOINT_MARGIN)
z_fl = z_nt - FLANGE_T
require(z_fl > z_jat - cap_height(JAC_R_OUT, jac_d_out, NECK_CORRUG_OUT_R)
        + NECK_JOINT_MARGIN,
        "NECK_LENGTH is too short to keep the flange above the jacket head")
require(z_fl > z_start,
        "NECK_LENGTH is too short for the outer tube and flange")
z_cork_limit = (z_va - cap_height(ves_r_out, ves_d_out, NECK_BORE_R)
                + NECK_JOINT_MARGIN + CORK_TIP_CLEARANCE)
cork_len = min(CORK_LEN, z_nt - z_cork_limit)
require(cork_len > 0.0,
        "CORK_TIP_CLEARANCE leaves no room for the cork in this neck")
cork_tip_h = min(6.0, cork_len / 4.0)

# ---- inner vessel (shell) --------------------------------------------------
ves_outer = capsule(ves_r_out, z_v0, z_v1, ves_d_out, ves_d_out)
ves_cavity = capsule(VES_R_IN, z_v0, z_v1, VES_HEAD_D, VES_HEAD_D)
ves_shell = ves_outer.cut(ves_cavity)
# The opening is cut below using the ACTUAL corrugated envelope, not a
# constant-radius cylinder that would leave gaps beside the sloping rings.

# ---- outer jacket (shell) --------------------------------------------------
jac_outer = capsule(JAC_R_OUT, z_j0, z_j1, jac_d_out, jac_d_out)
jac_cavity = capsule(jac_r_in, z_j0, z_j1, JAC_HEAD_D, JAC_HEAD_D)
jac_shell = jac_outer.cut(jac_cavity)
# opening for the outer neck tube in the top head: hole at the tube OUTER
# radius, deep enough to fully open the curved head
jac_hole_bot = z_start
jac_shell = jac_shell.cut(cylinder(NECK_OUT_R_OUT, jac_hole_bot,
                                   z_jat + NECK_JOINT_MARGIN))

# ---- skirt -----------------------------------------------------------------
sk_ro = SKIRT_R
sk_ri = SKIRT_R - SKIRT_T
sk_top = z_jb + cap_height(JAC_R_OUT, jac_d_out, sk_ri) + 1.5
skirt = polygon_solid([(sk_ri, 0.0), (sk_ro, 0.0), (sk_ro, sk_top), (sk_ri, sk_top)])

# ---- support wires (vessel <-> jacket, inside the vacuum) -------------------
# 8 thin rods replace the old solid support column: 4 hang from the jacket
# roof around the neck hole down to the vessel's upper head, 4 rise from
# the jacket bottom head up to the vessel's bottom head, spread every
# 90 degrees. Each rod lies in a plane through the axis, starts exactly
# ON the jacket's inner head surface and ends at the FIRST hit on the
# vessel's convex outer surface, so it can never pierce the vessel. Both
# ends dip a fraction of the wall thickness into the metal to guarantee
# welded contact for any wall thickness. The final wire is the portion
# lying in the vacuum (cut by both shells) so the ends exactly match the
# curved shell surfaces.
WIRE_COUNT = 4
wire_anchors = [
    # (anchor radius, anchor z on the jacket head, aim target z, is_top)
    (0.5 * (NECK_OUT_R_OUT + jac_r_in),
     z_ja - cap_height(jac_r_in, JAC_HEAD_D, 0.5 * (NECK_OUT_R_OUT + jac_r_in)),
     z_v0 + 0.5 * ves_cyl_h, True),          # roof, around the neck hole
    (30.0,                                      # small radius for vertical bottom wires
     z_jac_cav_bot + cap_height(jac_r_in, JAC_HEAD_D, 30.0),
     z_vb, False),                           # bottom apex area
]
pen_jac = min(0.5 * JAC_T, 0.5)              # anchor depth into the jacket
pen_ves = min(0.5 * VES_T, 0.5)             # anchor depth into the vessel
wires = []
for a_r, a_z, t_z, is_top in wire_anchors:
    dr, dz = -a_r, t_z - a_z                 # aim at the axis at height t_z
    length_2d = math.hypot(dr, dz)
    ur, uz = dr / length_2d, dz / length_2d
    t_hit = capsule_surface_hit(a_r, a_z, ur, uz,
                                ves_r_out, z_v0, z_v1, ves_d_out)
    require(t_hit is not None and t_hit > 2.0 * WIRE_R,
            "A support wire cannot reach the vessel; check the gaps")
    if is_top:
        # the wire must pass clearly BELOW the outer neck tube where their
        # radius bands overlap (the tube starts at z_start)
        t_tube = (NECK_OUT_R_OUT - a_r) / ur
        require(a_z + t_tube * uz < z_start - WIRE_R,
                "The upper support wires would hit the outer neck tube; "
                "check the neck and jacket head dimensions")
    for k in range(WIRE_COUNT):
        phi = math.radians(45.0 + 90.0 * k)
        c, s = math.cos(phi), math.sin(phi)
        r0e = a_r - ur * pen_jac
        p0 = VEC(r0e * c, r0e * s, a_z - uz * pen_jac)
        full_wire = Part.makeCylinder(
            WIRE_R, t_hit + pen_jac + pen_ves, p0, VEC(ur * c, ur * s, uz))
        # Keep only the portion lying in the vacuum (ends cut by the shell
        # inner surfaces).
        vac_wire = full_wire.cut(jac_shell).cut(ves_shell).removeSplitter()
        wires.append(vac_wire)

# ---- internal floor (flat sheet standing on the dished bottom) --------------
# A flat disk the full cavity radius, welded to the vessel wall at the
# bottom head / cylinder junction, plus a central support pad following
# the exact spherical bottom head (analytic revolve, no booleans): together
# they carry the floor on the dished bottom so boxes stand still.
z_floor_bot = z_v0                              # head / cylinder junction
z_floor_top = z_floor_bot + FLOOR_T
floor_disk = cylinder(VES_R_IN, z_floor_bot, z_floor_top)
big_b = (VES_R_IN ** 2 + VES_HEAD_D ** 2) / (2.0 * VES_HEAD_D)
cz_b = z_v0 - VES_HEAD_D + big_b                # bottom head sphere centre
t0 = math.asin(EPS_R / big_b)
t1 = math.asin(FLOOR_PAD_R / big_b)
tm = 0.5 * (t0 + t1)
pad_arc = Part.Arc(
    V(EPS_R, cz_b - math.sqrt(big_b * big_b - EPS_R * EPS_R)),
    V(big_b * math.sin(tm), cz_b - big_b * math.cos(tm)),
    V(FLOOR_PAD_R, cz_b - math.sqrt(big_b * big_b - FLOOR_PAD_R ** 2))
    ).toShape()
floor_pad = revolve_profile(Part.Wire([
    Part.makeLine(V(EPS_R, z_floor_bot),
                  V(EPS_R, cz_b - math.sqrt(big_b * big_b - EPS_R * EPS_R))),
    pad_arc,
    Part.makeLine(V(FLOOR_PAD_R, cz_b - math.sqrt(big_b * big_b
                                                  - FLOOR_PAD_R ** 2)),
                  V(FLOOR_PAD_R, z_floor_bot)),
    Part.makeLine(V(FLOOR_PAD_R, z_floor_bot), V(EPS_R, z_floor_bot)),
]))
floor_part = floor_disk.fuse(floor_pad).removeSplitter()

# ---- corrugated ("accordion") inner neck tube ------------------------------
r0 = NECK_BORE_R
inner_pts = [(r0 + RIB_AMPL, z_c0)]
for i in range(n_rib):
    zb = z_c0 + i * pitch
    inner_pts += [
        (r0, zb + 0.50 * pitch),              # conical flank to valley
        (r0 + RIB_AMPL, z_c1 if i == n_rib - 1
         else z_c0 + (i + 1) * pitch),        # directly back to crest
    ]
outer_profile = [(r + rib_radial_wall, z) for r, z in inner_pts]
outer_pts = list(reversed(outer_profile))
neck_corrug = polygon_solid(inner_pts + outer_pts)
# No flat lower cuff: trim the conical wall flush to the curved inner head.
# The trim tool is the exact spherical dome region (dome_region), whose
# tiny axial hole avoids the degenerate apex faces that make some OCC
# versions silently skip this cut.
neck_corrug = neck_corrug.cut(
    dome_region(VES_R_IN, z_v1, VES_HEAD_D)).removeSplitter()
# This axis-filled envelope supplies exactly matching joint surfaces for
# both the vessel opening and the flange seat, at any phase of a rib.
neck_envelope = polygon_solid([(0.0, z_c0)] + outer_profile + [(0.0, z_c1)])
ves_shell = ves_shell.cut(neck_envelope).removeSplitter()
n_rib_visible = sum(1 for i in range(n_rib)
                    if z_c0 + (i + 1) * pitch > neck_corrug.BoundBox.ZMin)

# ---- outer neck tube + flange (NO straight inner mouth sleeve) -------------
r_o_in = NECK_OUT_R_IN
r_o_out = NECK_OUT_R_OUT
# Start with a full flange disk; the shared envelope cuts its bore to match
# the angled bellows all the way through the flange thickness to the mouth.
neck_outer = polygon_solid([
    (r_o_in, z_start),
    (r_o_out, z_start),
    (r_o_out, z_fl),
    (FLANGE_R, z_fl),
    (FLANGE_R, z_nt),
    (0.0, z_nt),
    (0.0, z_fl),
    (r_o_in, z_fl),
])
neck_outer = neck_outer.cut(neck_envelope).cut(jac_cavity).removeSplitter()

# ---- cork (long tapered stopper like a bottle cork) ------------------------
zc = z_nt + CORK_LIFT
cork = polygon_solid([
    (0.0, zc - cork_len),
    (CORK_R_BOT - 2.0, zc - cork_len),                 # rounded-off tip
    (CORK_R_BOT, zc - cork_len + cork_tip_h),
    (CORK_R_TOP, zc),                                  # taper
    (CORK_HEAD_R, zc),                                 # head, flat underside
    (CORK_HEAD_R, zc + CORK_HEAD_H - 5.0),
    (CORK_HEAD_R - 5.0, zc + CORK_HEAD_H),
    (CORK_KNOB_R + 6.0, zc + CORK_HEAD_H),
    (CORK_KNOB_R, zc + CORK_HEAD_H + 6.0),             # knob
    (CORK_KNOB_R, zc + CORK_HEAD_H + CORK_KNOB_H - 4.0),
    (CORK_KNOB_R - 4.0, zc + CORK_HEAD_H + CORK_KNOB_H),
    (0.0, zc + CORK_HEAD_H + CORK_KNOB_H),
])

# ============================================================================
#                              DOCUMENT
# ============================================================================
parts = [
    ("Skirt", skirt, (0.30, 0.30, 0.32)),
    ("Jacket", jac_shell, (0.80, 0.82, 0.85)),
    ("InnerVessel", ves_shell, (0.55, 0.60, 0.70)),
    ("Floor", floor_part, (0.65, 0.45, 0.30)),
    ("NeckOuter", neck_outer, (0.80, 0.82, 0.85)),
    ("NeckCorrug", neck_corrug, (0.90, 0.60, 0.25)),
    ("Cork", cork, (0.78, 0.60, 0.38)),
]
parts += [("WireTop%d" % (i + 1), w, (0.45, 0.45, 0.48))
          for i, w in enumerate(wires[:WIRE_COUNT])]
parts += [("WireBot%d" % (i + 1), w, (0.45, 0.45, 0.48))
          for i, w in enumerate(wires[WIRE_COUNT:])]

# Fail instead of displaying disconnected or intersecting geometry for an
# incompatible input combination. Keep the displayed parts separate; these
# fusions only verify that each intended joint forms one connected solid.
for name, shape, color in parts:
    require(shape.isValid() and len(shape.Solids) == 1,
            "%s is not a valid single solid; check the input dimensions" % name)
for label, first, second in (
        ("vessel / conical neck", ves_shell, neck_corrug),
        ("conical neck / mouth flange", neck_corrug, neck_outer),
        ("jacket / outer neck", jac_shell, neck_outer),
        ("skirt / jacket", skirt, jac_shell)):
    joint = first.fuse(second).removeSplitter()
    require(joint.isValid() and len(joint.Solids) == 1,
            "Disconnected joint: %s; check the input dimensions" % label)
for i, wire in enumerate(wires):
    for other in (jac_shell, ves_shell):
        joint = wire.fuse(other).removeSplitter()
        require(joint.isValid() and len(joint.Solids) == 1,
                "Disconnected joint: support wire %d; check the gaps" % i)
require(ves_outer.cut(jac_cavity).Volume < 1.0e-5,
        "The inner vessel does not fit inside the jacket cavity; increase the gaps")
require(neck_corrug.common(jac_shell).Volume < 1.0e-5,
        "The corrugated neck intersects the jacket; check the neck and head dimensions")

if SECTION_VIEW:
    # Size the cut from the actual model, including arbitrarily long necks.
    x_min = min(s.BoundBox.XMin for n, s, c in parts) - 1.0
    x_max = max(s.BoundBox.XMax for n, s, c in parts) + 1.0
    y_max = max(s.BoundBox.YMax for n, s, c in parts) + 1.0
    z_min = min(s.BoundBox.ZMin for n, s, c in parts) - 1.0
    z_max = max(s.BoundBox.ZMax for n, s, c in parts) + 1.0
    cutter = Part.makeBox(x_max - x_min, y_max, z_max - z_min,
                          VEC(x_min, 0, z_min))
    parts = [(n, s.cut(cutter), c) for n, s, c in parts]
    # Support wires that lie entirely in the removed half vanish; drop the
    # empty shapes so only visible geometry is shown / exported.
    parts = [(n, s, c) for n, s, c in parts if s.Solids]

doc = App.listDocuments().get("Dewar") or App.newDocument("Dewar")
App.setActiveDocument(doc.Name)
# Remove objects from previous runs that are no longer part of the model
# (e.g. support wires dropped by the section cut).
for o in list(doc.Objects):
    if o.Name not in set(name for name, shape, color in parts):
        doc.removeObject(o.Name)
objs = []
for name, shape, color in parts:
    # Re-running after parameter edits updates the assembly rather than
    # leaving the previous geometry visible as a second set of parts.
    o = doc.getObject(name) or doc.addObject("Part::Feature", name)
    o.Shape = shape
    try:
        o.ViewObject.ShapeColor = color
    except Exception:
        pass            # headless mode - no view objects
    objs.append(o)
doc.recompute()

try:
    import FreeCADGui
    FreeCADGui.SendMsgToActiveView("ViewFit")
    FreeCADGui.activeDocument().activeView().viewIsometric()
except Exception:
    pass

if EXPORT_STEP:
    import Import
    Import.export(objs, EXPORT_STEP)

# ============================================================================
#                              REPORT
# ============================================================================
neck_bore_vol = math.pi * NECK_BORE_R ** 2 * (z_nt - (z_v1 + VES_HEAD_D)) / 1.0e6
App.Console.PrintMessage(
    "\n=== Dewar (ХБ-200 style, long neck, corrugated inner neck) ===\n"
    "Usable volume above floor : %.1f L (cavity %.1f L, + ~%.1f L in the neck)\n"
    "Vessel cylinder length    : %.0f mm\n"
    "Overall height (cork off) : %.0f mm\n"
    "Overall height with cork  : %.0f mm\n"
    "Jacket outer diameter     : %.0f mm\n"
    "Neck length (vessel->top) : %.0f mm\n"
    "Neck bore diameter        : %.0f mm (outer tube D = %.0f mm)\n"
    "Corrugated neck ribs      : %d visible (pitch %.1f mm, depth %.1f mm, angle %.1f deg)\n"
    "Bellows normal thickness  : %.2f mm (NOT structurally rated)\n"
    "Cork plug length          : %.1f mm (requested maximum %.1f mm)\n"
    % ((ves_cavity.Volume - floor_part.Volume) / 1.0e6,
       ves_cavity.Volume / 1.0e6, neck_bore_vol, ves_cyl_h, z_nt,
       zc + CORK_HEAD_H + CORK_KNOB_H, 2 * JAC_R_OUT, NECK_LENGTH,
       2 * NECK_BORE_R, 2 * NECK_OUT_R_IN,
       n_rib_visible, pitch, RIB_AMPL,
       math.degrees(math.atan(2.0 * RIB_AMPL / pitch)),
       RIB_WALL, cork_len, CORK_LEN)
)

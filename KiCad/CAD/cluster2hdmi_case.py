"""Cluster2HDMI case v6 (CadQuery). Change numbers in PARAMETERS and re-run.
Axes: X = left->right seen from the front, Y = front->back, Z = up.  Units: mm."""
import math, cadquery as cq

# ---------------- PARAMETERS ----------------
TILT      = 5.0    # screen leans back this many degrees from vertical
WALL      = 2.5    # wall thickness
PANEL_W   = 167.5  # LCD panel width (measured 167-168)
PANEL_H   = 100.0  # LCD panel height
PANEL_T   = 7.0    # LCD panel thickness (measured ~7)
CLR       = 0.5    # clearance around the panel
WIN_W     = 156.0  # screen window width = visible area width (measured)
WIN_H     = 156.0*480/800  # visible height worked out from 800x480 square pixels = 93.6  <-- check
STANDOFF  = 16.0   # board standoff length (Pico 13 mm + margin)
BOARD_GAP = 10.0   # gap between floor and board bottom edge (ribbon room)
BOARD_X_GAP = 12.0 # gap between left inner wall and board edge (room for the 10-pin ribbon into FPC1)
DC_HOLE_D = 12.0   # DC plug hole in the back cover (PJ-044A is a VERTICAL jack: plug goes in straight through the cover)
# Panel's top two screw holes (from your drawing): 22 mm in from each side edge, 123 mm apart
TAB_X      = (PANEL_W/2 - 61.5, PANEL_W/2 + 61.5)  # 123 mm apart, centred
TAB_FROM_TOP = 13.0         # mm down from the panel's top edge (measured)
TAB_SCREW  = 2.4            # clearance hole for M2 screws (panel holes are threaded M2, measured 2.2)
TAB_TUBE_D = 7.0            # outer diameter of the screw tubes
HDMI_HOLE = (24.0, 14.0)  # HDMI plug hole in top wall (X, Y)
M3_PILOT, M3_CLEAR = 2.5, 3.4
M2_PILOT = 1.8

# ---------------- derived ----------------
th = math.radians(TILT); c, s, t = math.cos(th), math.sin(th), math.tan(th)
W_IN = PANEL_W + 2*CLR; W = W_IN + 2*WALL
LP = PANEL_H + 2*CLR
H = WALL + PANEL_T*s + LP*c + CLR + WALL
Z_BOT = WALL + BOARD_GAP; Z_TOP = Z_BOT + 55.0
def panel_back_y(z): return z*t + (WALL + PANEL_T)/c
# board component face y (components point backwards, toward the cover)
y_cs_1 = panel_back_y(Z_TOP) + 1 + 3 + 1.6            # pin tails behind the panel
y_cs_2 = panel_back_y(H - WALL) + 1 + 6               # HDMI plug path clears the panel top
Y_CS = max(y_cs_1, y_cs_2)
D_BOT = Y_CS + STANDOFF
D_TOP = D_BOT - H*t
XC = WALL + BOARD_X_GAP + 64.0                       # board centre X (board mirrored: KiCad x178 at left)
def bx(kx): return XC - (kx - 114.0)
def bz(ky): return Z_TOP - (ky - 50.0)

# ---------------- case shell ----------------
outer = (cq.Workplane("YZ").polyline([(0,0),(D_BOT,0),(D_BOT,H),(D_BOT-D_TOP,H)]).close().extrude(W))
FILLET = 3.0       # rounded outer edges
try:
    outer = outer.edges("not(<Y or >Y)").fillet(FILLET)
except Exception as e:
    print("fillet skipped:", e)
cav = (cq.Workplane("YZ").workplane(offset=WALL)
       .polyline([(WALL*t + WALL/c, WALL), (D_BOT+1, WALL), (D_BOT+1, H-WALL), ((H-WALL)*t + WALL/c, H-WALL)])
       .close().extrude(W_IN))
case = outer.cut(cav)

# screen window through the sloped front wall
u = cq.Vector(0, s, c); n = cq.Vector(0, -c, s)
pb_z = WALL + PANEL_T*s; pb = cq.Vector(0, pb_z*t + WALL/c, pb_z)          # panel front-bottom corner
s0, s1 = CLR + (PANEL_H - WIN_H)/2, CLR + (PANEL_H + WIN_H)/2
win_c = pb + u*((s0+s1)/2) + cq.Vector(W/2, 0, 0)
win = (cq.Workplane(cq.Plane(origin=win_c, xDir=(1,0,0), normal=n))
       .rect(WIN_W, s1 - s0).extrude(10, both=True))
case = case.cut(win)

# HDMI plug hole in the top wall, DC plug hole in the left wall
hx, hy = bx(92.25), Y_CS + 3.0
case = case.cut(cq.Workplane("XY").box(HDMI_HOLE[0], HDMI_HOLE[1], WALL*4).translate((hx, hy, H - WALL/2)))
# (DC plug hole is in the back cover now)

# ---------------- back cover ----------------
cover = cq.Workplane("XY").box(W, WALL, H, centered=False).translate((0, D_BOT, 0))
try: cover = cover.edges("|Y").fillet(FILLET)
except Exception as e: print("cover fillet skipped:", e)
# locating lip: a 2 mm deep rim that slips just inside the shell's back opening (0.3 mm clearance)
LIP = 2.0
lip_outer = cq.Workplane("XZ", origin=(0, D_BOT, 0)).center(W/2, H/2).rect(W - 2*WALL - 0.6, H - 2*WALL - 0.6).extrude(LIP)
lip_inner = cq.Workplane("XZ", origin=(0, D_BOT, 0)).center(W/2, H/2).rect(W - 2*WALL - 0.6 - 2*1.6, H - 2*WALL - 0.6 - 2*1.6).extrude(LIP)
cover = cover.union(lip_outer.cut(lip_inner))
# 2 screw standoffs at board holes H1/H2 (the PCB screws onto these)
for (kx, ky) in ((113.5, 59.0), (113.5, 74.0)):
    st = (cq.Workplane("XZ", origin=(bx(kx), D_BOT, bz(ky))).circle(2.75).extrude(STANDOFF)
          .faces("<Y").workplane().hole(M2_PILOT, STANDOFF - 1))
    cover = cover.union(st)
# one clip next to the DC jack: pushing the DC plug in pushes that corner of the board toward the panel's metal back;
# this hook catches the board edge (front side) so the pin tails can't touch the panel
cx0 = bx(178.0)                                   # board edge nearest the DC jack (case left)
clip_z = bz(98.0)
post = cq.Workplane("XY").box(2.0, STANDOFF + 1.6 + 1.5, 6.0).translate((cx0 - 1.0 - 0.2, D_BOT - (STANDOFF + 1.6 + 1.5)/2, clip_z))
hook = cq.Workplane("XY").box(3.4, 1.5, 6.0).translate((cx0 + 0.5, D_BOT - STANDOFF - 1.6 - 0.75 - 0.1, clip_z))
cover = cover.union(post).union(hook)
# DC jack (vertical, centre at KiCad 167.25, 97.6 from the 3D model) -> plug hole straight through the cover
cover = cover.cut(cq.Workplane("XZ", origin=(bx(167.25), D_BOT + WALL + 1, bz(97.6))).circle(DC_HOLE_D/2).extrude(-(WALL + 2)))
# Panel hangs from the cover on its top two screws: a tube from the cover to each panel hole,
# screw goes in from outside the cover, through the tube, into the panel. Tube ends clamp the panel against the front lip.
s_hole = CLR + PANEL_H - TAB_FROM_TOP
for tx in TAB_X:
    pback = pb + u*s_hole - n*PANEL_T + cq.Vector(WALL + CLR + tx, 0, 0)
    L = (D_BOT + WALL - pback.y) / c
    pl = cq.Plane(origin=pback, xDir=(1,0,0), normal=(-n))
    cover = cover.union(cq.Workplane(pl).circle(TAB_TUBE_D/2).extrude((D_BOT - pback.y)/c))
    cover = cover.cut(cq.Workplane(pl).workplane(offset=-1).circle(TAB_SCREW/2).extrude(L + 3))
    print("panel screw: tube %.1f mm, screw length >= %.0f mm (+ thread into panel)" % ((D_BOT - pback.y)/c, L))

# ---------------- reference bodies (not printed) ----------------
panel = (cq.Workplane(cq.Plane(origin=pb + u*(CLR + PANEL_H/2) + cq.Vector(W/2,0,0) - n*(PANEL_T/2), xDir=(1,0,0), normal=n))
         .rect(PANEL_W, PANEL_H).extrude(PANEL_T/2, both=True))
board = cq.Workplane("XY").box(128, 1.6, 55, centered=False).translate((bx(178), Y_CS - 1.6, Z_BOT))

if __name__ == "__main__":
    print("case outer: W %.1f  H %.1f  depth bottom %.1f  top %.1f" % (W, H, D_BOT, D_TOP))
    cq.exporters.export(case, "case_shell.step"); cq.exporters.export(cover, "case_back_cover.step")
    cq.exporters.export(case, "case_shell.stl"); cq.exporters.export(cover, "case_back_cover.stl")
    asm = cq.Assembly().add(case, name="shell", color=cq.Color(0.85,0.85,0.88)).add(cover, name="cover", color=cq.Color(0.6,0.6,0.65)) \
        .add(panel, name="lcd_panel_ref", color=cq.Color(0.1,0.1,0.12)).add(board, name="pcb_ref", color=cq.Color(0.2,0.45,0.3))
    asm.save("case_assembly.step")
    for nm, o in (("panel", panel), ("board", board)): cq.exporters.export(o, f"ref_{nm}.stl")
    # interference checks
    print("panel vs shell overlap vol:", round(case.intersect(panel).val().Volume(),2))
    print("board vs shell overlap vol:", round(case.intersect(board).val().Volume(),2))
    print("board vs panel overlap vol:", round(panel.intersect(board).val().Volume(),2))
    print("valid:", case.val().isValid(), cover.val().isValid())

def board_from_kicad_step(path):
    """Place the real KiCad board STEP (exported with 'Board center origin') into the case."""
    from OCP.gp import gp_Trsf
    shp = cq.importers.importStep(path).val()
    tr = gp_Trsf()
    # case X = XC - x,  case Y = (Y_CS - 1.6) + z,  case Z = (Z_TOP - 27.5) + y
    tr.SetValues(-1, 0, 0, XC, 0, 0, 1, Y_CS - 1.6, 0, 1, 0, Z_TOP - 27.5)
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    return cq.Shape.cast(BRepBuilderAPI_Transform(shp.wrapped, tr, True).Shape())

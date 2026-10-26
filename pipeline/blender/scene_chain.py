"""Procedural Blender scene: the chain fountain (Mould effect).

Run headless:
  blender -b -noaudio -P pipeline/blender/scene_chain.py -- --shot A --start 0 --end 343 \
      --out videos/002-chain-fountain/build/frames/A [--res 576] [--samples 24] [--preview]

The chain is kinematic: a bead unit (sphere + link) is repeated with an Array
modifier and deformed along a poly-spline path by a Curve modifier. The path
(pile -> arch above the rim -> floor) is recomputed every (sub)frame from a few
smooth functions of time in a frame_change handler, so Cycles' motion blur sees
the real deformation. Flow = sliding the array along its own X by (v*t mod pitch).
Scene time runs at 1/SLOWMO of real time (slow-motion look, beads stay visible).

Shots (nominal durations in SHOT_DUR; paths clamp beyond):
  A  wide : chain released over the rim, slides, then the fountain rises and hovers
  C  hero : close orbit of the hovering loop at steady state
"""
import bpy, bmesh, math, sys, os, time
from mathutils import Vector
from mathutils import noise as mnoise

def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    a = {"shot": "A", "start": 0, "end": 1, "out": "/tmp/frames", "res": 576, "samples": 24, "preview": False, "fps": 24, "mblur": 1}
    i = 0
    while i < len(argv):
        k = argv[i].lstrip("-")
        if k == "preview": a["preview"] = True; i += 1; continue
        v = argv[i + 1]; i += 2
        a[k] = type(a[k])(v) if k in a and not isinstance(a[k], bool) else v
    return a

ARGS = parse_args(); FPS = ARGS["fps"]; SHOT = ARGS["shot"].upper()
FLAGS = set(os.environ.get("SCENE_FLAGS", "").split(","))
SHOT_DUR = {"A": 343 / 24, "C": 192 / 24}
T_SHOT = SHOT_DUR[SHOT]

# ----------------------------------------------------------------------------- helpers
def smoothstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0) if e1 != e0 else 0.0)); return t * t * (3 - 2 * t)
def lerp(a, b, t): return a + (b - a) * t
def vlerp(a, b, t): return Vector(a).lerp(Vector(b), t)
def ease_in_out(t): return smoothstep(0, 1, t)
def n1(t, seed=0.0): return mnoise.noise(Vector((t, seed * 17.17, seed * 3.3))) * 2.0

def clear_scene():
    for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras, bpy.data.curves):
        for x in list(coll): coll.remove(x)

def new_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    return m, nt, nt.nodes.new("ShaderNodeOutputMaterial")

def principled(name, color, rough=0.4, metallic=0.0, spec=0.5):
    m, nt, out = new_mat(name); p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = (*color, 1); p.inputs["Roughness"].default_value = rough; p.inputs["Metallic"].default_value = metallic
    nt.links.new(p.outputs[0], out.inputs[0]); return m

def film_glass(name):
    m, nt, out = new_mat(name); n = nt.nodes; L = nt.links
    fr = n.new("ShaderNodeFresnel"); fr.inputs["IOR"].default_value = 1.5
    tr = n.new("ShaderNodeBsdfTransparent"); tr.inputs["Color"].default_value = (0.94, 0.96, 0.98, 1)
    gl = n.new("ShaderNodeBsdfGlossy"); gl.inputs["Roughness"].default_value = 0.02
    sc = n.new("ShaderNodeMath"); sc.operation = "MULTIPLY"; sc.inputs[1].default_value = 0.45; L.new(fr.outputs[0], sc.inputs[0])
    mix = n.new("ShaderNodeMixShader"); L.new(sc.outputs[0], mix.inputs[0]); L.new(tr.outputs[0], mix.inputs[1]); L.new(gl.outputs[0], mix.inputs[2])
    L.new(mix.outputs[0], out.inputs[0]); return m

def link_obj(name, data):
    ob = bpy.data.objects.new(name, data); bpy.context.collection.objects.link(ob); return ob

def add_cylinder(name, r, h, loc, mat, segs=48, rot=(0, 0, 0), cap=True, bevel=0.0):
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=cap, segments=segs, radius1=r, radius2=r, depth=h)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(mat)
    for p in me.polygons: p.use_smooth = True
    ob = link_obj(name, me); ob.location = loc; ob.rotation_euler = rot
    if bevel: md = ob.modifiers.new("bevel", "BEVEL"); md.width = bevel; md.segments = 2
    return ob

def add_box(name, dims, loc, mat, rot=(0, 0, 0), bevel=0.002):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0); me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(mat)
    ob = link_obj(name, me); ob.scale = dims; ob.location = loc; ob.rotation_euler = rot
    if bevel: md = ob.modifiers.new("bevel", "BEVEL"); md.width = bevel; md.segments = 2
    return ob

# ----------------------------------------------------------------------------- constants (metres, scene seconds)
SLOWMO = 4.0
STOOL_H = 1.15
BEAKER_R, BEAKER_H = 0.078, 0.25   # stainless bucket, top radius (tapers to 0.065 at the base)
Z_BASE = STOOL_H; Z_RIM = STOOL_H + BEAKER_H
H1 = Z_RIM                      # drop height to the floor
ALPHA = 0.12
H_FOUNTAIN = ALPHA * H1 / (1 - ALPHA)   # ~0.19 m, Biggins & Warner
V_REAL = math.sqrt(9.81 * H1 / (1 - ALPHA))
V_SCENE = V_REAL / SLOWMO
BEAD_R, PITCH = 0.0030, 0.0080  # ~#13 bead chain (6 mm balls)
T_RELEASE = 3.8                 # the tug (just after "obviously" starts)
HANG0 = 0.12                    # how far the free end hangs below the rim before the tug
T_EMPTY = 30.0                  # beaker runs out ~ at the end of the explainer

RAMP = 4.5
def speed(t):
    return V_SCENE * smoothstep(T_RELEASE, T_RELEASE + RAMP, t)
def travelled(t):
    """Chain arc length that has flowed past any point: a 25 cm tug over 0.3 s, then the ramp-up (closed-form smoothstep integral)."""
    tug = 0.25 * smoothstep(T_RELEASE, T_RELEASE + 0.3, t)
    a, b = T_RELEASE, T_RELEASE + RAMP
    if t <= a: return tug
    if t >= b: return tug + V_SCENE * ((b - a) / 2 + (t - b))
    u = (t - a) / (b - a); return tug + V_SCENE * (b - a) * (u ** 3 - u ** 4 / 2)
def fountain_h(t):
    return 0.02 * smoothstep(T_RELEASE + 0.6, T_RELEASE + 3.6, t) + (H_FOUNTAIN - 0.02) * smoothstep(T_RELEASE + 3.6, T_RELEASE + 6.8, t)

def bezier(p0, p1, p2, p3, n):
    pts = []
    for i in range(n):
        u = i / (n - 1); v = 1 - u
        pts.append(p0 * v ** 3 + p1 * 3 * v * v * u + p2 * 3 * v * u * u + p3 * u ** 3)
    return pts

PILE = {}   # filled by build_pile(): "pts" (list of Vector along the helix, bottom->top), "cum" (arc length), "len"

def helix_at(L):
    """Point and unit tangent on the pile helix at arc length L from the bottom (clamped)."""
    pts, cum = PILE["pts"], PILE["cum"]
    L = max(0.0, min(L, cum[-1] - 1e-6))
    import bisect
    i = max(1, bisect.bisect_right(cum, L)); i = min(i, len(pts) - 1)
    u = (L - cum[i - 1]) / max(cum[i] - cum[i - 1], 1e-9)
    p = pts[i - 1].lerp(pts[i], u); tg = (pts[i] - pts[i - 1]).normalized()
    return p, tg

def pile_remaining(t):
    return PILE["len"] - travelled(t)

def chain_path(t):
    """Points of the chain path: leaves the top of the pile tangentially, swirls up into the arch,
    over the rim and down to the floor (and a little under it, so surplus beads are hidden)."""
    h = fountain_h(t); hf = h / H_FOUNTAIN
    sway_x = (0.010 * n1(t * 0.7, 1) + 0.004 * n1(t * 2.1, 2)) * hf
    sway_y = (0.010 * n1(t * 0.6, 3) + 0.004 * n1(t * 1.9, 4)) * hf
    S, tg = helix_at(pile_remaining(t))
    A = Vector((lerp(BEAKER_R, 0.05, hf) + sway_x, sway_y, Z_RIM + 0.004 + h))
    F0 = Vector((BEAKER_R + 0.035, 0.0, Z_RIM - 0.18))
    F1 = Vector((BEAKER_R + 0.035, 0.0, -0.05))
    # the pick-up point whips around the coil; keep that inside the bucket by routing the rising leg through a
    # fixed point M just under the rim, then up to a rounded apex (horizontal handles both sides)
    M = Vector((lerp(0.058, 0.032, hf) + 0.3 * sway_x, 0.3 * sway_y, Z_RIM - 0.012))
    dzM = max(A.z - M.z, 0.01); dz2 = A.z - F0.z
    hl = 0.015 + 0.045 * hf
    pts = bezier(S, S + tg * 0.06, M - Vector((0, 0, 0.06)), M, 30)
    pts += bezier(M, M + Vector((0, 0, 0.5 * dzM)), A - Vector((hl, 0, 0)), A, 30)[1:]
    pts += bezier(A, A + Vector((hl, 0, 0)), F0 + Vector((0, 0, 0.5 * dz2)), F0, 40)[1:]
    pts += [F0.lerp(F1, i / 12) for i in range(1, 13)]
    return pts

def path_length(pts, upto_z=None):
    L = 0.0
    for a, b in zip(pts[:-1], pts[1:]):
        if upto_z is not None and b.z < upto_z and a.x > BEAKER_R: return L + (a.z - upto_z) / max(a.z - b.z, 1e-9) * (b - a).length
        L += (b - a).length
    return L

# ----------------------------------------------------------------------------- build
def bead_unit(mat):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=BEAD_R)
    r2 = bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=BEAD_R * 0.33, radius2=BEAD_R * 0.33, depth=PITCH)
    bmesh.ops.rotate(bm, verts=r2["verts"], cent=(0, 0, 0), matrix=__import__("mathutils").Matrix.Rotation(math.pi / 2, 3, "Y"))
    bmesh.ops.translate(bm, verts=r2["verts"], vec=(PITCH / 2, 0, 0))
    me = bpy.data.meshes.new("bead"); bm.to_mesh(me); bm.free(); me.materials.append(mat)
    for p in me.polygons: p.use_smooth = True
    return me

def poly_curve(name, pts):
    cu = bpy.data.curves.new(name, "CURVE"); cu.dimensions = "3D"
    sp = cu.splines.new("POLY"); sp.points.add(len(pts) - 1)
    for p, q in zip(sp.points, pts): p.co = (q.x, q.y, q.z, 1.0)
    return link_obj(name, cu)

def set_curve(ob, pts):
    sp = ob.data.splines[0]
    if len(sp.points) != len(pts):
        ob.data.splines.clear(); sp = ob.data.splines.new("POLY"); sp.points.add(len(pts) - 1)
    for p, q in zip(sp.points, pts): p.co = (q.x, q.y, q.z, 1.0)

def chain_on_curve(name, bead_me, curve_ob, count):
    ob = link_obj(name, bead_me.copy() if False else bead_me)
    ar = ob.modifiers.new("array", "ARRAY"); ar.count = count; ar.use_relative_offset = False; ar.use_constant_offset = True; ar.constant_offset_displace = (PITCH, 0, 0)
    cv = ob.modifiers.new("curve", "CURVE"); cv.object = curve_ob; cv.deform_axis = "POS_X"
    return ob, ar

def build_pile():
    """Chain coiled flat, layer on layer, like a rope coil: each layer is a spiral between the wall (r=0.066)
    and the centre (r=0.028), alternating inward/outward so the chain is continuous. The top layer spirals
    outward so the chain leaves the coil at the wall, right under the rim. Fills PILE with arc lengths."""
    pts = []; z = Z_BASE + 0.006; z_top = Z_RIM - 0.032; layer_h = 0.0066
    n_layers = int((z_top - z) / layer_h)
    r_out, r_in, turns = 0.066, 0.028, 3.0
    for L in range(n_layers):
        outward = (n_layers - 1 - L) % 2 == 0          # last layer ends at the wall
        n = int(turns * 72)
        for i in range(n):
            u = i / n; r = lerp(r_in, r_out, u) if outward else lerp(r_out, r_in, u)
            ang = u * turns * 2 * math.pi + L * 0.7
            jitter = 0.0012 * mnoise.noise(Vector((ang * 0.9, L * 1.3, 0.2)))
            pts.append(Vector(((r + jitter) * math.cos(ang), (r + jitter) * math.sin(ang), z + L * layer_h + u * layer_h * 0.35 + 0.0008 * mnoise.noise(Vector((ang, L, 0.7))))))
    cum = [0.0]
    for a, b in zip(pts[:-1], pts[1:]): cum.append(cum[-1] + (b - a).length)
    PILE["pts"], PILE["cum"], PILE["len"] = pts, cum, cum[-1]
    return pts

def helix_points(r_fn, z0, z1, turns_per_m, n_per_turn=48, phase=0.0):
    pts = []; turns = (z1 - z0) * turns_per_m; N = int(turns * n_per_turn)
    for i in range(N):
        u = i / max(N - 1, 1); ang = phase + u * turns * 2 * math.pi
        r = r_fn(u, ang) + 0.007 * mnoise.noise(Vector((math.cos(ang) * 2.1, math.sin(ang) * 2.1, u * 60))); pts.append(Vector((r * math.cos(ang), r * math.sin(ang), z0 + u * (z1 - z0) + 0.002 * mnoise.noise(Vector((u * 90, ang, 3.0))))))
    return pts

def build_world():
    w = bpy.data.worlds["World"] if "World" in bpy.data.worlds else bpy.data.worlds.new("World")
    bpy.context.scene.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.004, 0.005, 0.008, 1)

def build_set():
    S = {}; build_world()
    floor_m = principled("floor", (0.025, 0.026, 0.030), 0.3)
    S["floor"] = add_box("floor", (6, 6, 0.02), (0, 0, -0.01), floor_m, bevel=0)
    back_m = principled("backdrop", (0.012, 0.014, 0.022), 0.85)
    add_box("backdrop", (10, 0.02, 6), (0, 3.6, 2.5), back_m, bevel=0)
    steel = principled("steel", (0.45, 0.46, 0.48), 0.3, 1.0)
    dark = principled("dark_metal", (0.10, 0.10, 0.11), 0.45, 1.0)
    wood = principled("wood", (0.16, 0.09, 0.045), 0.45)
    # stool
    SX = -0.085  # stool offset: the beaker sits at the stool edge so the chain falls clear to the floor
    add_box("stool_top", (0.34, 0.34, 0.03), (SX, 0, STOOL_H - 0.015), wood, bevel=0.006)
    for sx in (-1, 1):
        for sy in (-1, 1):
            add_cylinder(f"leg{sx}{sy}", 0.014, STOOL_H - 0.03, (SX + sx * 0.14, sy * 0.14, (STOOL_H - 0.03) / 2), dark)
    add_box("stool_brace", (0.30, 0.02, 0.02), (SX, -0.14, 0.35), dark); add_box("stool_brace2", (0.02, 0.30, 0.02), (SX + 0.14, 0, 0.35), dark)
    # stainless bucket: tapered, rolled rim, opaque (the coil is shown from above, not through glass)
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=False, segments=96, radius1=0.065, radius2=BEAKER_R, depth=BEAKER_H)
    me = bpy.data.meshes.new("bucket"); bm.to_mesh(me); bm.free(); me.materials.append(steel)
    for p in me.polygons: p.use_smooth = True
    bk = link_obj("bucket", me); bk.location = (0, 0, Z_BASE + BEAKER_H / 2)
    sol = bk.modifiers.new("solid", "SOLIDIFY"); sol.thickness = 0.0025; sol.offset = 1.0
    add_cylinder("bucket_bottom", 0.065, 0.004, (0, 0, Z_BASE + 0.002), principled("bucket_in", (0.25, 0.25, 0.26), 0.4, 1.0), segs=96)
    # rolled rim = a torus ring (NOT a disc)
    bpy.ops.mesh.primitive_torus_add(major_segments=96, minor_segments=12, major_radius=BEAKER_R + 0.001, minor_radius=0.0035, location=(0, 0, Z_RIM - 0.002))
    rim = bpy.context.object; rim.name = "rim"; rim.data.materials.append(steel)
    for p in rim.data.polygons: p.use_smooth = True
    # chain material + unit
    bead_m = principled("bead", (0.80, 0.80, 0.82), 0.22, 1.0)
    bead_me = bead_unit(bead_m)
    # pile: a messy heap of loops (random radius / centre per turn), top turns hugging the wall so the chain
    # lifts off near the rim. Built once; consumption = shrinking the array from the top.
    S["pile_curve"] = poly_curve("pile_path", build_pile())
    S["pile"], S["pile_ar"] = chain_on_curve("pile", bead_me, S["pile_curve"], 10)
    # flowing chain
    S["path"] = poly_curve("chain_path", chain_path(0.0))
    S["chain"], S["chain_ar"] = chain_on_curve("chain", bead_me, S["path"], int(2.6 / PITCH))
    # heap on the floor: flat spiral at the landing point
    hp = []
    for i in range(1400):
        u = i / 1400; ang = u * 26 * math.pi; r = 0.012 + 0.09 * u
        hp.append(Vector((BEAKER_R + 0.035 + r * math.cos(ang), r * math.sin(ang), 0.003 + 0.006 * (i % 2))))
    S["heap_curve"] = poly_curve("heap_path", hp)
    S["heap"], S["heap_ar"] = chain_on_curve("heap", bead_me, S["heap_curve"], 1)
    for k in ("pile", "heap"):
        S[k].cycles.use_motion_blur = False
    # lights
    def light(name, typ, loc, energy, color, size=1.0, rot=(0, 0, 0)):
        ld = bpy.data.lights.new(name, typ); ld.energy = energy; ld.color = color
        if typ == "AREA": ld.size = size
        ob = link_obj(name, ld); ob.location = loc; ob.rotation_euler = rot; return ob
    S["key"] = light("key", "AREA", (1.2, -1.4, 2.4), 110.0, (1.0, 0.9, 0.78), size=1.2, rot=(math.radians(45), 0, math.radians(40)))
    S["rim"] = light("rim", "AREA", (-1.3, 1.1, 2.0), 150.0, (0.35, 0.55, 1.0), size=0.8, rot=(math.radians(-50), 0, math.radians(-130)))
    S["fill"] = light("fill", "AREA", (-1.2, -1.6, 1.0), 14.0, (0.6, 0.75, 1.0), size=2.5, rot=(math.radians(70), 0, math.radians(-35)))
    S["spot"] = light("spot", "AREA", (0.4, -0.5, 2.3), 70.0, (1.0, 0.85, 0.7), size=0.3, rot=(math.radians(15), 0, math.radians(40)))
    S["top"] = light("top", "AREA", (0.05, -0.05, Z_RIM + 0.9), 40.0, (1.0, 0.95, 0.9), size=0.35, rot=(0, 0, 0))
    # camera
    cd = bpy.data.cameras.new("cam"); cam = link_obj("cam", cd); bpy.context.scene.camera = cam
    tgt = link_obj("cam_target", None)
    con = cam.constraints.new("TRACK_TO"); con.target = tgt; con.track_axis = "TRACK_NEGATIVE_Z"; con.up_axis = "UP_Y"
    cd.dof.use_dof = "nodof" not in FLAGS; cd.dof.focus_object = tgt
    S["cam"], S["cam_target"] = cam, tgt
    return S

STATE = {}

def catmull(keys, t):
    """Catmull-Rom through (time, Vector) keys, clamped."""
    ts = [k[0] for k in keys]
    if t <= ts[0]: return keys[0][1].copy()
    if t >= ts[-1]: return keys[-1][1].copy()
    i = max(j for j in range(len(ts) - 1) if ts[j] <= t)
    p0 = keys[max(i - 1, 0)][1]; p1 = keys[i][1]; p2 = keys[i + 1][1]; p3 = keys[min(i + 2, len(keys) - 1)][1]
    u = (t - ts[i]) / (ts[i + 1] - ts[i]); u = u * u * (3 - 2 * u)
    return 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u * u * u)

# shot A choreography: look into the bucket at the coil -> tilt to the hanging end -> the tug, hold on the rim
# while the coil unwinds -> pull out as the fountain grows.   (time, camera position), (time, look-at), (time, lens)
CAM_A = [(0.0, Vector((0.16, -0.26, Z_RIM + 0.46))), (3.0, Vector((0.30, -0.40, Z_RIM + 0.24))), (6.6, Vector((0.44, -0.46, Z_RIM + 0.08))),
         (10.5, Vector((0.42, -0.86, 1.56))), (14.3, Vector((0.38, -0.96, 1.62)))]
TGT_A = [(0.0, Vector((0.0, 0.0, Z_RIM - 0.06))), (3.0, Vector((0.08, 0.0, Z_RIM - 0.03))), (6.6, Vector((0.11, 0.0, Z_RIM + 0.0))),
         (10.5, Vector((0.06, 0.0, Z_RIM + 0.08))), (14.3, Vector((0.06, 0.0, Z_RIM + 0.10)))]
LENS_A = [(0.0, 40.0), (3.0, 40.0), (6.6, 42.0), (10.5, 36.0), (14.3, 36.0)]

def update(t):
    S = STATE["S"]; cam, tgt = S["cam"], S["cam_target"]
    pts = chain_path(t); set_curve(S["path"], pts)
    d = travelled(t)
    # free end: hangs HANG0 below the rim before the tug, then runs down the path and onto the floor
    if "hang_len" not in STATE: STATE["hang_len"] = path_length(pts, upto_z=Z_RIM - HANG0)
    end_len = STATE["hang_len"] + d
    S["chain"].location.x = -(d % PITCH)
    S["chain_ar"].count = max(2, min(int(end_len / PITCH), int(2.6 / PITCH)))
    S["pile_ar"].count = max(2, int(pile_remaining(t) / PITCH))
    S["heap_ar"].count = max(1, min(1390 * 3, int(max(0.0, end_len - path_length(pts) + 0.05) / PITCH)))
    if SHOT == "A":
        tt = min(t, SHOT_DUR["A"])
        cam.location = catmull(CAM_A, tt); tgt.location = catmull(TGT_A, tt)
        cam.data.lens = catmull([(k[0], Vector((k[1], 0, 0))) for k in LENS_A], tt).x; cam.data.dof.aperture_fstop = 3.2
    else:  # C hero close-up orbit of the hovering loop
        k = min(t / T_SHOT, 1.0)
        ang = math.radians(lerp(-25, 20, k)); rad = lerp(0.55, 0.48, ease_in_out(k))
        cam.location = Vector((0.05 + rad * math.sin(ang), -rad * math.cos(ang), Z_RIM + 0.17 + 0.08 * ease_in_out(k)))
        tgt.location = Vector((0.06, 0, Z_RIM + 0.10)); cam.data.lens = 55; cam.data.dof.aperture_fstop = 2.8

def shot_time(frame_float):
    # shot C shows steady state: start its clock 12 s into the event
    return frame_float / FPS + (14.0 if SHOT == "C" else 0.0)

def on_frame(scene):
    update(shot_time(scene.frame_current_final if hasattr(scene, "frame_current_final") else scene.frame_current + scene.frame_subframe))

def setup_render(res, samples):
    sc = bpy.context.scene; sc.render.engine = "CYCLES"; c = sc.cycles
    c.device = "CPU"; c.samples = samples; c.use_adaptive_sampling = True; c.adaptive_threshold = 0.1; c.adaptive_min_samples = 4
    c.use_denoising = "nodenoise" not in FLAGS; c.denoiser = "OPENIMAGEDENOISE"; c.denoising_input_passes = "RGB_ALBEDO_NORMAL"; c.denoising_use_gpu = False
    c.max_bounces = 6; c.diffuse_bounces = 2; c.glossy_bounces = 3; c.transmission_bounces = 4; c.volume_bounces = 0; c.transparent_max_bounces = 8
    c.caustics_reflective = False; c.caustics_refractive = False; c.blur_glossy = 1.0; c.sample_clamp_indirect = 8.0
    sc.render.use_persistent_data = True
    sc.render.use_motion_blur = bool(ARGS["mblur"]); sc.render.motion_blur_shutter = 0.5
    sc.render.resolution_x = res; sc.render.resolution_y = res * 16 // 9; sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGB"; sc.render.image_settings.compression = 20
    sc.render.fps = FPS
    sc.view_settings.view_transform = "AgX"
    try: sc.view_settings.look = "AgX - Medium High Contrast"
    except Exception: pass
    sc.view_settings.exposure = -0.1
    sc.use_nodes = True; nt = sc.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    rl = nt.nodes.new("CompositorNodeRLayers"); gl = nt.nodes.new("CompositorNodeGlare"); comp = nt.nodes.new("CompositorNodeComposite")
    gl.glare_type = "BLOOM"
    for k, v in (("Threshold", 1.5), ("Strength", 0.12), ("Size", 0.5)):
        try: gl.inputs[k].default_value = v
        except Exception: pass
    nt.links.new(rl.outputs["Image"], gl.inputs["Image"]); nt.links.new(gl.outputs["Image"], comp.inputs["Image"])

def main():
    clear_scene(); STATE["S"] = build_set(); setup_render(ARGS["res"], ARGS["samples"])
    bpy.app.handlers.frame_change_pre.clear(); bpy.app.handlers.frame_change_pre.append(on_frame)
    os.makedirs(ARGS["out"], exist_ok=True); sc = bpy.context.scene
    frames = [ARGS["start"]] if ARGS["preview"] else range(ARGS["start"], ARGS["end"])
    for f in frames:
        path = os.path.join(ARGS["out"], f"{SHOT}_{f:04d}.png")
        if os.path.exists(path) and not ARGS["preview"]: continue
        sc.frame_set(f); sc.render.filepath = path
        t0 = time.time(); bpy.ops.render.render(write_still=True)
        print(f"FRAME {SHOT} {f} {time.time() - t0:.1f}s", flush=True)

main()

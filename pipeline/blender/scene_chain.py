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
BEAKER_R, BEAKER_H = 0.072, 0.25
Z_BASE = STOOL_H; Z_RIM = STOOL_H + BEAKER_H
H1 = Z_RIM                      # drop height to the floor
ALPHA = 0.12
H_FOUNTAIN = ALPHA * H1 / (1 - ALPHA)   # ~0.19 m, Biggins & Warner
V_REAL = math.sqrt(9.81 * H1 / (1 - ALPHA))
V_SCENE = V_REAL / SLOWMO
BEAD_R, PITCH = 0.0030, 0.0080  # ~#13 bead chain (6 mm balls)
T_RELEASE = 1.0
T_EMPTY = 30.0                  # beaker runs out ~ at the end of the explainer

def speed(t):
    return V_SCENE * smoothstep(T_RELEASE, T_RELEASE + 4.5, t)
def travelled(t):
    # integral of speed; smoothstep integral done numerically once per call (cheap: closed form of cubic)
    a, b = T_RELEASE, T_RELEASE + 4.5
    if t <= a: return 0.0
    if t >= b: return V_SCENE * ((b - a) / 2 + (t - b))
    u = (t - a) / (b - a); return V_SCENE * (b - a) * (u ** 3 - u ** 4 / 2)
def fountain_h(t):
    return 0.02 * smoothstep(1.6, 5.8, t) + (H_FOUNTAIN - 0.02) * smoothstep(5.8, 9.6, t)
def pile_z(t):
    full, empty = Z_RIM - 0.035, Z_BASE + 0.02
    return lerp(full, empty, smoothstep(T_RELEASE, T_EMPTY, t))

def bezier(p0, p1, p2, p3, n):
    pts = []
    for i in range(n):
        u = i / (n - 1); v = 1 - u
        pts.append(p0 * v ** 3 + p1 * 3 * v * v * u + p2 * 3 * v * u * u + p3 * u ** 3)
    return pts

def chain_path(t):
    """Points of the chain path from inside the pile, over the arch, down to the floor (and under it)."""
    h = fountain_h(t); hf = h / H_FOUNTAIN
    sway_x = (0.010 * n1(t * 0.7, 1) + 0.004 * n1(t * 2.1, 2)) * hf
    sway_y = (0.010 * n1(t * 0.6, 3) + 0.004 * n1(t * 1.9, 4)) * hf
    S = Vector((-0.02 + 0.01 * n1(t * 0.3, 5), 0.0, pile_z(t)))
    A = Vector((lerp(BEAKER_R, 0.045, hf) + sway_x, sway_y, Z_RIM + 0.004 + h))
    F0 = Vector((BEAKER_R + 0.035, 0.0, Z_RIM - 0.18))
    F1 = Vector((BEAKER_R + 0.035, 0.0, -0.05))
    dz1 = A.z - S.z; dz2 = A.z - F0.z
    pts = bezier(S, S + Vector((0, 0, 0.55 * dz1)), A - Vector((0.035 * (0.3 + hf), 0, 0)), A, 40)
    pts += bezier(A, A + Vector((0.035 * (0.3 + hf), 0, 0)), F0 + Vector((0, 0, 0.5 * dz2)), F0, 40)[1:]
    pts += [F0.lerp(F1, i / 12) for i in range(1, 13)]
    return pts

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
    # beaker (thin film glass): open cylinder with a bottom disc
    glass = film_glass("beaker_glass")
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=False, segments=96, radius1=BEAKER_R, radius2=BEAKER_R, depth=BEAKER_H)
    me = bpy.data.meshes.new("beaker"); bm.to_mesh(me); bm.free(); me.materials.append(glass)
    for p in me.polygons: p.use_smooth = True
    bk = link_obj("beaker", me); bk.location = (0, 0, Z_BASE + BEAKER_H / 2)
    sol = bk.modifiers.new("solid", "SOLIDIFY"); sol.thickness = 0.003; sol.offset = 1.0
    add_cylinder("beaker_bottom", BEAKER_R, 0.004, (0, 0, Z_BASE + 0.002), glass, segs=96)
    # a white graduation strip hint
    add_box("grad", (0.002, 0.03, 0.14), (BEAKER_R + 0.0035, 0.0, Z_BASE + 0.12), principled("grad", (0.9, 0.9, 0.9), 0.6), bevel=0)
    # chain material + unit
    bead_m = principled("bead", (0.80, 0.80, 0.82), 0.22, 1.0)
    bead_me = bead_unit(bead_m)
    # flowing chain
    S["path"] = poly_curve("chain_path", chain_path(0.0))
    S["chain"], S["chain_ar"] = chain_on_curve("chain", bead_me, S["path"], int(2.6 / PITCH))
    # pile in beaker: double helix stack (two radii) from the bottom to pile_z(t)
    S["pile_curve"] = poly_curve("pile_path", helix_points(lambda u, a: 0.056 if int(a / (2 * math.pi)) % 2 == 0 else 0.042, Z_BASE + 0.006, Z_RIM, 1 / 0.0085))
    S["pile"], S["pile_ar"] = chain_on_curve("pile", bead_me, S["pile_curve"], 10)
    S["pile_len"] = sum((b - a).length for a, b in zip(S["pile_curve"].data.splines[0].points[:-1], S["pile_curve"].data.splines[0].points[1:])) if False else None
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
    # camera
    cd = bpy.data.cameras.new("cam"); cam = link_obj("cam", cd); bpy.context.scene.camera = cam
    tgt = link_obj("cam_target", None)
    con = cam.constraints.new("TRACK_TO"); con.target = tgt; con.track_axis = "TRACK_NEGATIVE_Z"; con.up_axis = "UP_Y"
    cd.dof.use_dof = "nodof" not in FLAGS; cd.dof.focus_object = tgt
    S["cam"], S["cam_target"] = cam, tgt
    return S

STATE = {}

def update(t):
    S = STATE["S"]; cam, tgt = S["cam"], S["cam_target"]
    # chain flow + path
    set_curve(S["path"], chain_path(t))
    d = travelled(t)
    S["chain"].location.x = -(d % PITCH)
    # pile shrinks from the top as chain is consumed; heap grows
    pile_pts = S["pile_curve"].data.splines[0].points
    seg = 2 * math.pi * 0.049 / 48  # approx arc per helix sample
    n_pile_max = int(len(pile_pts) * seg / PITCH)
    frac = (pile_z(t) - (Z_BASE + 0.006)) / (Z_RIM - (Z_BASE + 0.006))
    S["pile_ar"].count = max(2, int(n_pile_max * frac))
    S["heap_ar"].count = max(1, min(1390 * 3, int(d / PITCH)))
    apex = Vector((0.05, 0, Z_RIM + fountain_h(t)))
    if SHOT == "A":
        k = ease_in_out(min(t / T_SHOT, 1.0))
        cam.location = vlerp((0.46, -0.86, 1.44), (0.37, -0.70, 1.52), k)
        tgt.location = vlerp((0.06, 0, 1.36), (0.06, 0, 1.46), k)
        cam.data.lens = lerp(34, 40, k); cam.data.dof.aperture_fstop = 4.0
    else:  # C hero close-up
        k = min(t / T_SHOT, 1.0)
        ang = math.radians(lerp(-25, 20, k)); rad = lerp(0.55, 0.48, ease_in_out(k))
        cam.location = Vector((0.05 + rad * math.sin(ang), -rad * math.cos(ang), Z_RIM + 0.17 + 0.08 * ease_in_out(k)))
        tgt.location = Vector((0.06, 0, Z_RIM + 0.10)); cam.data.lens = 55; cam.data.dof.aperture_fstop = 2.8

def shot_time(frame_float):
    # shot C shows steady state: start its clock 12 s into the event
    return frame_float / FPS + (12.0 if SHOT == "C" else 0.0)

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

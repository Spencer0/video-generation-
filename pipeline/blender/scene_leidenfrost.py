"""Procedural Blender scene: Leidenfrost droplets on a hot brushed-steel pan.

Run headless:
  blender -b -noaudio -P pipeline/blender/scene_leidenfrost.py -- --shot M --start 0 --end 300 \
      --out videos/004-leidenfrost/build/frames/M [--res 576] [--samples 20] [--fps 30] [--preview]

Scale: 1 Blender unit = 1 cm (a 2 mm droplet has radius 0.2), so Cycles' ray epsilons behave.
Droplets are art-directed, not simulated: a seeded skitter path (Catmull-Rom through waypoints with
eased direction changes), volume-preserving wobble, slight elongation along the velocity, a hover gap
above the metal, and slow evaporation (shrinking radius). Motion blur on (shutter 0.5).

Shots (nominal lengths in SHOT_DUR):
  M  macro tracking shot, one drop: enters right at t=0, skitters, exits left at the end (loop-friendly)
  C  cooler pan: a drop lands, spreads into a puddle (for the split comparison)
  X  cutaway: half-droplet on a cross-sectioned pan, exaggerated vapor layer + escaping vapor
  G  wide on the whole skillet with a dozen droplets dancing, one continuous push-in onto a single droplet
  P  payoff: macro drop -> cutaway pull-back -> drop skitters out of frame, hold on the metal
"""
import bpy, bmesh, math, random, sys, os, time
from mathutils import Vector, Matrix
from mathutils import noise as mnoise

def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    a = {"shot": "M", "start": 0, "end": 1, "out": "/tmp/frames", "res": 576, "samples": 14, "preview": False, "fps": 30}
    i = 0
    while i < len(argv):
        k = argv[i].lstrip("-")
        if k == "preview": a["preview"] = True; i += 1; continue
        v = argv[i + 1]; i += 2
        a[k] = type(a[k])(v) if k in a and not isinstance(a[k], bool) else v
    return a

ARGS = parse_args(); FPS = ARGS["fps"]; SHOT = ARGS["shot"].upper()
SHOT_DUR = {"M": 10.0, "C": 3.0, "X": 12.2, "G": 7.0, "P": 8.0}
T_SHOT = SHOT_DUR[SHOT]

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
def principled(name, color, rough=0.5, metallic=0.0):
    m, nt, out = new_mat(name); p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = (*color, 1); p.inputs["Roughness"].default_value = rough; p.inputs["Metallic"].default_value = metallic
    nt.links.new(p.outputs[0], out.inputs[0]); return m
def link_obj(name, data):
    ob = bpy.data.objects.new(name, data); bpy.context.collection.objects.link(ob); return ob

# ----------------------------------------------------------------------------- materials
def pan_material(warm=1.0):
    """Brushed steel: anisotropic metal, roughness variation, faint smudges, stretched-noise bump."""
    m, nt, out = new_mat("pan"); n = nt.nodes; L = nt.links
    p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Metallic"].default_value = 1.0
    p.inputs["Base Color"].default_value = (0.40 * warm + 0.02, 0.37, 0.34, 1)
    p.inputs["Anisotropic"].default_value = 0.65; p.inputs["Anisotropic Rotation"].default_value = 0.0
    tc = n.new("ShaderNodeTexCoord"); mp = n.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1.0, 120.0, 1.0)
    L.new(tc.outputs["Object"], mp.inputs["Vector"])
    brush = n.new("ShaderNodeTexNoise"); brush.inputs["Scale"].default_value = 6.0; brush.inputs["Detail"].default_value = 6; brush.inputs["Roughness"].default_value = 0.7
    L.new(mp.outputs[0], brush.inputs["Vector"])
    bump = n.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.08; L.new(brush.outputs["Fac"], bump.inputs["Height"]); L.new(bump.outputs[0], p.inputs["Normal"])
    smud = n.new("ShaderNodeTexNoise"); smud.inputs["Scale"].default_value = 0.35; smud.inputs["Detail"].default_value = 3; L.new(tc.outputs["Object"], smud.inputs["Vector"])
    rough = n.new("ShaderNodeMapRange"); rough.inputs["From Min"].default_value = 0.35; rough.inputs["From Max"].default_value = 0.65
    rough.inputs["To Min"].default_value = 0.26; rough.inputs["To Max"].default_value = 0.38; L.new(smud.outputs["Fac"], rough.inputs["Value"]); L.new(rough.outputs[0], p.inputs["Roughness"])
    L.new(p.outputs[0], out.inputs[0]); return m

def water_material():
    m, nt, out = new_mat("water"); n = nt.nodes; L = nt.links
    g = n.new("ShaderNodeBsdfGlass"); g.inputs["IOR"].default_value = 1.333; g.inputs["Roughness"].default_value = 0.0; g.inputs["Color"].default_value = (0.94, 0.98, 1.0, 1)
    L.new(g.outputs[0], out.inputs[0]); return m

def interior_material():
    """Cut face of the droplet: milky blue-white so the cross-section reads as water, not a lens."""
    m, nt, out = new_mat("water_interior"); n = nt.nodes; L = nt.links
    p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Base Color"].default_value = (0.55, 0.78, 0.95, 1); p.inputs["Roughness"].default_value = 0.35
    p.inputs["Alpha"].default_value = 0.6
    try: p.inputs["Transmission Weight"].default_value = 0.45
    except Exception: pass
    L.new(p.outputs[0], out.inputs[0]); return m

def vapor_layer_material():
    """Thin, uneven, flowing: transparent mixed with a pale cyan emission by scrolling noise."""
    m, nt, out = new_mat("vapor_layer"); n = nt.nodes; L = nt.links
    tc = n.new("ShaderNodeTexCoord"); tv = n.new("ShaderNodeValue"); tv.name = "time"; tv.outputs[0].default_value = 0.0
    off = n.new("ShaderNodeCombineXYZ"); L.new(tv.outputs[0], off.inputs["X"])
    add = n.new("ShaderNodeVectorMath"); add.operation = "ADD"; L.new(tc.outputs["Object"], add.inputs[0]); L.new(off.outputs[0], add.inputs[1])
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 18.0; nz.inputs["Detail"].default_value = 4; L.new(add.outputs[0], nz.inputs["Vector"])
    mr = n.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = 0.35; mr.inputs["From Max"].default_value = 0.75; mr.inputs["To Max"].default_value = 0.55
    L.new(nz.outputs["Fac"], mr.inputs["Value"])
    em = n.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (0.75, 0.95, 1.0, 1); em.inputs["Strength"].default_value = 0.7
    tr = n.new("ShaderNodeBsdfTransparent"); mix = n.new("ShaderNodeMixShader")
    L.new(mr.outputs[0], mix.inputs[0]); L.new(tr.outputs[0], mix.inputs[1]); L.new(em.outputs[0], mix.inputs[2]); L.new(mix.outputs[0], out.inputs[0])
    return m

def wisp_material():
    m, nt, out = new_mat("wisp"); n = nt.nodes; L = nt.links
    tc = n.new("ShaderNodeTexCoord"); nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 3.0; nz.inputs["Detail"].default_value = 3; L.new(tc.outputs["Generated"], nz.inputs["Vector"])
    # soft radial falloff on the billboard
    sub = n.new("ShaderNodeVectorMath"); sub.operation = "SUBTRACT"; sub.inputs[1].default_value = (0.5, 0.5, 0.5); L.new(tc.outputs["Generated"], sub.inputs[0])
    ln = n.new("ShaderNodeVectorMath"); ln.operation = "LENGTH"; L.new(sub.outputs[0], ln.inputs[0])
    fall = n.new("ShaderNodeMapRange"); fall.inputs["From Min"].default_value = 0.15; fall.inputs["From Max"].default_value = 0.5; fall.inputs["To Min"].default_value = 1.0; fall.inputs["To Max"].default_value = 0.0
    L.new(ln.outputs["Value"], fall.inputs["Value"])
    mul = n.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; L.new(fall.outputs[0], mul.inputs[0]); L.new(nz.outputs["Fac"], mul.inputs[1])
    alpha = n.new("ShaderNodeValue"); alpha.name = "alpha"; alpha.outputs[0].default_value = 0.45
    mul2 = n.new("ShaderNodeMath"); mul2.operation = "MULTIPLY"; L.new(mul.outputs[0], mul2.inputs[0]); L.new(alpha.outputs[0], mul2.inputs[1])
    em = n.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (0.8, 0.95, 1.0, 1); em.inputs["Strength"].default_value = 1.6
    tr = n.new("ShaderNodeBsdfTransparent"); mix = n.new("ShaderNodeMixShader")
    L.new(mul2.outputs[0], mix.inputs[0]); L.new(tr.outputs[0], mix.inputs[1]); L.new(em.outputs[0], mix.inputs[2]); L.new(mix.outputs[0], out.inputs[0])
    return m

def hot_block_material():
    """Cross-section of the pan: graphite with an amber glow that fades with depth."""
    m, nt, out = new_mat("hot_block"); n = nt.nodes; L = nt.links
    p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Base Color"].default_value = (0.022, 0.022, 0.024, 1); p.inputs["Roughness"].default_value = 0.6; p.inputs["Metallic"].default_value = 0.5
    tc = n.new("ShaderNodeTexCoord"); sep = n.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Object"], sep.inputs[0])
    mr = n.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = 0.47; mr.inputs["From Max"].default_value = 0.5; mr.inputs["To Min"].default_value = 0.0; mr.inputs["To Max"].default_value = 0.09
    L.new(sep.outputs["Z"], mr.inputs["Value"])
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 2.0; L.new(tc.outputs["Object"], nz.inputs["Vector"])
    nm = n.new("ShaderNodeMapRange"); nm.inputs["From Min"].default_value = 0.3; nm.inputs["From Max"].default_value = 0.7; nm.inputs["To Min"].default_value = 0.7; nm.inputs["To Max"].default_value = 1.3; L.new(nz.outputs["Fac"], nm.inputs["Value"])
    mul = n.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; L.new(mr.outputs[0], mul.inputs[0]); L.new(nm.outputs[0], mul.inputs[1])
    em = n.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (1.0, 0.42, 0.08, 1); L.new(mul.outputs[0], em.inputs["Strength"])
    add = n.new("ShaderNodeAddShader"); L.new(p.outputs[0], add.inputs[0]); L.new(em.outputs[0], add.inputs[1]); L.new(add.outputs[0], out.inputs[0])
    return m

# ----------------------------------------------------------------------------- geometry
def sphere_mesh(name, r, mat, half=False):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=96, v_segments=48, radius=r)
    if half:   # keep y >= 0, flat cut face toward the camera at -y
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        res = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, 0), plane_no=(0, -1, 0), clear_outer=True)
        edges = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
        filled = bmesh.ops.holes_fill(bm, edges=edges)
        for f in filled["faces"]: f.material_index = 1
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(mat)
    if half: me.materials.append(interior_material())
    for p in me.polygons: p.use_smooth = True
    ob = link_obj(name, me)
    if not half:
        md = ob.modifiers.new("subsurf", "SUBSURF"); md.levels = 1; md.render_levels = 1
    return ob

def add_plane(name, size, loc, mat):
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=size)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if mat: me.materials.append(mat)
    ob = link_obj(name, me); ob.location = loc; return ob
def build_skillet(mat, handle_mat):
    """Lathe a skillet profile (flat floor, sloped wall, rolled lip) + a dark handle."""
    prof = [(0.0, 0.0), (11.6, 0.0), (12.9, 1.7), (13.25, 1.85), (13.4, 1.7), (13.1, 1.55), (12.6, 1.55), (11.4, -0.25), (0.0, -0.25)]
    bm = bmesh.new()
    verts = [bm.verts.new((r, 0.0, z)) for r, z in prof]
    edges = [bm.edges.new((verts[i], verts[i + 1])) for i in range(len(verts) - 1)]
    bmesh.ops.spin(bm, geom=verts + edges, cent=(0, 0, 0), axis=(0, 0, 1), angle=2 * math.pi, steps=160, use_merge=True)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    me = bpy.data.meshes.new("skillet"); bm.to_mesh(me); bm.free(); me.materials.append(mat)
    for p in me.polygons: p.use_smooth = True
    ob = link_obj("skillet", me)
    h = add_box("handle", (17, 2.6, 1.1), (21.0, 0.0, 1.9), handle_mat); h.rotation_euler = (0, math.radians(-4), 0)
    add_box("handle_neck", (3.0, 3.4, 0.6), (13.6, 0.0, 1.6), handle_mat)
    return ob

def add_box(name, dims, loc, mat):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0); me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(mat)
    ob = link_obj(name, me); ob.scale = dims; ob.location = loc; return ob

# ----------------------------------------------------------------------------- droplet kinematics
class Skitter:
    """Seeded waypoint path on the pan with eased direction changes (Catmull-Rom in time)."""
    def __init__(self, seed, start, end, duration, speed=2.6, jitter=1.6, n=None, waypoints=None):
        rng = random.Random(seed); self.keys = []
        if waypoints:
            self.keys = [(t, Vector((x, y, 0.0))) for t, x, y in waypoints]; return
        start, end = Vector((start[0], start[1], 0.0)), Vector((end[0], end[1], 0.0))
        n = n or max(3, int(duration / 1.1))
        for i in range(n + 1):
            u = i / n; base = start.lerp(end, u)
            off = Vector((rng.uniform(-1, 1) * jitter, rng.uniform(-1, 1) * jitter, 0)) * (0.0 if i in (0, n) else 1.0)
            self.keys.append((u * duration + (rng.uniform(-0.25, 0.25) * duration / n if 0 < i < n else 0.0), base + off))
        self.keys.sort(key=lambda k: k[0])
    def pos(self, t):
        ks = self.keys; ts = [k[0] for k in ks]
        if t <= ts[0]: return ks[0][1] + (ks[1][1] - ks[0][1]).normalized() * (t - ts[0]) * 2.0
        if t >= ts[-1]: return ks[-1][1] + (ks[-1][1] - ks[-2][1]).normalized() * (t - ts[-1]) * 2.0
        i = max(j for j in range(len(ts) - 1) if ts[j] <= t)
        p0 = ks[max(i - 1, 0)][1]; p1 = ks[i][1]; p2 = ks[i + 1][1]; p3 = ks[min(i + 2, len(ks) - 1)][1]
        u = (t - ts[i]) / (ts[i + 1] - ts[i])
        return 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3)
    def vel(self, t, h=1 / 120):
        return (self.pos(t + h) - self.pos(t - h)) / (2 * h)

def place_drop(ob, path, t, r0, seed, life=None, gap=0.012, extra=None):
    """Position + wobble + heading + evaporation for one droplet. Returns current radius (0 = gone)."""
    r = r0 * (max(0.0, 1 - t / life) ** 0.5 if life else 1.0)
    if r < 0.004: ob.hide_render = True; return 0.0
    ob.hide_render = False
    p = path.pos(t) if path else Vector((0, 0, 0)); v = path.vel(t) if path else Vector((0, 0, 0))
    sp = v.length; heading = math.atan2(v.y, v.x) if sp > 1e-6 else 0.0
    w1 = 1 + 0.06 * math.sin(t * 17.0 + seed) + 0.03 * n1(t * 3.0, seed)
    w2 = 1 + 0.06 * math.sin(t * 13.0 + seed * 2.1) + 0.03 * n1(t * 2.7, seed + 1)
    elong = 1 + 0.10 * min(sp / 4.0, 1.0)
    sx, sy = w1 * elong, w2 / elong; sz = 0.78 / (sx * sy)
    ob.scale = (r * sx, r * sy, r * sz); ob.rotation_euler = (0, 0, heading)
    hover = gap + 0.004 * abs(math.sin(t * 9.0 + seed))
    ob.location = Vector((p.x, p.y, r * sz + hover)) + (extra or Vector((0, 0, 0)))
    return r

# ----------------------------------------------------------------------------- set
def build_world():
    w = bpy.data.worlds["World"] if "World" in bpy.data.worlds else bpy.data.worlds.new("World")
    bpy.context.scene.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.0, 0.0, 0.0, 1)

def light(name, typ, loc, energy, color, size=1.0, rot=(0, 0, 0)):
    ld = bpy.data.lights.new(name, typ); ld.energy = energy; ld.color = color
    if typ == "AREA": ld.size = size
    ob = link_obj(name, ld); ob.location = loc; ob.rotation_euler = rot; ob.visible_camera = False; return ob

def build_set():
    S = {}; build_world()
    water = water_material()
    cut = SHOT == "X" or SHOT == "P"
    if SHOT in ("M", "C", "P"):
        S["pan"] = add_plane("pan", 60, (0, 0, 0), pan_material(0.7 if SHOT == "C" else 1.0))
    if SHOT == "G":
        handle = principled("handle", (0.015, 0.015, 0.016), 0.5)
        S["skillet"] = build_skillet(pan_material(), handle)
        add_plane("stove", 80, (0, 0, -0.3), principled("stove", (0.012, 0.012, 0.014), 0.7))
    if cut:
        # cross-sectioned pan: the block's top face is the brushed surface, the front face (y=0) glows amber inside
        S["block"] = add_box("block", (14, 6, 2.5), (0, 3, -1.25), hot_block_material())
        S["block_top"] = add_plane("block_top", 3.5, (0, 3.5, 0.001), pan_material())   # bmesh grid size is a half-extent
        S["half"] = sphere_mesh("half_drop", 1.0, water, half=True); S["half"].hide_render = True
        S["layer"] = sphere_mesh("layer", 1.0, vapor_layer_material()); S["layer"].hide_render = True
        S["layer_mat"] = S["layer"].data.materials[0]
        wm = wisp_material(); S["wisps"] = []
        for i in range(6):
            bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.09)
            me = bpy.data.meshes.new(f"wisp{i}"); bm.to_mesh(me); bm.free(); me.materials.append(wm)
            ob = link_obj(f"wisp{i}", me); ob.rotation_euler = (math.radians(90), 0, 0); ob.hide_render = True; ob.visible_shadow = False; S["wisps"].append(ob)
        S["wisp_mat"] = wm
    # environment the water can reflect: a graphite backdrop and a dim overhead panel (midnight-blue tint)
    back = add_plane("backdrop", 45, (0, 30, 20), None); back.rotation_euler = (math.radians(90), 0, 0)
    bm_, nt_, out_ = new_mat("backdrop"); pb = nt_.nodes.new("ShaderNodeBsdfPrincipled"); pb.inputs["Base Color"].default_value = (0.03, 0.035, 0.05, 1); pb.inputs["Roughness"].default_value = 0.9
    nt_.links.new(pb.outputs[0], out_.inputs[0]); back.data.materials.append(bm_)
    S["top"] = light("top", "AREA", (0, 2, 14), 650.0, (0.9, 0.86, 0.8), size=16.0, rot=(0, 0, 0))
    S["drops"] = [sphere_mesh(f"drop{i}", 1.0, water) for i in range(16)]
    for d in S["drops"]: d.hide_render = True
    # lighting: grazing warm key, cool rim from behind, soft fill
    S["key"] = light("key", "AREA", (6, -4, 2.2), 1300.0, (1.0, 0.86, 0.70), size=5.0, rot=(math.radians(62), 0, math.radians(55)))
    S["rim"] = light("rim", "AREA", (-5, 7, 3.0), 700.0, (0.55, 0.72, 1.0), size=4.0, rot=(math.radians(-50), 0, math.radians(-145)))
    S["fill"] = light("fill", "AREA", (-6, -6, 6), 160.0, (0.7, 0.8, 1.0), size=12.0, rot=(math.radians(45), 0, math.radians(-45)))
    S["spec"] = light("spec", "AREA", (1, -9, 1.0), 300.0, (1.0, 0.9, 0.8), size=0.6, rot=(math.radians(84), 0, 0))
    cd = bpy.data.cameras.new("cam"); cam = link_obj("cam", cd); bpy.context.scene.camera = cam
    tgt = link_obj("cam_target", None)
    con = cam.constraints.new("TRACK_TO"); con.target = tgt; con.track_axis = "TRACK_NEGATIVE_Z"; con.up_axis = "UP_Y"
    cd.dof.use_dof = True; cd.dof.focus_object = tgt; cd.clip_start = 0.05
    S["cam"], S["cam_target"] = cam, tgt
    # paths
    S["paths"] = {
        "M": Skitter(4, None, None, 10.0, waypoints=[(0, 3.1, 0.4), (1.5, 1.6, -0.5), (3.0, 0.2, 0.9), (4.5, -1.2, -0.3), (6.0, 0.6, -1.0), (7.5, -1.0, 0.8), (8.6, -2.6, 0.2), (10.0, -5.8, -0.4)]),
        "G0": Skitter(11, (2.6, 1.4), (0.6, -0.4), 7.0, jitter=0.9),
        "P": Skitter(21, (2.5, 0.3), (-2.5, -0.3), 3.0, jitter=0.6), "P2": Skitter(22, (0.0, 0.0), (9.0, 0.8), 1.4, jitter=0.4, n=3),
    }
    rngG = random.Random(77)
    for i in range(1, 16):
        a0, a1 = rngG.uniform(0, 2 * math.pi), rngG.uniform(0, 2 * math.pi); r0, r1 = rngG.uniform(2, 9.5), rngG.uniform(2, 9.5)
        S["paths"][f"G{i}"] = Skitter(100 + i, (r0 * math.cos(a0), r0 * math.sin(a0)), (r1 * math.cos(a1), r1 * math.sin(a1)), 7.0, jitter=2.2)
    return S

STATE = {}
def cam_follow(S, target_xy, lag_key, t, limit, offset, lens, fstop, look_dz=0.0):
    """Camera that tracks the droplet with a smoothed, limited pan; keeps the drop readable."""
    prev = STATE.get(lag_key)
    tx = max(-limit, min(limit, target_xy.x)); ty = max(-limit * 0.5, min(limit * 0.5, target_xy.y))
    cur = Vector((tx, ty, 0)) if prev is None else prev.lerp(Vector((tx, ty, 0)), 0.18)
    STATE[lag_key] = cur
    cam, tgt = S["cam"], S["cam_target"]
    cam.location = cur + Vector(offset); tgt.location = cur + Vector((0, 0, 0.16 + look_dz)); cam.data.lens = lens; cam.data.dof.aperture_fstop = max(fstop, 4.0)
    cam.data.dof.focus_object = S["drops"][0]

def update(t):
    S = STATE["S"]; cam, tgt = S["cam"], S["cam_target"]; drops = S["drops"]
    for d in drops: d.hide_render = True
    if SHOT == "M":
        r = place_drop(drops[0], S["paths"]["M"], t, 0.21, 1.0, life=60.0)
        cam_follow(S, drops[0].location, "lagM", t, 3.0, (0.9, -3.2, 0.95), 95, 2.8)
    elif SHOT == "G":
        rsz = [0.26] + [0.11 + 0.14 * ((i * 7919) % 10) / 10 for i in range(1, 16)]
        for i, d in enumerate(drops): place_drop(d, S["paths"][f"G{i}"], t, rsz[i], 2.0 + i, life=(120 if i else 200))
        lead = drops[0].location
        k = ease_in_out(min(t / 6.4, 1.0))
        wide_cam, wide_tgt = Vector((2.0, -31.0, 37.0)), Vector((0.0, 1.0, 0.3))
        near_cam, near_tgt = lead + Vector((0.9, -3.2, 0.95)), lead + Vector((0, 0, 0.0))
        cam.location = wide_cam.lerp(near_cam, k); tgt.location = wide_tgt.lerp(near_tgt, k)
        cam.data.lens = lerp(40, 95, k); cam.data.dof.aperture_fstop = lerp(9.0, 4.0, k); cam.data.dof.focus_object = drops[0]
    elif SHOT == "C":
        d = drops[0]; d.hide_render = False
        k = smoothstep(0.15, 0.55, t); z0 = 1.2 * (1 - smoothstep(0.0, 0.22, t)) ** 1.0
        spread = 1 + 1.3 * k + 0.08 * math.sin(t * 20) * (1 - smoothstep(0.5, 1.3, t)); flat = lerp(1.0, 0.27, k) * (1 - 0.1 * smoothstep(1.0, 3.0, t))
        r = 0.21
        d.scale = (r * spread, r * spread, r * flat); d.location = (0.0, 0.0, r * flat * 0.92 + z0)
        cam.location = (1.2, -3.0, 0.9); tgt.location = (0, 0, 0.12); cam.data.lens = 95; cam.data.dof.aperture_fstop = 2.8
    elif SHOT == "X":
        # cutaway: half drop glides slowly; slow-motion window 6.5..9.5 s
        slow = 1.0 - 0.75 * (smoothstep(6.3, 6.9, t) - smoothstep(9.3, 9.9, t))
        tt = STATE.get("tX", 0.0) + slow / FPS * 1.0 if "tX" in STATE else 0.0
        # (tt integrates with the handler's frame order; fine for sequential renders, recomputed below for safety)
        xs = 0.9 * math.sin(t * 0.45) ; STATE["tX"] = tt
        half = S["half"]; half.hide_render = False
        r = 0.22; w1 = 1 + 0.05 * math.sin(t * 9.0); w2 = 1 + 0.05 * math.sin(t * 7.0 + 1.0); sz = 0.84 / (w1 * w2)
        gap = 0.03 + 0.004 * math.sin(t * 6.0)
        half.scale = (r * w1, r * w2, r * sz); half.location = (xs, 0.0, r * sz + gap)
        layer = S["layer"]; layer.hide_render = False
        layer.scale = (r * w1 * 0.80, r * w2 * 0.80, gap * 0.42); layer.location = (xs, 0.0, gap * 0.5)
        S["layer_mat"].node_tree.nodes["time"].outputs[0].default_value = t * 0.9
        for i, wv in enumerate(S["wisps"]):
            per = 0.9; ph = ((t * (0.8 + 0.1 * (i % 3)) + i * 0.37) % per) / per
            side = -1 if i % 2 == 0 else 1; ang = (i * 0.9) % (math.pi)
            wv.hide_render = False
            wv.location = (xs + side * (r * 1.0 + ph * 0.12), 0.04 + 0.08 * (i % 3), gap + ph * 0.26 + 0.02)
            s = 0.22 + ph * 0.5; wv.scale = (s, s, s)
            wv.rotation_euler = (math.radians(90), 0, side * ph * 0.6)
        S["wisp_mat"].node_tree.nodes["alpha"].outputs[0].default_value = 0.45
        k = ease_in_out(min(t / 1.2, 1.0))
        cam.location = vlerp((xs + 1.4, -3.4, 1.3), (xs + 0.3, -2.9, 0.40), k); tgt.location = vlerp((xs, 0.3, 0.2), (xs, 0.0, 0.16), k)
        cam.data.lens = lerp(90, 100, k); cam.data.dof.aperture_fstop = lerp(4.0, 7.0, k); cam.data.dof.focus_object = S["half"]
    elif SHOT == "P":
        cut_now = 3.0 <= t < 6.4
        if "pan" in S: S["pan"].hide_render = cut_now
        S["block"].hide_render = not cut_now; S["block_top"].hide_render = not cut_now
        if t < 3.0:   # macro drop
            place_drop(drops[0], S["paths"]["P"], t, 0.22, 3.0)
            cam_follow(S, drops[0].location, "lagP", t, 2.0, (0.8, -2.8, 0.75), 100, 2.6)
            for wv in S["wisps"]: wv.hide_render = True
            S["half"].hide_render = True; S["layer"].hide_render = True
        elif t < 6.4:  # cutaway, pulling back
            k = ease_in_out(min((t - 3.0) / 3.0, 1.0)); r = 0.22; gap = 0.03 + 0.004 * math.sin(t * 6)
            w1 = 1 + 0.05 * math.sin(t * 9.0); w2 = 1 + 0.05 * math.sin(t * 7.0 + 1.0); sz = 0.84 / (w1 * w2)
            half = S["half"]; half.hide_render = False; half.scale = (r * w1, r * w2, r * sz); half.location = (0, 0, r * sz + gap)
            layer = S["layer"]; layer.hide_render = False; layer.scale = (r * w1 * 0.80, r * w2 * 0.80, gap * 0.42); layer.location = (0, 0, gap * 0.5)
            S["layer_mat"].node_tree.nodes["time"].outputs[0].default_value = t * 0.9
            for i, wv in enumerate(S["wisps"]):
                per = 0.9; ph = ((t * (0.8 + 0.1 * (i % 3)) + i * 0.37) % per) / per; side = -1 if i % 2 == 0 else 1
                wv.hide_render = False; wv.location = (side * (r * 1.0 + ph * 0.12), 0.04 + 0.08 * (i % 3), gap + ph * 0.26 + 0.02)
                s = 0.22 + ph * 0.5; wv.scale = (s, s, s); wv.rotation_euler = (math.radians(90), 0, side * ph * 0.6)
            cam.location = vlerp((0.3, -2.6, 0.38), (0.6, -5.2, 1.1), k); tgt.location = vlerp((0, 0, 0.17), (0, 0.3, 0.12), k)
            cam.data.lens = 100; cam.data.dof.aperture_fstop = lerp(6.0, 4.0, k)
        else:          # back to the real surface: the drop skitters out of frame, camera holds on the metal
            S["half"].hide_render = True; S["layer"].hide_render = True
            for wv in S["wisps"]: wv.hide_render = True
            place_drop(drops[0], S["paths"]["P2"], t - 6.4, 0.22, 3.0)
            cam.location = (0.9, -3.4, 1.0); tgt.location = (0.6, 0.6, 0.16); cam.data.lens = 95; cam.data.dof.aperture_fstop = 3.5

def on_frame(scene):
    f = scene.frame_current_final if hasattr(scene, "frame_current_final") else scene.frame_current
    update(f / FPS)

def setup_render(res, samples):
    sc = bpy.context.scene; sc.render.engine = "CYCLES"; c = sc.cycles
    c.device = "CPU"; c.samples = samples; c.use_adaptive_sampling = True; c.adaptive_threshold = 0.1; c.adaptive_min_samples = 4
    c.use_denoising = True; c.denoiser = "OPENIMAGEDENOISE"; c.denoising_input_passes = "RGB_ALBEDO_NORMAL"; c.denoising_use_gpu = False
    c.max_bounces = 6; c.diffuse_bounces = 2; c.glossy_bounces = 3; c.transmission_bounces = 6; c.volume_bounces = 0; c.transparent_max_bounces = 6
    c.caustics_reflective = False; c.caustics_refractive = False; c.blur_glossy = 1.0; c.sample_clamp_indirect = 6.0
    sc.render.use_persistent_data = True; sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5
    sc.render.resolution_x = res; sc.render.resolution_y = res * 16 // 9; sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGB"; sc.render.image_settings.compression = 20
    sc.render.fps = FPS; sc.view_settings.view_transform = "AgX"
    try: sc.view_settings.look = "AgX - Medium High Contrast"
    except Exception: pass
    sc.view_settings.exposure = 0.1
    sc.use_nodes = True; nt = sc.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    rl = nt.nodes.new("CompositorNodeRLayers"); gl = nt.nodes.new("CompositorNodeGlare"); comp = nt.nodes.new("CompositorNodeComposite")
    gl.glare_type = "BLOOM"
    for k, v in (("Threshold", 1.6), ("Strength", 0.08), ("Size", 0.5)):
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
        # warm the camera lag so a standalone frame matches a sequential render
        for g in range(max(ARGS["start"], f - 40), f): update(g / FPS)
        sc.frame_set(f); sc.render.filepath = path
        t0 = time.time(); bpy.ops.render.render(write_still=True)
        print(f"FRAME {SHOT} {f} {time.time() - t0:.1f}s", flush=True)

main()

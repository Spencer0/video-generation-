"""Procedural Blender scene for video 006: people who were struck by lightning and lived.

Run headless:
  blender -b -noaudio -P pipeline/blender/scene_struck.py -- --shot H --start 0 --end 233 \
      --out videos/006-struck-by-lightning/build/frames/H [--res 576] [--samples 12] [--preview]

Shots (all event times are scene seconds, chosen from the real VO word times in build/timeline.json):
  H  Roy Sullivan, park ranger, on a Blue Ridge outcrop with a fire-lookout tower behind him.
     Seven strikes in a comic montage (hat pops, eyebrows smoke off, hair catches fire twice, shoe smokes).
  G  Lee Trevino, 1975: sitting under a striped umbrella by a pond on a golf course. Lightning hits the
     pond, the umbrella flies off; he gets up and holds a 1-iron at the sky. Nothing happens.
  F  "You" in a rainy field at night, extreme slow motion: stepped leader, return stroke, a glowing
     flashover sheath skims over the skin, steam lifts off, the shoes blow off.
  R  A hiker near a lone oak in a meadow. The oak is hit; a ring of ground current spreads out and a
     glowing path runs up one leg and down the other.
  L  Close-up of a forearm on a hospital sheet: a fern-shaped Lichtenberg figure grows, then fades.

Characters are vinyl-toy figures: ellipsoid parts parented to joint empties, posed per frame in Python
(pure functions of time, no keyframes, so any frame renders standalone). Per-object fades (smoke, sheath,
flames, bolts) use ob.color alpha read by an Object Info node, so one material serves many objects.
"""
import bpy, bmesh, math, random, sys, os, time
from mathutils import Vector, Euler, Matrix
from mathutils import noise as mnoise

def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    a = {"shot": "H", "start": 0, "end": 1, "out": "/tmp/frames", "res": 576, "samples": 12, "preview": False, "fps": 24}
    i = 0
    while i < len(argv):
        k = argv[i].lstrip("-")
        if k == "preview": a["preview"] = True; i += 1; continue
        v = argv[i + 1]; i += 2
        a[k] = type(a[k])(v) if k in a and not isinstance(a[k], bool) else v
    return a

ARGS = parse_args(); FPS = ARGS["fps"]; SHOT = ARGS["shot"].upper()

# ----------------------------------------------------------------------------- event times (keep in sync with beats.js / sfx_cues.py)
# H: hook 0..3.25 + roy 3.25..10.5 (strike one, 1942: hole in the shoe), then the hair section from H_HAIR0 (bg_plan "hair" starts there)
H_STRIKES = [0.0, 10.75, 11.45, 12.10, 12.70]   # strike 1 (1942) and strikes 3-6 (hair on fire); strike 2 is shot T, strike 7 shot B
H_HAIR0 = 10.5; H_SHOE_CU = 8.6; H_POUR0, H_POUR1 = 13.30, 14.6
G_STRIKE = 1.45; G_STAND0, G_STAND1 = 1.95, 2.7; G_RAISE0, G_RAISE1 = 2.85, 3.35; G_SHRUG = 5.3   # golf beat: 'hit' 1.48, 'Hold up' 2.86, 'Not even God' 3.97
F_LEADER0, F_STRIKE = 0.10, 1.20; F_SHOES = 6.40; F_STEAM = 2.6   # why beat: 'Speed.' 1.17, 'skims' 4.52, 'out through the feet' 5.69-6.46
R_STRIKE = 1.38; R_RING1 = 3.6; R_LEG0, R_LEG1 = 3.85, 5.05; R_RADIUS = 6.0
L_GROW0, L_GROW1, L_FADE0, L_FADE1 = 0.55, 1.9, 3.25, 4.4
T_STRIKE1 = 1.15; T_BROWS = 2.78; T_WINUP0, T_WINUP1 = 3.40, 3.95; T_STRIKE2 = 4.55; T_THUMB = 5.2      # truck beat: 'through his truck window' 0.97-1.84, 'eyebrows' 2.80, 'Windows up' 3.43
B_STRIKE = 0.80; B_BEAR0 = 2.2; B_STAND0, B_STAND1 = 3.3, 4.0; B_GRAB = 4.45; B_BONK = 5.55; B_WIN = 6.5   # bear beat: 'hit' 0.81, 'bear' 3.80, 'steal' 4.50, 'stick' 5.76

def smoothstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0) if e1 != e0 else 0.0)); return t * t * (3 - 2 * t)
def lerp(a, b, t): return a + (b - a) * t
def vlerp(a, b, t): return Vector(a).lerp(Vector(b), t)
def n1(t, seed=0.0): return mnoise.noise(Vector((t, seed * 17.17, seed * 3.3))) * 2.0
def pulse(t, t0, attack=0.02, hold=0.05, decay=0.18):
    if t < t0: return 0.0
    k = t - t0
    if k < attack: return k / attack
    if k < attack + hold: return 1.0
    return math.exp(-(k - attack - hold) / decay)

# ----------------------------------------------------------------------------- basic builders
def clear_scene():
    for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras, bpy.data.curves):
        for x in list(coll): coll.remove(x)
def new_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    return m, nt, nt.nodes.new("ShaderNodeOutputMaterial")
def principled(name, color, rough=0.5, metallic=0.0, coat=0.0, emit=None, emit_s=0.0):
    m, nt, out = new_mat(name); p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = (*color, 1); p.inputs["Roughness"].default_value = rough; p.inputs["Metallic"].default_value = metallic
    p.inputs["Coat Weight"].default_value = coat
    if emit: p.inputs["Emission Color"].default_value = (*emit, 1); p.inputs["Emission Strength"].default_value = emit_s
    nt.links.new(p.outputs[0], out.inputs[0]); return m
def emissive(name, color, strength):
    m, nt, out = new_mat(name); e = nt.nodes.new("ShaderNodeEmission"); e.inputs["Color"].default_value = (*color, 1); e.inputs["Strength"].default_value = strength
    nt.links.new(e.outputs[0], out.inputs[0]); return m
def faded_emission(name, color, strength, noise_scale=0.0, flow=None, streak=False):
    """Emission * ob.color alpha (Object Info), transparent where faint. Optional noise breakup (animated via 'flow' value)."""
    m, nt, out = new_mat(name); n = nt.nodes; L = nt.links
    oi = n.new("ShaderNodeObjectInfo"); em = n.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (*color, 1)
    s = n.new("ShaderNodeMath"); s.operation = "MULTIPLY"; s.inputs[1].default_value = strength; L.new(oi.outputs["Alpha"], s.inputs[0])
    vis = oi.outputs["Alpha"]
    if noise_scale:
        tc = n.new("ShaderNodeTexCoord"); nz = n.new("ShaderNodeTexNoise"); nz.noise_dimensions = "4D"; nz.inputs["Scale"].default_value = noise_scale; nz.inputs["Detail"].default_value = 3
        if streak:   # stretched along Z: rivulets of current running down the body rather than confetti
            mp = n.new("ShaderNodeVectorMath"); mp.operation = "MULTIPLY"; mp.inputs[1].default_value = (1.0, 1.0, 0.18)
            L.new(tc.outputs["Object"], mp.inputs[0]); L.new(mp.outputs[0], nz.inputs["Vector"])
        else: L.new(tc.outputs["Object"], nz.inputs["Vector"])
        fv = n.new("ShaderNodeValue"); fv.name = "flow"; L.new(fv.outputs[0], nz.inputs["W"])
        mr = n.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = 0.45 if streak else 0.5; mr.inputs["From Max"].default_value = 0.62 if streak else 0.7; L.new(nz.outputs["Fac"], mr.inputs["Value"])
        if streak:   # brighter at grazing angles: reads as a film hugging the surface
            lw = n.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.35
            rim = n.new("ShaderNodeMath"); rim.operation = "MULTIPLY_ADD"; rim.inputs[1].default_value = 1.4; rim.inputs[2].default_value = 0.35; L.new(lw.outputs["Facing"], rim.inputs[0])
            mr2 = n.new("ShaderNodeMath"); mr2.operation = "MULTIPLY"; mr2.use_clamp = True; L.new(mr.outputs[0], mr2.inputs[0]); L.new(rim.outputs[0], mr2.inputs[1]); mr = mr2
        s2 = n.new("ShaderNodeMath"); s2.operation = "MULTIPLY"; L.new(s.outputs[0], s2.inputs[0]); L.new(mr.outputs[0], s2.inputs[1]); s = s2
        v2 = n.new("ShaderNodeMath"); v2.operation = "MULTIPLY"; L.new(oi.outputs["Alpha"], v2.inputs[0]); L.new(mr.outputs[0], v2.inputs[1]); vis = v2.outputs[0]
    L.new(s.outputs[0], em.inputs["Strength"])
    tr = n.new("ShaderNodeBsdfTransparent"); mix = n.new("ShaderNodeMixShader"); cl = n.new("ShaderNodeMath"); cl.operation = "MINIMUM"; cl.inputs[1].default_value = 1.0
    L.new(vis, cl.inputs[0]); L.new(cl.outputs[0], mix.inputs[0]); L.new(tr.outputs[0], mix.inputs[1]); L.new(em.outputs[0], mix.inputs[2]); L.new(mix.outputs[0], out.inputs[0])
    return m
def smoke_material(name, color=(0.55, 0.55, 0.57)):
    m, nt, out = new_mat(name); n = nt.nodes; L = nt.links
    oi = n.new("ShaderNodeObjectInfo"); p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Base Color"].default_value = (*color, 1); p.inputs["Roughness"].default_value = 1.0
    p.inputs["Emission Color"].default_value = (*color, 1); p.inputs["Emission Strength"].default_value = 0.12
    tc = n.new("ShaderNodeTexCoord"); nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 2.2; nz.inputs["Detail"].default_value = 4; L.new(tc.outputs["Object"], nz.inputs["Vector"])
    lw = n.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.5
    f = n.new("ShaderNodeMath"); f.operation = "SUBTRACT"; f.inputs[0].default_value = 1.0; L.new(lw.outputs["Facing"], f.inputs[1])   # 1 at centre, 0 at the silhouette
    f3 = n.new("ShaderNodeMath"); f3.operation = "POWER"; f3.inputs[1].default_value = 2.5; L.new(f.outputs[0], f3.inputs[0])   # alpha ~ (1-facing)^2.5: no hard silhouette
    a1 = n.new("ShaderNodeMath"); a1.operation = "MULTIPLY"; L.new(f3.outputs[0], a1.inputs[0]); L.new(nz.outputs["Fac"], a1.inputs[1])
    a2 = n.new("ShaderNodeMath"); a2.operation = "MULTIPLY"; a2.use_clamp = True; L.new(a1.outputs[0], a2.inputs[0]); L.new(oi.outputs["Alpha"], a2.inputs[1])
    tr = n.new("ShaderNodeBsdfTransparent"); mix = n.new("ShaderNodeMixShader")
    L.new(a2.outputs[0], mix.inputs[0]); L.new(tr.outputs[0], mix.inputs[1]); L.new(p.outputs[0], mix.inputs[2]); L.new(mix.outputs[0], out.inputs[0]); return m
def link_obj(name, data, parent=None):
    ob = bpy.data.objects.new(name, data); bpy.context.collection.objects.link(ob)
    if parent is not None: ob.parent = parent
    return ob
def mesh_from_bm(name, bm, mat=None, smooth=True):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if mat: me.materials.append(mat)
    for p in me.polygons: p.use_smooth = smooth
    return me
def ellipsoid(name, loc, scale, mat, parent=None, subdiv=3, rot=(0, 0, 0)):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=12, radius=1.0)
    ob = link_obj(name, mesh_from_bm(name, bm, mat), parent); ob.location = loc; ob.scale = scale; ob.rotation_euler = rot; return ob
def cylinder(name, r0, r1, h, loc, mat, segs=16, rot=(0, 0, 0), parent=None, smooth=True):
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=r0, radius2=r1, depth=h)
    ob = link_obj(name, mesh_from_bm(name, bm, mat, smooth), parent); ob.location = loc; ob.rotation_euler = rot; return ob
def box(name, dims, loc, mat, rot=(0, 0, 0), parent=None):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * dims[0], v.co.y * dims[1], v.co.z * dims[2]))
    ob = link_obj(name, mesh_from_bm(name, bm, mat, False), parent); ob.location = loc; ob.rotation_euler = rot; return ob
def empty(name, loc=(0, 0, 0), parent=None):
    ob = link_obj(name, None, parent); ob.location = loc; ob.empty_display_size = 0.05; return ob
def seg_between(name, a, b, r, mat, segs=8):
    a, b = Vector(a), Vector(b); d = b - a
    return cylinder(name, r, r, d.length, (a + b) / 2, mat, segs=segs, rot=d.to_track_quat("Z", "Y").to_euler(), smooth=False)
def curve_obj(name, pts, mat, radius, parent=None, taper=None):
    cu = bpy.data.curves.new(name, "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = radius; cu.bevel_resolution = 1; cu.use_fill_caps = True
    sp = cu.splines.new("POLY"); sp.points.add(len(pts) - 1)
    for i, (p, q) in enumerate(zip(sp.points, pts)):
        p.co = (q[0], q[1], q[2], 1.0)
        if taper: p.radius = taper(i / max(1, len(pts) - 1))
    cu.materials.append(mat); ob = link_obj(name, cu, parent); ob.visible_shadow = False; return ob
def set_alpha(ob, a, r=1.0):
    ob.color = (r, 1, 1, max(0.0, min(1.0, a))); ob.hide_render = a <= 0.002
def displaced_grid(name, size, segs, fz, mat, loc=(0, 0, 0)):
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=segs, y_segments=segs, size=size)
    for v in bm.verts: v.co.z = fz(v.co.x, v.co.y)
    ob = link_obj(name, mesh_from_bm(name, bm, mat)); ob.location = loc; return ob
def noise2(x, y, s, seed=0.0): return mnoise.noise(Vector((x / s, y / s, seed)))

# ----------------------------------------------------------------------------- lightning
def midpoint_path(p0, p1, levels, rough, rng):
    pts = [Vector(p0), Vector(p1)]
    for lv in range(levels):
        out = [pts[0]]
        for a, b in zip(pts[:-1], pts[1:]):
            m = (a + b) / 2; seg = (b - a).length
            d = Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 0.3))) * seg * rough * (0.6 ** lv * 1.6)
            out += [m + d, b]
        pts = out
    return pts

class Bolt:
    """Main channel + branches as bevelled POLY curves; leader growth via bevel_factor_end; glow via ob.color alpha."""
    def __init__(self, name, top, tip, seed, mat, radius=0.9, nbranch=7, blen=(40, 160), converge=10, mid=None, via=None):
        rng = random.Random(seed); top, tip = Vector(top), Vector(tip)
        tail = min(40.0, (top - tip).length * 0.08)   # the last stretch is a finer, rougher path so it stays jagged close to the camera
        mid = Vector(mid) if mid else tip + Vector((rng.uniform(-0.3, 0.3) * tail, rng.uniform(-0.2, 0.2) * tail, tail))
        if via:   # come in along a chosen line: ... -> mid -> via -> tip (e.g. through an open window)
            self.main = midpoint_path(top, mid, 7, 0.10, rng) + midpoint_path(mid, Vector(via), 5, 0.12, rng)[1:] + [tip]
        else:
            self.main = midpoint_path(top, mid, 7, 0.10, rng) + midpoint_path(mid, tip, 6, 0.16, rng)[1:]
        n = len(self.main)
        # taper: full width up high, thinning over the last stretch so the channel does not read as a light-sabre near the camera
        self.obs = [(curve_obj(name, self.main, mat, radius, taper=lambda u: 1.0 - 0.6 * smoothstep(0.75, 1.0, u)), 0.0, 1.0)]
        cum = [0.0]
        for a, b in zip(self.main[:-1], self.main[1:]): cum.append(cum[-1] + (b - a).length)
        for j in range(nbranch):
            u = rng.uniform(0.08, 0.8); i = min(range(n), key=lambda k: abs(cum[k] / cum[-1] - u))
            root = self.main[i]; side = Vector((rng.uniform(-1, 1), rng.uniform(-0.6, 0.6), -rng.uniform(0.5, 1.3))).normalized()
            L = (1 - u) * rng.uniform(*blen); pts = midpoint_path(root, root + side * L, 4, 0.2, rng)
            self.obs.append((curve_obj(f"{name}_b{j}", pts, mat, radius * 0.4, taper=lambda v: 1.0 - 0.7 * v), u, rng.uniform(0.45, 0.8)))
        self.radius = radius
    def set(self, grow, glow, thick=1.0, struck=None):
        """grow: fraction of the main channel revealed (leader), glow: 0..1 brightness, struck: white (return stroke) vs violet (leader)."""
        thick = min(thick, 1.2); white = (1.0 if grow >= 0.999 else 0.0) if struck is None else struck
        for k, (ob, u, br) in enumerate(self.obs):
            if k == 0: f = grow
            else: f = max(0.0, min(1.0, (grow - u) / (0.3 * (1 - u) + 0.05)))
            ob.data.bevel_factor_end = f; set_alpha(ob, glow * (1.0 if k == 0 else br) if f > 0.001 else 0.0, white)
            ob.data.bevel_depth = self.radius * (1.0 if k == 0 else 0.4) * thick

def bolt_material():
    # the leader is violet, the return stroke white-blue: colour follows brightness
    m, nt, out = new_mat("bolt"); n = nt.nodes; L = nt.links
    oi = n.new("ShaderNodeObjectInfo"); mixc = n.new("ShaderNodeMix"); mixc.data_type = "RGBA"
    mixc.inputs[6].default_value = (0.55, 0.42, 1.0, 1); mixc.inputs[7].default_value = (0.86, 0.92, 1.0, 1)
    sc = n.new("ShaderNodeSeparateColor"); L.new(oi.outputs["Color"], sc.inputs[0]); L.new(sc.outputs[0], mixc.inputs[0])   # ob.color R: 0 leader (violet), 1 struck (white); not tied to brightness, so fades stay white
    s = n.new("ShaderNodeMath"); s.operation = "MULTIPLY"; s.inputs[1].default_value = 30.0; L.new(oi.outputs["Alpha"], s.inputs[0])
    em = n.new("ShaderNodeEmission"); L.new(mixc.outputs[2], em.inputs["Color"]); L.new(s.outputs[0], em.inputs["Strength"]); L.new(em.outputs[0], out.inputs[0])
    return m

# ----------------------------------------------------------------------------- toy characters
SKIN = (0.80, 0.56, 0.42)
class Figure:
    """Toy figure facing -Y. Joints: root > pelvis > spine > neck; spine > shoulders > elbows > hands; pelvis > hips > knees > ankles."""
    def __init__(self, name, shirt, pants, shoes=(0.12, 0.08, 0.06), skin=SKIN, hair=(0.16, 0.10, 0.06), sheath_mat=None, hat=None):
        self.name = name; mk = lambda n, c, r=0.55, coat=0.25: principled(f"{name}_{n}", c, r, coat=coat)
        self.m_skin = mk("skin", skin, 0.45, 0.35); self.m_shirt = mk("shirt", shirt, 0.7, 0.1); self.m_pants = mk("pants", pants, 0.75, 0.1)
        self.m_shoe = mk("shoe", shoes, 0.35, 0.6); self.m_hair = mk("hair", hair, 0.6, 0.2); dark = principled(f"{name}_eye", (0.02, 0.02, 0.025), 0.15, coat=1.0)
        self.parts = []; J = {}
        def part(n, loc, scale, mat, parent, rot=(0, 0, 0)):
            ob = ellipsoid(f"{name}_{n}", loc, scale, mat, parent, rot=rot); self.parts.append(ob); return ob
        J["root"] = empty(f"{name}_root"); J["pelvis"] = empty(f"{name}_pelvis", (0, 0, 0.95), J["root"])
        part("hipsb", (0, 0, 0.02), (0.19, 0.13, 0.12), self.m_pants, J["pelvis"])
        J["spine"] = empty(f"{name}_spine", (0, 0, 0.05), J["pelvis"])
        part("torso", (0, 0, 0.27), (0.21, 0.145, 0.30), self.m_shirt, J["spine"])
        J["neck"] = empty(f"{name}_neck", (0, 0, 0.56), J["spine"])
        part("neckp", (0, 0, 0.03), (0.06, 0.06, 0.06), self.m_skin, J["neck"])
        J["head"] = empty(f"{name}_head", (0, 0, 0.19), J["neck"])
        part("head", (0, 0, 0), (0.165, 0.155, 0.175), self.m_skin, J["head"])
        self.hair = part("hairp", (0, 0.025, 0.045), (0.17, 0.16, 0.15), self.m_hair, J["head"])
        for sx in (-1, 1):
            ellipsoid(f"{name}_eye{sx}", (0.058 * sx, -0.143, 0.02), (0.024, 0.014, 0.03), dark, J["head"])
            part(f"ear{sx}", (0.163 * sx, 0.0, 0.0), (0.025, 0.04, 0.05), self.m_skin, J["head"])
        self.brows = [box(f"{name}_brow{sx}", (0.05, 0.015, 0.012), (0.058 * sx, -0.145, 0.072), self.m_hair, rot=(0, 0, -0.12 * sx), parent=J["head"]) for sx in (-1, 1)]
        part("nose", (0, -0.165, -0.025), (0.028, 0.03, 0.03), self.m_skin, J["head"])
        ellipsoid(f"{name}_mouth", (0, -0.15, -0.075), (0.045, 0.012, 0.012), principled(f"{name}_lip", (0.35, 0.1, 0.08), 0.4), J["head"])
        for side, sx in (("l", 1), ("r", -1)):
            J[f"{side}_sho"] = empty(f"{name}_{side}sho", (0.25 * sx, 0, 0.47), J["spine"])
            part(f"{side}_uarm", (0, 0, -0.15), (0.068, 0.068, 0.18), self.m_shirt, J[f"{side}_sho"])
            J[f"{side}_elb"] = empty(f"{name}_{side}elb", (0, 0, -0.30), J[f"{side}_sho"])
            part(f"{side}_farm", (0, 0, -0.13), (0.055, 0.055, 0.16), self.m_skin, J[f"{side}_elb"])
            J[f"{side}_hand"] = empty(f"{name}_{side}hand", (0, 0, -0.30), J[f"{side}_elb"])
            part(f"{side}_handp", (0, 0, -0.01), (0.055, 0.04, 0.065), self.m_skin, J[f"{side}_hand"])
            J[f"{side}_hip"] = empty(f"{name}_{side}hip", (0.10 * sx, 0, -0.02), J["pelvis"])
            part(f"{side}_thigh", (0, 0, -0.22), (0.088, 0.088, 0.25), self.m_pants, J[f"{side}_hip"])
            J[f"{side}_knee"] = empty(f"{name}_{side}knee", (0, 0, -0.44), J[f"{side}_hip"])
            part(f"{side}_shin", (0, 0, -0.21), (0.072, 0.072, 0.24), self.m_pants, J[f"{side}_knee"])
            J[f"{side}_ankle"] = empty(f"{name}_{side}ankle", (0, 0, -0.43), J[f"{side}_knee"])
            J[f"{side}_shoe"] = empty(f"{name}_{side}shoeE", (0, 0, 0), J[f"{side}_ankle"])
            part(f"{side}_shoep", (0, -0.045, -0.045), (0.075, 0.13, 0.055), self.m_shoe, J[f"{side}_shoe"])
        self.J = J
        if hat == "ranger":   # campaign hat: wide flat brim + pinched crown, leather band
            felt = principled(f"{name}_felt", (0.42, 0.30, 0.17), 0.8); band = principled(f"{name}_band", (0.12, 0.07, 0.04), 0.5)
            J["hat"] = empty(f"{name}_hat", (0, 0.0, 0.11), J["head"])
            cylinder(f"{name}_brim", 0.33, 0.33, 0.014, (0, 0, 0), felt, segs=40, parent=J["hat"])
            cylinder(f"{name}_crown", 0.15, 0.06, 0.15, (0, 0, 0.08), felt, segs=4, rot=(0, 0, math.pi / 4), parent=J["hat"])
            cylinder(f"{name}_band", 0.152, 0.14, 0.03, (0, 0, 0.02), band, segs=4, rot=(0, 0, math.pi / 4), parent=J["hat"])
            badge = principled(f"{name}_badge", (0.9, 0.7, 0.25), 0.25, 1.0)
            ellipsoid(f"{name}_badgep", (0.09, -0.135, 0.38), (0.03, 0.01, 0.035), badge, J["spine"])
        elif hat == "cap":
            capm = principled(f"{name}_capm", (0.95, 0.95, 0.93), 0.6)
            J["hat"] = empty(f"{name}_hat", (0, 0.0, 0.07), J["head"])
            ellipsoid(f"{name}_capdome", (0, 0.01, 0.0), (0.172, 0.168, 0.11), capm, J["hat"])
            ellipsoid(f"{name}_visor", (0, -0.17, -0.02), (0.12, 0.09, 0.012), capm, J["hat"], rot=(0.15, 0, 0))
        self.sheath = []
        if sheath_mat:   # flashover: a glowing film just outside the skin and clothes
            for ob in self.parts:
                s = ellipsoid(ob.name + "_sh", ob.location, Vector(ob.scale) * 1.0 + Vector((0.022, 0.022, 0.022)), sheath_mat, ob.parent, rot=ob.rotation_euler)
                s.visible_shadow = False; self.sheath.append(s)
        self.set_sheath(0.0)
    def set_sheath(self, a):
        for s in self.sheath: set_alpha(s, a)
    def pose(self, P, root_loc=(0, 0, 0), root_rot=0.0, pelvis_z=0.95):
        J = self.J; J["root"].location = root_loc; J["root"].rotation_euler = (0, 0, root_rot); J["pelvis"].location = (0, 0, pelvis_z)
        for k in ("pelvis", "spine", "neck", "head", "l_sho", "r_sho", "l_elb", "r_elb", "l_hand", "r_hand", "l_hip", "r_hip", "l_knee", "r_knee", "l_ankle", "r_ankle"):
            J[k].rotation_euler = P.get(k, (0, 0, 0))
    def world(self, joint): return self.J[joint].matrix_world.translation.copy()
    def lowest(self):
        """Lowest world z of the body ellipsoids (support function of a transformed unit sphere in -z)."""
        bpy.context.view_layer.update(); lo = 1e9
        for ob in self.parts:
            M = ob.matrix_world; lo = min(lo, M.translation.z - math.sqrt(M[2][0] ** 2 + M[2][1] ** 2 + M[2][2] ** 2))
        return lo
    def ground_snap(self, ground_z):
        """Shift the root so the lowest body point (sole, seat) rests on ground_z: no buried shins, no floating feet."""
        d = ground_z - self.lowest(); self.J["root"].location.z += d; bpy.context.view_layer.update(); return d

def blend_pose(a, b, t):
    keys = set(a) | set(b); z = (0, 0, 0)
    return {k: tuple(lerp(x, y, t) for x, y in zip(a.get(k, z), b.get(k, z))) for k in keys}
def add_pose(a, b, w=1.0):
    keys = set(a) | set(b); z = (0, 0, 0)
    return {k: tuple(x + w * y for x, y in zip(a.get(k, z), b.get(k, z))) for k in keys}
# limb convention: rotation about X, negative = forward (figure faces -Y); about Y spreads a limb outward with l: -, r: + (arms AND legs;
# the left side sits at +x, so a positive Y on the left hip swings that leg inward and the legs cross -- QA caught that in v1)
STAND = {"l_sho": (0.05, -0.12, 0), "r_sho": (0.05, 0.12, 0), "l_elb": (-0.15, 0, 0), "r_elb": (-0.15, 0, 0), "l_hip": (0, -0.05, 0), "r_hip": (0, 0.05, 0)}
JOLT = {"spine": (0.22, 0, 0), "neck": (0.25, 0, 0), "l_sho": (0, -1.35, 0), "r_sho": (0, 1.35, 0), "l_elb": (0, 0, 0), "r_elb": (0, 0, 0),
        "l_hip": (0, -0.2, 0), "r_hip": (0, 0.2, 0), "l_knee": (0, 0, 0), "r_knee": (0, 0, 0)}
SLUMP = {"spine": (-0.12, 0, 0), "neck": (-0.2, 0, 0), "l_sho": (0.1, -0.05, 0), "r_sho": (0.1, 0.05, 0), "l_elb": (-0.1, 0, 0), "r_elb": (-0.1, 0, 0),
         "l_hip": (0, -0.06, 0), "r_hip": (0, 0.06, 0), "l_knee": (0.05, 0, 0), "r_knee": (0.05, 0, 0)}
# knees-up sit on the ground: thighs forward and up, shins forward-down, feet flat (pelvis ~0.17 m; ground_snap settles it exactly)
SIT = {"spine": (0.30, 0, 0), "neck": (-0.25, 0, 0), "l_hip": (-2.0, -0.18, 0), "r_hip": (-2.0, 0.18, 0), "l_knee": (1.25, 0, 0), "r_knee": (1.25, 0, 0),
       "l_ankle": (0.75, 0, 0), "r_ankle": (0.75, 0, 0),
       "l_sho": (-0.55, -0.30, 0), "r_sho": (-0.55, 0.30, 0), "l_elb": (-0.7, 0, 0), "r_elb": (-0.7, 0, 0)}
RAISE = {"spine": (0.08, 0, 0), "neck": (0.35, 0, 0), "r_sho": (-3.0, 0.15, 0), "r_elb": (-0.05, 0, 0), "l_sho": (0.15, -0.5, 0), "l_elb": (-1.6, 0, 0.0),
         "l_hip": (0, -0.08, 0), "r_hip": (0, 0.08, 0)}
# hopping on the left foot, right foot pulled up behind, arms flapping (Roy after strike one)
HOP = {"spine": (0.1, 0, 0), "neck": (-0.25, 0, 0), "r_hip": (-0.35, 0.1, 0), "r_knee": (1.7, 0, 0), "l_hip": (0, -0.03, 0),
       "l_sho": (0, -1.0, 0), "r_sho": (0, 1.0, 0), "l_elb": (-0.6, 0, 0), "r_elb": (-0.6, 0, 0)}
SHRUG = {"spine": (0.0, 0, 0), "neck": (0.1, 0, 0.0), "r_sho": (-2.7, 0.3, 0), "r_elb": (-0.3, 0, 0), "l_sho": (-0.3, -0.75, 0), "l_elb": (-1.5, 0, 0)}

# ----------------------------------------------------------------------------- shared effects
class Puffs:
    """Pool of smoke/steam spheres. Events: (t0, origin, n, spread, rise, size, life, seed)."""
    def __init__(self, name, mat, n=36):
        self.pool = [ellipsoid(f"{name}{i}", (0, 0, -100), (0.1, 0.1, 0.1), mat) for i in range(n)]
        for p in self.pool: p.visible_shadow = False
        self.parts = []
    def add(self, t0, origin, n=8, spread=0.12, rise=0.6, size=0.12, life=1.4, seed=1, dur=0.15, alpha=0.8):
        r = random.Random(seed)
        for i in range(n):
            d = Vector((r.gauss(0, 1), r.gauss(0, 1), abs(r.gauss(0, 1)))).normalized()
            o = (lambda f=origin, off=d * spread * 0.5: f() + off) if callable(origin) else Vector(origin) + d * spread * 0.5   # callable origin: follows a moving emitter
            self.parts.append((t0 + r.uniform(0, dur), o, d * spread + Vector((0, 0, rise * r.uniform(0.6, 1.2))), size * r.uniform(0.7, 1.3), life * r.uniform(0.7, 1.2), alpha))
    def update(self, t, origin_fn=None):
        live = [(t - t0, p) for (t0, *p) in self.parts if 0 <= t - t0 < p[3]]
        for i, ob in enumerate(self.pool):
            if i < len(live):
                k, (o, v, s, life, a) = live[i]; u = k / life
                if callable(o): o = o()
                ob.location = o + v * (1 - math.exp(-k * 1.8)) / 1.8 + Vector((0, 0, 0.25 * k * k)); sc = s * (0.4 + 1.6 * u ** 0.5)
                ob.scale = (sc, sc, sc); set_alpha(ob, a * smoothstep(0, 0.08, u) * (1 - u) ** 1.5)
            else: ob.location = (0, 0, -100); set_alpha(ob, 0)

def flame_mesh(name, mat, parent=None, h=0.22, r=0.07):
    bm = bmesh.new(); prof = [(r * math.sin(math.pi * min(1, (z / h) * 1.4)) ** 0.7 * (1 - z / h) ** 0.6 + 1e-3, z) for z in [h * i / 14 for i in range(15)]]
    rings = []
    for (pr, z) in prof:
        rings.append([bm.verts.new((pr * math.cos(a), pr * math.sin(a), z)) for a in [2 * math.pi * j / 16 for j in range(16)]])
    for a, b in zip(rings[:-1], rings[1:]):
        for j in range(16): bm.faces.new((a[j], a[(j + 1) % 16], b[(j + 1) % 16], b[j]))
    ob = link_obj(name, mesh_from_bm(name, bm, mat), parent); ob.visible_shadow = False; return ob

def rain(name, center, size, n, length, seed, mat):
    """Two stacked blocks of thin streaks; the object slides down and wraps every block height."""
    r = random.Random(seed); bm = bmesh.new()
    for i in range(n):
        x, y, z = r.uniform(-size[0], size[0]), r.uniform(-size[1], size[1]), r.uniform(0, size[2])
        w = 0.0025; v = [bm.verts.new(p) for p in ((x - w, y, z), (x + w, y, z), (x + w + 0.03, y, z + length), (x - w + 0.03, y, z + length))]
        bm.faces.new(v)
    me = mesh_from_bm(name, bm, mat, False); obs = []
    for k in range(2):
        ob = link_obj(f"{name}{k}", me); ob.visible_shadow = False; obs.append(ob)
    return {"obs": obs, "center": Vector(center), "h": size[2]}
def rain_update(R, t, speed=9.0):
    off = (t * speed) % R["h"]
    for k, ob in enumerate(R["obs"]): ob.location = R["center"] + Vector((0.0, 0, -off + k * R["h"] - R["h"] * 0.5))

def storm_world(zen=(0.05, 0.06, 0.08), hor=(0.30, 0.34, 0.40), strength=1.0, clouds=0.7):
    """Sky by view direction: dark zenith, pale horizon, big noise cloud masses; 'flash' value brightens it."""
    w = bpy.data.worlds.new("sky"); bpy.context.scene.world = w; w.use_nodes = True; nt = w.node_tree; n = nt.nodes; L = nt.links
    for x in list(n): n.remove(x)
    out = n.new("ShaderNodeOutputWorld"); bg = n.new("ShaderNodeBackground"); tc = n.new("ShaderNodeTexCoord"); sep = n.new("ShaderNodeSeparateXYZ")
    L.new(tc.outputs["Generated"], sep.inputs[0])
    mr = n.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = -0.05; mr.inputs["From Max"].default_value = 0.55; L.new(sep.outputs["Z"], mr.inputs["Value"])
    gr = n.new("ShaderNodeMix"); gr.data_type = "RGBA"; gr.inputs[6].default_value = (*hor, 1); gr.inputs[7].default_value = (*zen, 1); L.new(mr.outputs[0], gr.inputs[0])
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 2.6; nz.inputs["Detail"].default_value = 8; nz.inputs["Roughness"].default_value = 0.6
    L.new(tc.outputs["Generated"], nz.inputs["Vector"])
    cr = n.new("ShaderNodeMapRange"); cr.inputs["From Min"].default_value = 0.38; cr.inputs["From Max"].default_value = 0.65; cr.inputs["To Min"].default_value = 1.0; cr.inputs["To Max"].default_value = 1.0 - clouds
    L.new(nz.outputs["Fac"], cr.inputs["Value"])
    mul = n.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"; mul.inputs[0].default_value = 1.0; L.new(gr.outputs[2], mul.inputs[6])
    cc = n.new("ShaderNodeCombineColor"); [L.new(cr.outputs[0], cc.inputs[i]) for i in range(3)]; L.new(cc.outputs[0], mul.inputs[7])
    fl = n.new("ShaderNodeValue"); fl.name = "flash"; fl.outputs[0].default_value = 0.0
    st = n.new("ShaderNodeMath"); st.operation = "MULTIPLY_ADD"; st.inputs[1].default_value = 2.0; st.inputs[2].default_value = strength; L.new(fl.outputs[0], st.inputs[0])
    L.new(mul.outputs[2], bg.inputs["Color"]); L.new(st.outputs[0], bg.inputs["Strength"]); L.new(bg.outputs[0], out.inputs[0])
    return fl

def light(name, typ, loc, energy, color, size=1.0, rot=(0, 0, 0)):
    ld = bpy.data.lights.new(name, typ); ld.energy = energy; ld.color = color
    if typ == "AREA": ld.size = size
    if typ == "POINT": ld.shadow_soft_size = size
    if typ == "SUN": ld.angle = size
    ob = link_obj(name, ld); ob.location = loc; ob.rotation_euler = rot; return ob
def camera(lens=35):
    cd = bpy.data.cameras.new("cam"); cam = link_obj("cam", cd); bpy.context.scene.camera = cam
    tgt = empty("cam_target"); con = cam.constraints.new("TRACK_TO"); con.target = tgt; con.track_axis = "TRACK_NEGATIVE_Z"; con.up_axis = "UP_Y"
    cd.clip_end = 30000; cd.clip_start = 0.05; cd.lens = lens; return cam, tgt
def dof(cam, focus_ob, fstop):
    cam.data.dof.use_dof = True; cam.data.dof.focus_object = focus_ob; cam.data.dof.aperture_fstop = fstop

def pine(name, loc, h, mat_trunk, mat_needle, r=None):
    r = r or h * 0.28
    cylinder(name + "t", 0.08 * h / 6, 0.05 * h / 6, h * 0.3, (loc[0], loc[1], loc[2] + h * 0.15), mat_trunk, segs=6)
    for k in range(4):
        z0 = h * (0.22 + 0.19 * k); rr = r * (1 - 0.22 * k)
        cylinder(f"{name}c{k}", rr, 0.0, h * 0.36, (loc[0], loc[1], loc[2] + z0 + h * 0.18), mat_needle, segs=9)
def round_tree(name, loc, h, mat_trunk, mat_leaf, rng):
    cylinder(name + "t", 0.18 * h / 8, 0.12 * h / 8, h * 0.5, (loc[0], loc[1], loc[2] + h * 0.25), mat_trunk, segs=7)
    for k in range(5):
        o = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-0.5, 0.6))) * h * 0.16
        s = h * rng.uniform(0.2, 0.3); ob = ellipsoid(f"{name}l{k}", (loc[0] + o.x, loc[1] + o.y, loc[2] + h * 0.68 + o.z), (s, s, s * 0.85), mat_leaf)

def leaf_material(name, c0, c1, scale=6.0):
    m, nt, out = new_mat(name); n = nt.nodes; L = nt.links
    p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Roughness"].default_value = 0.8
    tc = n.new("ShaderNodeTexCoord"); vz = n.new("ShaderNodeTexVoronoi"); vz.inputs["Scale"].default_value = scale; L.new(tc.outputs["Object"], vz.inputs["Vector"])
    ramp = n.new("ShaderNodeMix"); ramp.data_type = "RGBA"; ramp.inputs[6].default_value = (*c0, 1); ramp.inputs[7].default_value = (*c1, 1); L.new(vz.outputs["Distance"], ramp.inputs[0])
    L.new(ramp.outputs[2], p.inputs["Base Color"])
    bump = n.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.6; L.new(vz.outputs["Distance"], bump.inputs["Height"]); L.new(bump.outputs[0], p.inputs["Normal"])
    L.new(p.outputs[0], out.inputs[0]); return m
def ground_material(name, c0, c1, scale=0.4, rough=0.7, ring=None, wet=0.0):
    """Noise-mottled ground. ring=(center xy, color): adds an emissive expanding ring driven by 'ring_r' / 'ring_a' values."""
    m, nt, out = new_mat(name); n = nt.nodes; L = nt.links
    p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Roughness"].default_value = rough
    tc = n.new("ShaderNodeTexCoord"); nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = scale; nz.inputs["Detail"].default_value = 8
    L.new(tc.outputs["Object"], nz.inputs["Vector"])
    mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.inputs[6].default_value = (*c0, 1); mx.inputs[7].default_value = (*c1, 1); L.new(nz.outputs["Fac"], mx.inputs[0])
    L.new(mx.outputs[2], p.inputs["Base Color"])
    nz2 = n.new("ShaderNodeTexNoise"); nz2.inputs["Scale"].default_value = scale * 40; L.new(tc.outputs["Object"], nz2.inputs["Vector"])
    bump = n.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.35; L.new(nz2.outputs["Fac"], bump.inputs["Height"]); L.new(bump.outputs[0], p.inputs["Normal"])
    if ring:
        (cx, cy), col = ring
        sep = n.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Object"], sep.inputs[0])
        dx = n.new("ShaderNodeMath"); dx.operation = "SUBTRACT"; dx.inputs[1].default_value = cx; L.new(sep.outputs["X"], dx.inputs[0])
        dy = n.new("ShaderNodeMath"); dy.operation = "SUBTRACT"; dy.inputs[1].default_value = cy; L.new(sep.outputs["Y"], dy.inputs[0])
        cxy = n.new("ShaderNodeCombineXYZ"); L.new(dx.outputs[0], cxy.inputs[0]); L.new(dy.outputs[0], cxy.inputs[1])
        ln = n.new("ShaderNodeVectorMath"); ln.operation = "LENGTH"; L.new(cxy.outputs[0], ln.inputs[0])
        rr = n.new("ShaderNodeValue"); rr.name = "ring_r"; ra = n.new("ShaderNodeValue"); ra.name = "ring_a"
        # branchy streaks: distort the distance with noise so the ring is a crackle of filaments, not a clean circle
        nz3 = n.new("ShaderNodeTexNoise"); nz3.inputs["Scale"].default_value = 1.2; nz3.inputs["Detail"].default_value = 6; L.new(tc.outputs["Object"], nz3.inputs["Vector"])
        dd = n.new("ShaderNodeMath"); dd.operation = "MULTIPLY_ADD"; dd.inputs[1].default_value = 1.6; L.new(nz3.outputs["Fac"], dd.inputs[0]); L.new(ln.outputs["Value"], dd.inputs[2])
        d2 = n.new("ShaderNodeMath"); d2.operation = "SUBTRACT"; L.new(dd.outputs[0], d2.inputs[0]); L.new(rr.outputs[0], d2.inputs[1])
        d2b = n.new("ShaderNodeMath"); d2b.operation = "SUBTRACT"; d2b.inputs[1].default_value = 0.8; L.new(d2.outputs[0], d2b.inputs[0])
        g = n.new("ShaderNodeMath"); g.operation = "MULTIPLY"; L.new(d2b.outputs[0], g.inputs[0]); L.new(d2b.outputs[0], g.inputs[1])
        g2 = n.new("ShaderNodeMath"); g2.operation = "MULTIPLY"; g2.inputs[1].default_value = -1.2; L.new(g.outputs[0], g2.inputs[0])
        ex = n.new("ShaderNodeMath"); ex.operation = "EXPONENT"; L.new(g2.outputs[0], ex.inputs[0])
        # inside the ring: faint lingering glow
        ins = n.new("ShaderNodeMath"); ins.operation = "LESS_THAN"; L.new(dd.outputs[0], ins.inputs[0]); L.new(rr.outputs[0], ins.inputs[1])
        insw = n.new("ShaderNodeMath"); insw.operation = "MULTIPLY_ADD"; insw.inputs[1].default_value = 0.015; L.new(ins.outputs[0], insw.inputs[0]); L.new(ex.outputs[0], insw.inputs[2])
        vr = n.new("ShaderNodeTexVoronoi"); vr.feature = "DISTANCE_TO_EDGE"; vr.inputs["Scale"].default_value = 2.2
        warp = n.new("ShaderNodeVectorMath"); warp.operation = "MULTIPLY_ADD"; warp.inputs[1].default_value = (0.9, 0.9, 0.0)   # crooked, crackly filaments instead of plates
        L.new(nz3.outputs["Color"], warp.inputs[0]); L.new(tc.outputs["Object"], warp.inputs[2]); L.new(warp.outputs[0], vr.inputs["Vector"])
        vm = n.new("ShaderNodeMapRange"); vm.inputs["From Min"].default_value = 0.0; vm.inputs["From Max"].default_value = 0.035; vm.inputs["To Min"].default_value = 1.0; vm.inputs["To Max"].default_value = 0.0
        L.new(vr.outputs["Distance"], vm.inputs["Value"])
        e1 = n.new("ShaderNodeMath"); e1.operation = "MULTIPLY"; L.new(insw.outputs[0], e1.inputs[0]); L.new(vm.outputs[0], e1.inputs[1])
        e2 = n.new("ShaderNodeMath"); e2.operation = "MULTIPLY"; L.new(e1.outputs[0], e2.inputs[0]); L.new(ra.outputs[0], e2.inputs[1])
        p.inputs["Emission Color"].default_value = (*col, 1); L.new(e2.outputs[0], p.inputs["Emission Strength"])
    L.new(p.outputs[0], out.inputs[0]); return m

# ----------------------------------------------------------------------------- shot H: Roy on the ridge
def blue_ridge(S, rng, near_trees=True, fz=None, tree_box=((-30, 30), (4, 40)), keep_clear=None):
    """Hazy Blue Ridge layers (far ones lighter, emission matched to the horizon) + pines on the near slopes."""
    layers = [(380, 70, (0.09, 0.13, 0.10), 0.0), (800, 140, (0.13, 0.18, 0.20), 0.15), (1600, 230, (0.20, 0.26, 0.31), 0.35), (3000, 330, (0.28, 0.33, 0.40), 0.6), (5500, 420, (0.34, 0.38, 0.45), 0.8)]
    for i, (dist, hgt, col, haze) in enumerate(layers):
        bm = bmesh.new(); nx = 160; w = dist * 3.2; rows = []
        for j in range(3):
            rows.append([bm.verts.new((-w / 2 + w * k / nx, dist + j * dist * 0.2, 0)) for k in range(nx + 1)])
        for k, v in enumerate(rows[0]):
            x = v.co.x; h = hgt * (0.55 + 0.45 * noise2(x, i * 50, dist * 0.6, i)) + hgt * 0.18 * noise2(x, 7, dist * 0.12, i + 3)
            rows[0][k].co.z = h - 120 - i * 25; rows[1][k].co.z = h * 0.9 - 120 - i * 25; rows[2][k].co.z = -400
        for a, b in zip(rows[:-1], rows[1:]):
            for k in range(nx): bm.faces.new((a[k], a[k + 1], b[k + 1], b[k]))
        mat = principled(f"ridge{i}", col, 0.9, emit=col, emit_s=haze * 1.1)
        ob = link_obj(f"ridge{i}", mesh_from_bm(f"ridge{i}", bm, mat)); ob.visible_shadow = False
    if near_trees:
        bark = principled("bark", (0.10, 0.07, 0.05), 0.9); ndl = leaf_material("needles", (0.03, 0.07, 0.04), (0.07, 0.13, 0.06), 9)
        for i in range(34):
            x, y = rng.uniform(*tree_box[0]), rng.uniform(*tree_box[1])
            if keep_clear and keep_clear(x, y): continue
            pine(f"pine{i}", (x, y, fz(x, y) - 0.2), rng.uniform(4, 9), bark, ndl)

ROY_HAIR = (0.10, 0.06, 0.035)   # dark enough to read as hair against the skin (v1 looked bald)
def make_roy(sheath):
    return Figure("roy", shirt=(0.58, 0.48, 0.30), pants=(0.16, 0.20, 0.13), shoes=(0.10, 0.07, 0.05), hair=ROY_HAIR, sheath_mat=sheath, hat="ranger")
def hair_flames(S, roy, scale=2.4):
    fmat = faded_emission("flame", (1.0, 0.45, 0.10), 30.0, noise_scale=14.0); S["fmat"] = fmat
    S["flames"] = [flame_mesh(f"hairflame{i}", fmat, roy.J["head"], h=(0.20 + 0.06 * i) * scale, r=0.06 * scale * 0.8) for i in range(3)]
    for i, f in enumerate(S["flames"]): f.location = ((i - 1) * 0.08, 0.03, 0.14)
    S["glow"] = light("flameglow", "POINT", (0, 0, 2.2), 0.0, (1.0, 0.5, 0.15), size=0.2)
def update_flames(S, roy, t, fl):
    for i, f in enumerate(S["flames"]):
        s = 1.0 + 0.25 * n1(t * 9, i); f.scale = (s, s, s * (1 + 0.3 * n1(t * 13, i + 5))); set_alpha(f, fl)
    S["fmat"].node_tree.nodes["flow"].outputs[0].default_value = t * 4.0
    S["glow"].location = roy.world("head") + Vector((0, -0.4, 0.4)); S["glow"].data.energy = 90 * fl

def build_H():
    S = {}; S["flash"] = storm_world((0.06, 0.07, 0.10), (0.42, 0.46, 0.52), 1.0, 0.65); rng = random.Random(11)
    def fz(x, y):
        d = math.hypot(x, y * 0.7); base = -0.0 - 0.05 * d - 0.004 * d * d * smoothstep(8, 40, d)
        return base + 0.6 * noise2(x, y, 6, 1) + 0.15 * noise2(x, y, 1.5, 2)
    grass = ground_material("summit", (0.10, 0.13, 0.05), (0.24, 0.26, 0.10), 0.35, 0.85)
    S["ground"] = displaced_grid("summit", 90, 140, fz, grass)
    rock = leaf_material("rock", (0.07, 0.07, 0.075), (0.16, 0.155, 0.15), 3.0)
    for i in range(26):   # granite boulders + the outcrop Roy stands on
        x, y = rng.uniform(-14, 14), rng.uniform(-6, 18)
        if i == 0: x, y = 0, 0.3
        s = rng.uniform(0.4, 1.8) if i else 1.2
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1)
        for v in bm.verts: v.co *= 1 + 0.25 * mnoise.noise(v.co * 1.7 + Vector((i, 0, 0)))
        ob = link_obj(f"rock{i}", mesh_from_bm(f"rock{i}", bm, rock, False)); ob.scale = (s * 1.3, s, s * 0.55); ob.location = (x, y, fz(x, y) - s * 0.25)
        ob.rotation_euler = (0, 0, rng.uniform(0, 6))
        if i == 0: S["stand_z"] = fz(0, 0.3) - s * 0.25 + s * 0.55 * 0.92
    blue_ridge(S, rng, True, fz, keep_clear=lambda x, y: abs(x) < 3.5 and y < 14)
    # fire lookout tower behind Roy (1942: he ran out of a new tower with no lightning rod)
    wood = principled("timber", (0.30, 0.20, 0.12), 0.8); roof = principled("roof", (0.22, 0.10, 0.08), 0.6)
    glass = principled("window", (0.6, 0.7, 0.8), 0.05, emit=(1.0, 0.75, 0.45), emit_s=0.6)
    tx, ty = 4.2, 10.0; tz = fz(tx, ty) - 0.2; H_ = 9.0; b0, b1 = 2.4, 1.6
    for sx in (-1, 1):
        for sy in (-1, 1):
            seg_between(f"leg{sx}{sy}", (tx + sx * b0, ty + sy * b0, tz - 1), (tx + sx * b1, ty + sy * b1, tz + H_), 0.12, wood, 6)
    for lv in range(3):
        z0, z1 = tz + lv * 3.0, tz + (lv + 1) * 3.0; f0, f1 = lerp(b0, b1, lv / 3), lerp(b0, b1, (lv + 1) / 3)
        for (ax, ay), (bx, by) in (((-1, -1), (1, -1)), ((1, -1), (1, 1)), ((1, 1), (-1, 1)), ((-1, 1), (-1, -1))):
            seg_between(f"x{lv}{ax}{ay}a", (tx + ax * f0, ty + ay * f0, z0), (tx + bx * f1, ty + by * f1, z1), 0.05, wood, 5)
            seg_between(f"x{lv}{ax}{ay}b", (tx + bx * f0, ty + by * f0, z0), (tx + ax * f1, ty + ay * f1, z1), 0.05, wood, 5)
            seg_between(f"h{lv}{ax}{ay}", (tx + ax * f1, ty + ay * f1, z1), (tx + bx * f1, ty + by * f1, z1), 0.06, wood, 5)
    cz = tz + H_
    box("cabfloor", (4.0, 4.0, 0.2), (tx, ty, cz), wood); box("cabwall", (3.6, 3.6, 0.9), (tx, ty, cz + 0.55), wood)
    box("cabglass", (3.5, 3.5, 1.0), (tx, ty, cz + 1.5), glass)
    for sx in (-1, 1):
        for sy in (-1, 1): box(f"post{sx}{sy}", (0.12, 0.12, 1.1), (tx + sx * 1.75, ty + sy * 1.75, cz + 1.5), wood)
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=4, radius1=3.3, radius2=0.05, depth=1.3)
    ob = link_obj("cabroof", mesh_from_bm("cabroof", bm, roof, False)); ob.location = (tx, ty, cz + 2.65); ob.rotation_euler = (0, 0, math.pi / 4)
    # Roy
    sheath = faded_emission("sheath", (0.55, 0.72, 1.0), 4.0, noise_scale=6.0, streak=True); S["sheath"] = sheath
    S["roy"] = roy = make_roy(sheath)
    hair_flames(S, roy)
    S["smoke"] = Puffs("smoke", smoke_material("smoke"), 60)
    S["steam"] = Puffs("steamH", smoke_material("steamHm", (0.82, 0.84, 0.87)), 24)
    char = principled("char", (0.012, 0.010, 0.010), 0.9)
    S["hole"] = ellipsoid("shoehole", (0.0, -0.10, 0.005), (0.05, 0.055, 0.02), char, roy.J["r_shoe"])
    S["ember"] = ellipsoid("shoeember", (0.0, -0.10, 0.0), (0.06, 0.066, 0.018), emissive("emberm", (1.0, 0.35, 0.08), 6.0), roy.J["r_shoe"])   # glowing rim
    # the 1942 burn: a scorched strip down the outside of the right trouser leg
    S["burn"] = [ellipsoid(f"burn{k}", (-0.06, -0.02, z), (0.035, 0.05, h), char, roy.J[j]) for k, (j, z, h) in enumerate((("r_hip", -0.22, 0.22), ("r_knee", -0.21, 0.21)))]
    # water can (hair section): body, spout, handle, held in the right hand; a stream + steam when he pours
    tin = principled("tin", (0.55, 0.60, 0.62), 0.35, 0.9)
    S["can"] = can = empty("can", (0, 0, -0.06), roy.J["r_hand"])
    cylinder("canbody", 0.09, 0.09, 0.2, (0, 0, -0.08), tin, segs=20, parent=can)
    seg_between("canspout", (0, -0.08, -0.12), (0, -0.25, -0.02), 0.015, tin).parent = can
    S["stream"] = curve_obj("stream", [(0, 0, 0)] * 6, principled("waterm", (0.6, 0.75, 0.9), 0.05, emit=(0.6, 0.8, 1.0), emit_s=1.5), 0.025)
    S["rain"] = rain("rain", (0, 2.0, 0), (8, 5, 12), 2600, 0.5, 3, faded_emission("rainm", (0.8, 0.85, 0.95), 0.18))
    for ob in S["rain"]["obs"]: set_alpha(ob, 1.0)
    bm_ = bolt_material(); S["bolts"] = []
    for i in range(len(H_STRIKES)):
        r = random.Random(100 + i); top = Vector((r.uniform(-120, 120), r.uniform(150, 400), 900))
        S["bolts"].append(Bolt(f"bolt{i}", top, (0, 0.3, S["stand_z"] + 1.95), 40 + i, bm_, radius=0.06, nbranch=8, blen=(60, 240), converge=14))
    # the strike-one current running down the leg to the shoe (visible for a few frames, like the leg path in v1's shot R)
    S["legcur"] = curve_obj("legcurH", [(0, 0, 0)] * 6, faded_emission("legcurHm", (0.65, 0.8, 1.0), 14.0), 0.05)
    S["key"] = light("key", "SUN", (0, 0, 100), 1.6, (0.75, 0.82, 1.0), size=0.12, rot=(math.radians(50), 0, math.radians(30)))
    S["fill"] = light("fillH", "AREA", (-3, -7, 3), 220, (0.85, 0.9, 1.0), size=6, rot=(math.radians(75), 0, math.radians(-25)))
    S["strike"] = light("strikeH", "POINT", (2, -3, 12), 0.0, (0.8, 0.88, 1.0), size=2)
    S["cam"], S["tgt"] = camera(32); S["focus"] = empty("focusH"); dof(S["cam"], S["focus"], 4.0)
    S["fz"] = fz
    return S

def strike_env(t, times, attack=0.02):
    """Brightness of the most recent strike + 2 quick re-strike flickers."""
    v = 0.0; idx = -1
    for i, ts in enumerate(times):
        p = pulse(t, ts, attack, 0.05, 0.12) + 0.6 * pulse(t, ts + 0.13, 0.01, 0.03, 0.08) + 0.4 * pulse(t, ts + 0.24, 0.01, 0.02, 0.07)
        if p > v: v, idx = p, i
    return min(v, 1.2), idx

def strike_pose(P, t, times, dur=1.2):
    """Jolt for ~0.35 s after each strike (with an electric shiver), then a slump."""
    for i, ts in enumerate(times):
        k = t - ts
        if -0.02 < k < dur:
            j = smoothstep(-0.02, 0.03, k) * (1 - smoothstep(0.32, 0.6, k))
            P = blend_pose(P, JOLT, j)
            P = blend_pose(P, SLUMP, smoothstep(0.45, 0.65, k) * (1 - smoothstep(0.9, 1.2, k)) * 0.8)
            sh = 0.12 * j * n1(t * 60, i); P = add_pose(P, {"l_sho": (0, sh, 0), "r_sho": (0, -sh, 0), "neck": (sh, 0, 0)})
    return P

def update_H(S, t):
    roy = S["roy"]; inten, idx = strike_env(t, H_STRIKES); hair_sec = t >= H_HAIR0
    for i, b in enumerate(S["bolts"]):
        ts = H_STRIKES[i]; grow = smoothstep(ts - 0.07, ts, t) if i else 1.0
        glow = (0.12 * grow if t < ts else pulse(t, ts, 0.02, 0.05, 0.12) + 0.6 * pulse(t, ts + 0.13, 0.01, 0.03, 0.08) + 0.4 * pulse(t, ts + 0.24, 0.01, 0.02, 0.07)) if t > ts - 0.07 else 0.0
        if i == 0 and t < 0.02: glow = 1.0
        b.set(grow, min(glow, 1.0) if t < ts + 0.6 else 0.0, 1.0 + 0.2 * min(glow, 1))
    S["flash"].outputs[0].default_value = 0.35 * inten
    S["strike"].data.energy = 1.0e4 * inten
    P = strike_pose(dict(STAND), t, H_STRIKES)
    lift = 0.0
    if not hair_sec:
        # strike one: shake it off, look down at the smoking shoe, then hop on the other foot
        P = add_pose(P, {"neck": (0.0, 0, 0.25 * math.sin((t - 1.0) * 14) * smoothstep(0.9, 1.0, t) * (1 - smoothstep(1.6, 2.0, t)))})
        P = blend_pose(P, {**STAND, "neck": (-0.55, 0, 0.1), "spine": (-0.15, 0, 0)}, smoothstep(2.6, 3.2, t) * (1 - smoothstep(4.4, 4.8, t)))
        hk = smoothstep(4.6, 4.9, t) * (1 - smoothstep(H_SHOE_CU - 0.5, H_SHOE_CU - 0.2, t))
        P = blend_pose(P, HOP, hk)
        # stop hopping and lift the foot forward, toe up, to look at the hole
        P = blend_pose(P, {**STAND, "r_hip": (-1.15, 0.15, 0), "r_knee": (1.0, 0, 0), "r_ankle": (0.15, 0, 0), "neck": (-0.6, 0, 0), "spine": (-0.2, 0, 0),
                           "l_sho": (0.1, -0.45, 0), "r_sho": (0.1, 0.45, 0)}, smoothstep(H_SHOE_CU - 0.5, H_SHOE_CU - 0.1, t))
        P = add_pose(P, {"l_sho": (0, 0.35 * math.sin(t * 14), 0), "r_sho": (0, -0.35 * math.sin(t * 14), 0)}, hk)
        lift = hk * 0.16 * abs(math.sin(t * 7.0))
    else:
        # hair section: strikes 3-6 with the hat gone, then he lifts the can and pours it over his burning head
        kc = smoothstep(H_POUR0 - 0.45, H_POUR0, t)
        P = blend_pose(P, {**STAND, "r_sho": (-2.85, 0.35, 0), "r_elb": (-0.55, 0, 0), "r_hand": (0.0, 0, 0), "neck": (-0.2, 0, 0)}, kc)
    roy.pose(P, (0, 0.3, S["stand_z"] + lift), 0.0)
    # feet on the rock (the hop lifts on purpose)
    fz_rock = S["stand_z"]
    if lift == 0.0: roy.ground_snap(fz_rock)
    else: roy.J["root"].location.z += (fz_rock - (roy.lowest() - lift))
    bpy.context.view_layer.update()
    roy.set_sheath(min(1.0, inten * 1.1))
    S["sheath"].node_tree.nodes["flow"].outputs[0].default_value = t * 9.0
    # can: tilts to pour; stream from the spout down onto the head
    S["can"].hide_render = not hair_sec
    for ch in S["can"].children: ch.hide_render = not hair_sec
    tilt = smoothstep(H_POUR0, H_POUR0 + 0.3, t); S["can"].rotation_euler = (-1.9 * tilt, 0, 0)
    pouring = hair_sec and H_POUR0 + 0.2 < t < H_POUR1
    if pouring:
        bpy.context.view_layer.update(); sp = S["can"].matrix_world @ Vector((0, -0.25, -0.02)); hd = roy.world("head") + Vector((0, 0, 0.17))
        pts = [sp.lerp(hd, k / 5) + Vector((0, 0, 0.12 * math.sin(math.pi * k / 5))) for k in range(6)]
        for p, q in zip(S["stream"].data.splines[0].points, pts): p.co = (q.x, q.y, q.z, 1.0)
    S["stream"].hide_render = not pouring
    # hat: pops on strike one and lands back; flies off for good at the first hair strike
    hat = roy.J["hat"]
    if not hair_sec:
        k = t; up = max(0, 0.55 * math.sin(math.pi * min(1, k / 0.55))) if k < 0.55 else 0
        hat.location = (0, 0, 0.11 + up); hat.rotation_euler = (0.4 * up, 0, 2.5 * up)
    else: hat.location = (0, 0, -50)
    for b in roy.brows: b.hide_render = hair_sec   # strike two (the truck) took them
    roy.hair.scale = (0.17, 0.16, 0.15) if not hair_sec else (0.19, 0.18, 0.19)   # frizz
    fl = 0.0
    if hair_sec: fl = smoothstep(H_STRIKES[1] + 0.05, H_STRIKES[1] + 0.15, t) * (1 - smoothstep(H_POUR0 + 0.35, H_POUR0 + 0.55, t))
    update_flames(S, roy, t, fl * (1 + 0.25 * sum(t > ts for ts in H_STRIKES[2:])))
    S["hole"].hide_render = t < 0.05; S["ember"].hide_render = t < 0.05 or t > H_HAIR0
    for b_ in S["burn"]: b_.hide_render = t < 0.08
    # strike-one current: head -> right hip -> knee -> shoe, drawn in the first 0.25 s
    js = [roy.world("head"), roy.world("r_sho"), roy.world("r_hip"), roy.world("r_knee"), roy.world("r_ankle"), roy.world("r_ankle") + Vector((0, -0.08, -0.08))]
    for p, q in zip(S["legcur"].data.splines[0].points, js): p.co = (q.x - 0.12, q.y - 0.02, q.z, 1.0)
    S["legcur"].data.bevel_factor_end = smoothstep(0.0, 0.12, t); set_alpha(S["legcur"], 1.0 - smoothstep(0.18, 0.35, t))
    rain_update(S["rain"], t)
    if not S["smoke"].parts:
        sm = S["smoke"]; z0 = S["stand_z"]
        for i, ts in enumerate(H_STRIKES): sm.add(ts + 0.08, (0, 0.3, z0 + 1.3), 9, 0.35, 0.8, 0.12, 1.6, 10 + i, 0.25, 0.5)
        for k, ts in enumerate((0.05, 1.2, 2.4, 3.6, 4.8, 6.0, 7.2, 8.4, 9.4)):   # the shoe keeps smoking
            sm.add(ts, (-0.1, 0.18, z0 + 0.05), 5, 0.12, 0.35, 0.06, 1.4, 30 + k, 0.4, 0.7)
        for k in range(6): sm.add(H_STRIKES[1] + 0.2 + k * 0.45, (0, 0.33, z0 + 2.0), 5, 0.1, 0.9, 0.08, 1.4, 60 + k, 0.2, 0.6)   # burning hair
        S["steam"].add(H_POUR0 + 0.4, (0, 0.33, z0 + 2.0), 14, 0.25, 1.2, 0.12, 1.8, 90, 0.5, 0.75)
    S["smoke"].update(t); S["steam"].update(t)
    shake = Vector((n1(t * 31, 1), n1(t * 29, 2), n1(t * 27, 3))) * 0.06 * inten
    z0 = S["stand_z"]
    if not hair_sec:
        # wide on the hook (head to toe), push in, then tilt down to the shoe for "hole in his shoe"
        k = smoothstep(0, 7.0, t); ks = smoothstep(H_SHOE_CU - 0.4, H_SHOE_CU + 0.5, t)
        shoe = roy.world("r_ankle")
        cam = vlerp((1.0, -4.9, z0 + 0.9), (0.7, -3.8, z0 + 0.9), k).lerp(shoe + Vector((0.45, -1.05, 1.0)), ks)
        tgt = Vector((0.1, 0.3, z0 + lerp(2.25, 2.0, k))).lerp(shoe + Vector((0.0, -0.10, 0.0)), ks)
        S["focus"].location = Vector((0, 0.3, z0 + 1.2)).lerp(shoe + Vector((0, -0.1, 0)), ks)
    else:
        k = smoothstep(H_HAIR0, H_HAIR0 + 4.4, t)
        cam = vlerp((0.9, -3.4, z0 + 1.3), (0.6, -2.7, z0 + 1.45), k); tgt = Vector((0.1, 0.3, z0 + 2.0)); S["focus"].location = Vector((0, 0.3, z0 + 1.7))
    S["cam"].location = cam + shake; S["tgt"].location = tgt

# ----------------------------------------------------------------------------- shot G: golf course, 1975
def build_G():
    S = {}; S["flash"] = storm_world((0.07, 0.08, 0.10), (0.45, 0.48, 0.50), 1.1, 0.6); rng = random.Random(5)
    PX, PY = 0.0, 7.0   # pond centre
    def fz(x, y):
        d = math.hypot((x - PX) / 1.4, y - PY)
        return 0.3 * noise2(x, y, 14, 1) + 0.6 * noise2(x, y, 40, 3) - 0.9 * (1 - smoothstep(3.5, 6.0, d)) + 0.6 * smoothstep(20, 50, y)
    # fairway stripes (mowing pattern) via a wave texture on X
    m, nt, out = new_mat("turf"); n = nt.nodes; L = nt.links
    p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Roughness"].default_value = 0.75; tc = n.new("ShaderNodeTexCoord")
    wv = n.new("ShaderNodeTexWave"); wv.inputs["Scale"].default_value = 0.06; wv.wave_profile = "SAW"; L.new(tc.outputs["Object"], wv.inputs["Vector"])
    st = n.new("ShaderNodeMath"); st.operation = "GREATER_THAN"; st.inputs[1].default_value = 0.5; L.new(wv.outputs["Fac"], st.inputs[0])
    mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.inputs[6].default_value = (0.11, 0.30, 0.07, 1); mx.inputs[7].default_value = (0.16, 0.38, 0.09, 1); L.new(st.outputs[0], mx.inputs[0])
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.3; L.new(tc.outputs["Object"], nz.inputs["Vector"])
    mx2 = n.new("ShaderNodeMix"); mx2.data_type = "RGBA"; mx2.blend_type = "MULTIPLY"; mx2.inputs[0].default_value = 0.5; L.new(mx.outputs[2], mx2.inputs[6]); L.new(nz.outputs["Color"], mx2.inputs[7])
    L.new(mx2.outputs[2], p.inputs["Base Color"]); L.new(p.outputs[0], out.inputs[0])
    displaced_grid("course", 120, 200, fz, m)
    # pond: dark glossy water with animated rain ripples
    wm, nt, out = new_mat("pond"); n = nt.nodes; L = nt.links
    p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Base Color"].default_value = (0.02, 0.05, 0.05, 1); p.inputs["Roughness"].default_value = 0.04
    tc = n.new("ShaderNodeTexCoord"); vz = n.new("ShaderNodeTexVoronoi"); vz.voronoi_dimensions = "4D"; vz.inputs["Scale"].default_value = 3.5; L.new(tc.outputs["Object"], vz.inputs["Vector"])
    wvv = n.new("ShaderNodeValue"); wvv.name = "rip"; L.new(wvv.outputs[0], vz.inputs["W"])
    sn = n.new("ShaderNodeMath"); sn.operation = "SINE"; mm = n.new("ShaderNodeMath"); mm.operation = "MULTIPLY"; mm.inputs[1].default_value = 40.0
    L.new(vz.outputs["Distance"], mm.inputs[0]); L.new(mm.outputs[0], sn.inputs[0])
    fade = n.new("ShaderNodeMath"); fade.operation = "MULTIPLY"; L.new(sn.outputs[0], fade.inputs[0])
    inv = n.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 0.35; L.new(vz.outputs["Distance"], inv.inputs[1]); L.new(inv.outputs[0], fade.inputs[1])
    bp = n.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.25; L.new(fade.outputs[0], bp.inputs["Height"]); L.new(bp.outputs[0], p.inputs["Normal"])
    p.inputs["Emission Color"].default_value = (0.7, 0.85, 1.0, 1); pe = n.new("ShaderNodeValue"); pe.name = "pondglow"; L.new(pe.outputs[0], p.inputs["Emission Strength"])
    L.new(p.outputs[0], out.inputs[0]); S["pond"] = wm
    bm = bmesh.new(); bmesh.ops.create_circle(bm, cap_ends=True, segments=64, radius=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * 6.2 * (1 + 0.08 * mnoise.noise(v.co * 2)), v.co.y * 4.6, 0))
    ob = link_obj("pond", mesh_from_bm("pond", bm, wm, False)); ob.location = (PX, PY, -0.35)
    # sand bunker, green + flag, trees, tree line, golf cart
    sand = ground_material("sand", (0.62, 0.55, 0.40), (0.75, 0.68, 0.52), 2.0, 0.9)
    bm = bmesh.new(); bmesh.ops.create_circle(bm, cap_ends=True, segments=40, radius=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * 3.0, v.co.y * 1.5, 0))
    ob = link_obj("bunker", mesh_from_bm("bunker", bm, sand, False)); ob.location = (-7, 16, fz(-7, 16) + 0.03)
    green = principled("green", (0.18, 0.45, 0.10), 0.6)
    bm = bmesh.new(); bmesh.ops.create_circle(bm, cap_ends=True, segments=48, radius=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * 6.0, v.co.y * 4.5, 0))
    ob = link_obj("puttinggreen", mesh_from_bm("puttinggreen", bm, green, False)); ob.location = (6, 20, fz(6, 20) + 0.05)
    cylinder("pin", 0.02, 0.02, 2.2, (6.5, 20.5, fz(6.5, 20.5) + 1.1), principled("pinm", (0.9, 0.9, 0.9), 0.3), segs=8)
    S["flag"] = box("flagcloth", (0.55, 0.01, 0.38), (6.78, 20.5, fz(6.5, 20.5) + 1.98), principled("flagm", (0.85, 0.08, 0.06), 0.6))
    bark = principled("barkG", (0.12, 0.08, 0.05), 0.9); leaf = leaf_material("leafG", (0.05, 0.12, 0.04), (0.12, 0.22, 0.06), 5)
    for i in range(30):
        x, y = rng.uniform(-35, 35), rng.uniform(12, 70)
        if abs(x - 6) < 8 and abs(y - 20) < 7: continue
        if abs(x) < 9 and y < 13: continue
        round_tree(f"oak{i}", (x, y, fz(x, y) - 0.3), rng.uniform(7, 13), bark, leaf, rng)
    cart_w = principled("cartw", (0.92, 0.92, 0.88), 0.35, coat=0.6); tire = principled("tire", (0.03, 0.03, 0.03), 0.6)
    cx, cy = -6.5, 4.5; cz = fz(cx, cy)
    box("cartbody", (1.2, 2.3, 0.5), (cx, cy, cz + 0.55), cart_w); box("cartseat", (1.1, 0.6, 0.45), (cx, cy + 0.25, cz + 0.95), principled("seat", (0.1, 0.18, 0.4), 0.5))
    box("cartroof", (1.3, 1.8, 0.07), (cx, cy + 0.1, cz + 2.0), cart_w)
    for sx in (-1, 1):
        for sy in (-1, 1): cylinder(f"wheel{sx}{sy}", 0.22, 0.22, 0.16, (cx + sx * 0.62, cy + sy * 0.8, cz + 0.22), tire, segs=16, rot=(0, math.pi / 2, 0))
        seg_between(f"cartpost{sx}", (cx + sx * 0.6, cy + 0.85, cz + 0.7), (cx + sx * 0.6, cy + 0.85, cz + 2.0), 0.025, cart_w)
        seg_between(f"cartpostf{sx}", (cx + sx * 0.6, cy - 0.7, cz + 0.8), (cx + sx * 0.6, cy - 0.6, cz + 2.0), 0.025, cart_w)
    # Lee, sitting at the pond edge against his bag
    LX, LY = 0.3, 0.4; S["lz"] = fz(LX, LY)
    sheath = faded_emission("sheathG", (0.55, 0.72, 1.0), 3.0, noise_scale=9.0); S["sheath"] = sheath
    S["lee"] = Figure("lee", shirt=(0.95, 0.72, 0.10), pants=(0.10, 0.12, 0.20), shoes=(0.92, 0.92, 0.9), skin=(0.62, 0.42, 0.30), hair=(0.05, 0.04, 0.03), sheath_mat=sheath, hat="cap")
    S["LX"], S["LY"] = LX, LY
    bagm = principled("bag", (0.55, 0.05, 0.05), 0.4, coat=0.8); steel = principled("steelG", (0.8, 0.8, 0.82), 0.2, 1.0)
    # bag lying on the grass at his left, clubs sticking out of its mouth (children of the bag, so they follow its tilt)
    bx, by = LX + 0.85, LY + 0.25
    bag = cylinder("bag", 0.17, 0.15, 0.95, (bx, by, S["lz"] + 0.2), bagm, segs=20, rot=(0.15, 1.25, 0.5))
    for i in range(5):
        a = i * 1.25; o = Vector((0.07 * math.cos(a), 0.07 * math.sin(a), 0.52))
        seg_between(f"clubshaft{i}", o - Vector((0, 0, 0.1)), o + Vector((0, 0, 0.22)), 0.01, steel).parent = bag
        box(f"clubhead{i}", (0.09, 0.04, 0.05), o + Vector((0.03, 0.0, 0.24)), steel, rot=(0, 0, a), parent=bag)
    # 1-iron in the right hand (child of the hand empty: continues the forearm)
    club = empty("club", (0, 0, -0.02), S["lee"].J["r_hand"]); S["club"] = club
    cylinder("shaft", 0.008, 0.008, 1.0, (0, 0, -0.45), steel, segs=8, parent=club)
    cylinder("grip", 0.016, 0.014, 0.25, (0, 0, -0.02), principled("grip", (0.05, 0.05, 0.05), 0.7), segs=8, parent=club)
    box("ironhead", (0.09, 0.025, 0.05), (0.035, 0, -0.95), steel, parent=club)
    # striped umbrella planted beside him; flies off on the strike
    um = new_mat("umb")[0]; nt = um.node_tree; n = nt.nodes; L = nt.links; out = n["Material Output"]
    p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Roughness"].default_value = 0.5; tc = n.new("ShaderNodeTexCoord"); sep = n.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Object"], sep.inputs[0])
    at = n.new("ShaderNodeMath"); at.operation = "ARCTAN2"; L.new(sep.outputs["Y"], at.inputs[0]); L.new(sep.outputs["X"], at.inputs[1])
    s8 = n.new("ShaderNodeMath"); s8.operation = "MULTIPLY"; s8.inputs[1].default_value = 4.0; L.new(at.outputs[0], s8.inputs[0])
    sn = n.new("ShaderNodeMath"); sn.operation = "SINE"; L.new(s8.outputs[0], sn.inputs[0]); gt = n.new("ShaderNodeMath"); gt.operation = "GREATER_THAN"; L.new(sn.outputs[0], gt.inputs[0])
    mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.inputs[6].default_value = (0.92, 0.92, 0.9, 1); mx.inputs[7].default_value = (0.8, 0.06, 0.05, 1); L.new(gt.outputs[0], mx.inputs[0])
    L.new(mx.outputs[2], p.inputs["Base Color"]); L.new(p.outputs[0], out.inputs[0])
    S["umb"] = empty("umbrella")
    cylinder("canopy", 1.1, 0.03, 0.42, (0, 0, 1.75), um, segs=16, parent=S["umb"], smooth=False)
    cylinder("pole", 0.015, 0.015, 2.0, (0, 0, 1.0), steel, segs=6, parent=S["umb"])
    # bolt into the pond
    S["bolt"] = Bolt("boltG", (-60, 300, 800), (PX + 1.0, PY + 0.5, -0.3), 7, bolt_material(), radius=0.16, nbranch=8, blen=(60, 220), converge=14)
    S["P"] = (PX + 1.0, PY + 0.5)
    S["smoke"] = Puffs("smokeG", smoke_material("smokeG"), 30)
    S["steam"] = Puffs("steamG", smoke_material("steamGm", (0.7, 0.72, 0.75)), 24)
    S["rain"] = rain("rainG", (0, 4.5, 0), (7, 5, 12), 2400, 0.5, 4, faded_emission("rainGm", (0.8, 0.85, 0.95), 0.18))
    for ob in S["rain"]["obs"]: set_alpha(ob, 1.0)
    S["key"] = light("keyG", "SUN", (0, 0, 100), 2.0, (0.8, 0.85, 1.0), size=0.15, rot=(math.radians(55), 0, math.radians(-25)))
    S["fill"] = light("fillG", "AREA", (2.5, -5, 3), 200, (0.9, 0.92, 1.0), size=6, rot=(math.radians(70), 0, math.radians(25)))
    S["strike"] = light("strikeG", "POINT", (PX + 1, PY + 0.5, 8), 0.0, (0.8, 0.88, 1.0), size=1.5)
    S["cam"], S["tgt"] = camera(34); dof(S["cam"], S["lee"].J["neck"], 4.5)
    S["fz"] = fz
    return S

def update_G(S, t):
    lee = S["lee"]; LX, LY, lz = S["LX"], S["LY"], S["lz"]
    inten, _ = strike_env(t, [G_STRIKE]); grow = smoothstep(G_STRIKE - 0.08, G_STRIKE, t)
    S["bolt"].set(grow, (0.12 if t < G_STRIKE else min(1, inten)) if t > G_STRIKE - 0.08 and t < G_STRIKE + 0.6 else 0.0, 1.0 + 0.6 * min(inten, 1))
    S["flash"].outputs[0].default_value = 0.35 * inten; S["strike"].data.energy = 4e3 * inten
    S["pond"].node_tree.nodes["pondglow"].outputs[0].default_value = 2.0 * inten
    S["pond"].node_tree.nodes["rip"].outputs[0].default_value = t * 1.5
    # sit -> jolt -> stand -> raise the 1-iron -> hold -> shrug
    j = smoothstep(G_STRIKE + 0.06, G_STRIKE + 0.1, t) * (1 - smoothstep(G_STRIKE + 0.45, G_STRIKE + 0.8, t))
    sitj = add_pose(SIT, {"spine": (-0.1, 0, 0), "neck": (0.5, 0, 0), "l_sho": (0, -1.0, 0), "r_sho": (0, 1.0, 0), "l_elb": (0.8, 0, 0), "r_elb": (0.8, 0, 0)}, j)
    sitj = add_pose(sitj, {"l_sho": (0, 0.12 * j * n1(t * 50, 1), 0), "r_sho": (0, -0.12 * j * n1(t * 50, 2), 0)})
    ks = smoothstep(G_STAND0, G_STAND1, t); P = blend_pose(sitj, STAND, ks)
    kr = smoothstep(G_RAISE0, G_RAISE1, t); P = blend_pose(P, RAISE, kr)
    P = blend_pose(P, SHRUG, smoothstep(G_SHRUG, G_SHRUG + 0.35, t))
    P = add_pose(P, {"r_sho": (0.06 * math.sin(t * 2.2) * kr, 0, 0), "neck": (0, 0, 0.18 * math.sin((t - 5.0) * 3) * smoothstep(5.0, 5.3, t) * (1 - smoothstep(6.2, 6.5, t)))})
    pel = lerp(0.20, 0.95, smoothstep(G_STAND0, G_STAND1, t))
    lee.pose(P, (LX, LY - 0.12 * (1 - ks), lz), 0.15 * (1 - ks), pel)
    lee.ground_snap(S["fz"](LX, LY)); lee.J["root"].location.z += 0.06 * j   # seat/soles on the turf, a little hop on the jolt
    lee.set_sheath(min(1.0, inten * 1.1))
    # the club is held down by his side until he raises it; hidden while sitting
    S["club"].hide_render = False
    for ch in S["club"].children: ch.hide_render = t < G_STAND1 - 0.2
    # umbrella: planted at his left; on the strike it lifts, tumbles away and lands behind him
    u = S["umb"]; base = Vector((LX - 0.55, LY - 0.1, lz))
    if t < G_STRIKE + 0.05: u.location = base; u.rotation_euler = (0.05, -0.15, 0)
    else:
        k = t - G_STRIKE - 0.05; u.location = base + Vector((-1.6 * k, 2.4 * k, 6.0 * k - 1.5 * k * k))   # blown up and away, out of frame
        u.rotation_euler = (1.4 * k, -0.15 - 2.6 * k, 0.8 * k)
        if k > 1.6: u.location = (0, 0, -60)
    S["flag"].rotation_euler = (0, 0, 0.15 * math.sin(t * 5.0))
    if not S["smoke"].parts:
        S["smoke"].add(G_STRIKE + 0.06, (LX, LY, lz + 0.7), 9, 0.35, 0.7, 0.15, 1.6, 31, 0.25, 0.6)
        S["steam"].add(G_STRIKE + 0.03, (S["P"][0], S["P"][1], -0.3), 14, 1.4, 2.0, 0.6, 1.5, 32, 0.3, 0.75)   # short-lived: fading puffs read as dark bats against the trees
    S["smoke"].update(t); S["steam"].update(t); rain_update(S["rain"], t)
    shake = Vector((n1(t * 31, 1), n1(t * 29, 2), n1(t * 27, 3))) * 0.08 * inten
    k = smoothstep(0, 6.2, t); up = smoothstep(G_STAND0, G_RAISE1, t)
    S["cam"].location = vlerp((-1.9, -4.1, lz + 0.8), (-1.3, -3.5, lz + 1.0), k) + shake
    S["tgt"].location = Vector((LX + 0.4, LY + 1.0, lz + lerp(1.15, 1.95, up)))

# ----------------------------------------------------------------------------- meadow (shots F and R)
def build_meadow(ring=False):
    S = {}; S["flash"] = storm_world((0.03, 0.035, 0.05), (0.18, 0.20, 0.26), 1.0, 0.75); rng = random.Random(21)
    TX, TY = 0.0, 0.0   # the oak (shot R) stands at the origin
    def fz(x, y): return 0.25 * noise2(x, y, 9, 1) + 0.8 * noise2(x, y, 35, 2) + 1.5 * smoothstep(30, 80, y)
    gm = ground_material("meadow", (0.07, 0.10, 0.04), (0.16, 0.19, 0.07), 0.25, 0.6, ring=((TX, TY), (0.55, 0.7, 1.0)) if ring else None)
    S["gmat"] = gm; displaced_grid("meadow", 150, 220, fz, gm)
    # grass tufts: one joined mesh of thin blades around the action
    bm = bmesh.new()
    for i in range(2600):
        x, y = rng.uniform(-14, 16), rng.uniform(-15, 18); z = fz(x, y)
        for b in range(3):
            a = rng.uniform(0, 6.28); h = rng.uniform(0.15, 0.42); w = 0.012; lean = Vector((math.cos(a), math.sin(a), 0)) * h * 0.3
            v = [bm.verts.new((x + w * math.cos(a + 1.57), y + w * math.sin(a + 1.57), z)), bm.verts.new((x - w * math.cos(a + 1.57), y - w * math.sin(a + 1.57), z)),
                 bm.verts.new((x + lean.x, y + lean.y, z + h))]
            bm.faces.new(v)
    link_obj("grass", mesh_from_bm("grass", bm, principled("blade", (0.10, 0.16, 0.05), 0.6), False))
    # the oak: recursive branches + leaf clumps
    bark = principled("barkM", (0.09, 0.07, 0.05), 0.9); leaf = leaf_material("leafM", (0.03, 0.06, 0.03), (0.08, 0.13, 0.05), 4)
    def branch(p, d, L, r, depth, name):
        q = p + d * L; seg_between(name, p, q, r, bark, 7)
        if depth == 0:
            s = rng.uniform(1.2, 2.0); ellipsoid(name + "lf", q, (s, s, s * 0.8), leaf); return
        for k in range(2 if depth < 3 else 3):
            nd = (d + Vector((rng.uniform(-0.9, 0.9), rng.uniform(-0.9, 0.9), rng.uniform(0.1, 0.6)))).normalized()
            branch(q, nd, L * rng.uniform(0.62, 0.78), r * 0.62, depth - 1, f"{name}{k}")
    branch(Vector((TX, TY, fz(TX, TY) - 0.3)), Vector((0, 0, 1)), 3.4, 0.38, 4, "oak")
    S["oak_top"] = Vector((TX + 0.3, TY, fz(TX, TY) + 9.5))
    # far side: fence line, barn with a lit window, distant trees
    wood = principled("fence", (0.25, 0.19, 0.13), 0.8)
    for i in range(30):
        x = -30 + i * 2.2; y = 26 + 0.15 * x; z = fz(x, y)
        cylinder(f"fpost{i}", 0.06, 0.06, 1.3, (x, y, z + 0.6), wood, segs=6)
        if i: seg_between(f"frail{i}", (x - 2.2, y - 0.33, fz(x - 2.2, y - 0.33) + 1.0), (x, y, z + 1.0), 0.03, wood, 5)
    barn = principled("barnM", (0.35, 0.07, 0.05), 0.7); bz = fz(18, 45)
    box("barn", (10, 7, 5), (18, 45, bz + 2.5), barn, rot=(0, 0, 0.3)); bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=4, radius1=6.8, radius2=0.1, depth=3)
    ob = link_obj("barnroof", mesh_from_bm("barnroof", bm, principled("barnroofm", (0.12, 0.12, 0.13), 0.5), False)); ob.location = (18, 45, bz + 6.5); ob.rotation_euler = (0, 0, 0.3 + math.pi / 4); ob.scale = (1.2, 0.85, 1)
    box("barnwin", (1.2, 0.1, 0.9), (16.0, 41.5, bz + 3.0), emissive("barnwinm", (1.0, 0.7, 0.35), 8), rot=(0, 0, 0.3))
    bark2 = principled("bark2", (0.07, 0.06, 0.05), 0.9)
    for i in range(24):
        x, y = rng.uniform(-80, 80), rng.uniform(55, 120); round_tree(f"far{i}", (x, y, fz(x, y) - 0.5), rng.uniform(9, 16), bark2, leaf, rng)
    S["rain"] = rain("rainM", (0, -3, 0), (8, 8, 12), 2800, 0.45, 5, faded_emission("rainMm", (0.8, 0.85, 0.95), 0.25))
    for ob in S["rain"]["obs"]: set_alpha(ob, 1.0)
    S["moon"] = light("moon", "SUN", (0, 0, 100), 0.35, (0.6, 0.7, 1.0), size=0.2, rot=(math.radians(55), 0, math.radians(-30)))
    S["fz"] = fz
    return S

def build_F():
    S = build_meadow(False); fz = S["fz"]
    YX, YY = 10.0, -6.0; S["yz"] = fz(YX, YY); S["YX"], S["YY"] = YX, YY
    sheath = faded_emission("sheathF", (0.62, 0.76, 1.0), 9.0, noise_scale=5.0, streak=True); S["sheath"] = sheath
    S["you"] = make_roy(sheath)   # v2: the flashover is explained on Roy himself
    S["rain"]["center"] = Vector((YX, YY + 3.5, 0))
    S["pool"] = ellipsoid("exitglow", (YX, YY, S["yz"] + 0.01), (0.55, 0.55, 0.02), faded_emission("exitglowm", (0.6, 0.78, 1.0), 12.0, noise_scale=8.0))   # current leaving through the soles
    # skin-tight "water film" that boils off as steam
    S["steam"] = Puffs("steamF", smoke_material("steamFm", (0.75, 0.78, 0.82)), 54)
    S["smoke"] = Puffs("smokeF", smoke_material("smokeFm"), 20)
    # loose shoes (separate objects so they can fly)
    J = S["you"].J; S["shoes"] = []
    for side in ("l", "r"):
        for ch in list(J[f"{side}_shoe"].children): ch.hide_render = True
        e = empty(f"flyshoe{side}"); ellipsoid(f"flyshoe{side}m", (0, -0.045, -0.045), (0.075, 0.13, 0.055), S["you"].m_shoe, e)
        sh = ellipsoid(f"flyshoe{side}sh", (0, -0.045, -0.045), (0.097, 0.152, 0.077), sheath, e); sh.visible_shadow = False; S["you"].sheath.append(sh)
        S["shoes"].append((side, e))
    S["bolt"] = Bolt("boltF", (YX - 30, YY + 140, 500), (YX, YY, S["yz"] + 1.95), 12, bolt_material(), radius=0.045, nbranch=10, blen=(20, 90), converge=18)
    S["strike"] = light("strikeF", "POINT", (YX + 0.5, YY - 1.0, S["yz"] + 3.5), 0.0, (0.8, 0.88, 1.0), size=0.6)
    S["skin"] = light("skinglow", "POINT", (YX, YY - 0.6, S["yz"] + 1.2), 0.0, (0.6, 0.75, 1.0), size=0.5)
    S["fill"] = light("fillF", "AREA", (YX - 2, YY - 5, S["yz"] + 2.5), 90, (0.6, 0.7, 1.0), size=4, rot=(math.radians(70), 0, math.radians(-20)))
    S["cam"], S["tgt"] = camera(30); dof(S["cam"], S["you"].J["spine"], 3.5)
    return S

def leader_steps(t, t0, t1, steps=16):
    u = smoothstep(t0, t1, t) ** 0.9; return min(1.0, math.floor(u * steps) / steps + (u * steps - math.floor(u * steps)) * 0.2)

def update_F(S, t):
    you = S["you"]; YX, YY, yz = S["YX"], S["YY"], S["yz"]
    grow = 1.0 if t >= F_STRIKE else leader_steps(t, F_LEADER0, F_STRIKE - 0.05)
    # slow motion: the return stroke flares and decays over seconds instead of microseconds
    ret = pulse(t, F_STRIKE, 0.06, 0.25, 1.4) if t >= F_STRIKE else 0.0
    S["bolt"].set(grow, max(0.10 * (t > F_LEADER0), min(1.0, ret)), 1.0 + 0.8 * ret)
    S["flash"].outputs[0].default_value = 0.25 * ret; S["strike"].data.energy = 500 * ret
    sh = smoothstep(F_STRIKE, F_STRIKE + 0.12, t) * (1 - 0.65 * smoothstep(F_STRIKE + 1.5, 7.6, t))
    you.set_sheath(sh); S["sheath"].node_tree.nodes["flow"].outputs[0].default_value = t * 1.6
    set_alpha(S["pool"], sh * 0.5 + 1.2 * pulse(t, F_SHOES - 0.2, 0.1, 0.2, 0.5))
    S["pool"].data.materials[0].node_tree.nodes["flow"].outputs[0].default_value = t * 2.0
    hat = you.J["hat"]; k = t - F_STRIKE; up = 0.35 * smoothstep(0, 1.5, k) if k > 0 else 0.0   # slow-mo hat lift
    hat.location = (0, 0, 0.11 + up); hat.rotation_euler = (0.3 * up, 0, 1.2 * up)
    S["skin"].data.energy = 120 * sh
    # pose: stands in the rain looking up; at the strike, frozen jolt (slow-mo), shoes leave at F_SHOES
    P = blend_pose(STAND, {"neck": (0.45, 0, 0), "spine": (0.05, 0, 0), "l_sho": (0.05, -0.15, 0), "r_sho": (0.05, 0.15, 0)}, smoothstep(0.0, 1.5, t))
    P = blend_pose(P, JOLT, 0.8 * smoothstep(F_STRIKE, F_STRIKE + 1.2, t))
    lift = 0.12 * smoothstep(F_SHOES - 0.1, F_SHOES + 0.6, t)
    you.pose(P, (YX, YY, yz), 0.0); you.ground_snap(yz); you.J["root"].location.z += lift; bpy.context.view_layer.update()
    for side, e in S["shoes"]:
        anchor = you.J[f"{side}_shoe"].matrix_world.copy()
        if t < F_SHOES: e.matrix_world = anchor if t > 0 else anchor; continue
        k = t - F_SHOES; sx = 1 if side == "l" else -1
        base = Vector((YX + 0.1 * sx, YY, yz + 0.05)); e.location = base + Vector((0.5 * sx * k, -0.35 * k, 1.5 * k - 0.9 * k * k))   # slow-mo arc, stays in frame
        e.rotation_euler = (2.0 * k, 1.0 * sx * k, 1.2 * k)
    if not S["steam"].parts:
        rs = random.Random(3)
        for i in range(10):   # steam from the wet skin and clothes, rising through the sheath
            z = rs.uniform(0.3, 1.8); S["steam"].add(F_STEAM + i * 0.25, (YX + rs.uniform(-0.2, 0.2), YY + rs.uniform(-0.1, 0.1), yz + z), 5, 0.25, 0.35, 0.10, 2.2, 50 + i, 0.2, 0.55)
        S["smoke"].add(F_SHOES, (YX, YY, yz + 0.08), 12, 0.6, 0.4, 0.12, 1.5, 61, 0.1, 0.8)
    S["steam"].update(t); S["smoke"].update(t)
    rain_update(S["rain"], t, 1.2 if t > F_STRIKE else 6.0 - 4.8 * smoothstep(F_STRIKE - 1.0, F_STRIKE, t))   # rain slows into slow motion
    # camera: wide on the leader coming down, then a slow orbit close around the figure
    # orbit away from the oak (it read as a dark blob top-left)
    a = lerp(-0.25, -0.75, smoothstep(F_STRIKE, 7.3, t)); r = lerp(7.5, 3.9, smoothstep(0.4, F_STRIKE + 0.6, t))
    hz = lerp(1.3, 1.1, smoothstep(F_STRIKE, 8, t))
    S["cam"].location = Vector((YX + r * math.sin(a), YY - r * math.cos(a), yz + hz))
    S["tgt"].location = Vector((YX, YY, yz + lerp(3.6, 1.45, smoothstep(0.6, F_STRIKE + 0.4, t))))   # head stays low in frame, under the captions

def build_R():
    S = build_meadow(True); fz = S["fz"]
    HX, HY = 3.6, -3.3; S["hz"] = fz(HX, HY); S["HX"], S["HY"] = HX, HY
    S["hiker"] = Figure("hiker", shirt=(0.85, 0.30, 0.10), pants=(0.25, 0.24, 0.20), shoes=(0.25, 0.15, 0.08), hair=(0.25, 0.15, 0.08), hat="cap")
    pack = principled("pack", (0.10, 0.35, 0.30), 0.6); ellipsoid("pack", (0, 0.2, 0.28), (0.17, 0.11, 0.24), pack, S["hiker"].J["spine"])
    S["legpath"] = curve_obj("legpath", [(0, 0, 0)] * 9, faded_emission("legcur", (0.6, 0.78, 1.0), 12.0, noise_scale=30.0), 0.105); S["legpath"].data.bevel_resolution = 3
    S["bolt"] = Bolt("boltR", (-40, 160, 520), tuple(S["oak_top"]), 9, bolt_material(), radius=0.35, nbranch=9, blen=(40, 160), converge=16)
    S["side"] = Bolt("sideR", tuple(S["oak_top"] + Vector((0.4, -0.5, -3.5))), (HX - 0.5, HY + 0.6, S["hz"] + 1.2), 4, bolt_material(), radius=0.06, nbranch=0, converge=4)
    S["smoke"] = Puffs("smokeR", smoke_material("smokeRm"), 24)
    S["strike"] = light("strikeR", "POINT", (4.0, -7.0, 4.0), 0.0, (0.8, 0.88, 1.0), size=1.0)
    S["fill"] = light("fillR", "AREA", (HX - 3, HY - 6, S["hz"] + 3), 140, (0.6, 0.7, 1.0), size=5, rot=(math.radians(70), 0, math.radians(-25)))
    S["cam"], S["tgt"] = camera(24); dof(S["cam"], S["hiker"].J["spine"], 6.0)
    return S

def update_R(S, t):
    h = S["hiker"]; HX, HY, hz = S["HX"], S["HY"], S["hz"]
    inten, _ = strike_env(t, [R_STRIKE]); grow = smoothstep(R_STRIKE - 0.1, R_STRIKE, t)
    S["bolt"].set(grow, (0.12 if t < R_STRIKE else min(1, inten)) if R_STRIKE - 0.1 < t < R_STRIKE + 0.6 else 0.0, 1 + 0.6 * min(1, inten))
    S["side"].set(1.0, 0.5 * pulse(t, R_STRIKE + 0.02, 0.01, 0.04, 0.08), 1.0)
    S["flash"].outputs[0].default_value = 0.4 * inten; S["strike"].data.energy = 5e3 * inten
    # ground current ring (slow-mo visualisation): spreads from the trunk, reaches the hiker at R_RING1
    rr = R_RADIUS * smoothstep(R_STRIKE, R_RING1, t) ** 0.8 + 1.5 * smoothstep(R_RING1, 6.0, t)
    nd = S["gmat"].node_tree.nodes; nd["ring_r"].outputs[0].default_value = rr
    nd["ring_a"].outputs[0].default_value = 30.0 * smoothstep(R_STRIKE, R_STRIKE + 0.1, t) * (1 - smoothstep(5.2, 5.9, t))
    # pose: feet apart, looking up at the tree; jolt when the current runs through
    look = blend_pose(STAND, {"neck": (0.35, 0, 0.6), "spine": (0, 0, 0.25), "l_hip": (0.2, 0.18, 0), "r_hip": (-0.2, -0.18, 0)}, 1.0)
    j = smoothstep(R_STRIKE, R_STRIKE + 0.05, t) * (1 - smoothstep(R_STRIKE + 0.3, R_STRIKE + 0.6, t)) * 0.5 + smoothstep(R_LEG1 - 0.1, R_LEG1, t) * (1 - smoothstep(R_LEG1 + 0.35, R_LEG1 + 0.7, t))
    P = blend_pose(look, JOLT, j)
    P = add_pose(P, {"l_sho": (0, 0.15 * j * n1(t * 50, 1), 0), "r_sho": (0, -0.15 * j * n1(t * 50, 2), 0)})
    h.pose(P, (HX, HY, hz + 0.08 * j), 2.6)
    bpy.context.view_layer.update()
    # current path: left foot -> knee -> hip -> pelvis -> right hip -> knee -> foot
    js = ["l_ankle", "l_knee", "l_hip", "pelvis", "r_hip", "r_knee", "r_ankle"]
    pts = [h.world(js[0]) + Vector((0, 0, -0.08))] + [h.world(k) for k in js] + [h.world(js[-1]) + Vector((0, 0, -0.08))]
    for p, q in zip(S["legpath"].data.splines[0].points, pts): p.co = (q.x, q.y, q.z, 1.0)
    S["legpath"].data.bevel_factor_start = smoothstep(R_LEG1, R_LEG1 + 0.5, t)
    S["legpath"].data.bevel_factor_end = smoothstep(R_LEG0, R_LEG1, t)
    set_alpha(S["legpath"], (1.0 + 0.3 * n1(t * 40, 4)) * smoothstep(R_LEG0, R_LEG0 + 0.05, t) * (1 - smoothstep(R_LEG1 + 0.4, R_LEG1 + 0.55, t)))
    if not S["smoke"].parts:
        S["smoke"].add(R_STRIKE + 0.05, S["oak_top"] + Vector((0, 0, -3.0)), 12, 1.2, 1.0, 0.6, 2.5, 91, 0.3, 0.6)
        S["smoke"].add(R_LEG1 + 0.1, (HX, HY, hz + 0.1), 8, 0.4, 0.4, 0.1, 1.4, 92, 0.2, 0.7)
    S["smoke"].update(t); rain_update(S["rain"], t)
    shake = Vector((n1(t * 31, 1), n1(t * 29, 2), n1(t * 27, 3))) * 0.08 * inten
    k = smoothstep(0, 6.0, t)
    S["cam"].location = vlerp((7.4, -9.6, hz + 1.1), (6.6, -8.3, hz + 0.95), k) + shake
    S["tgt"].location = vlerp((1.6, 0.0, hz + 4.6), (2.6, -2.2, hz + 2.6), smoothstep(R_RING1 - 1.6, R_LEG0, t))

# ----------------------------------------------------------------------------- shot L: Lichtenberg figure on a forearm
def lichtenberg(rng, root, ang, L, depth, out, gen=0, t0=0.0):
    """Fern-like branching in (s, theta) arm-surface coordinates. Returns list of (pts2d, gen, start_delay, width)."""
    pts = [root]; p = list(root); a = ang; n = max(4, int(L / 0.005)); side = 1 if rng.random() < 0.5 else -1
    for i in range(n):
        a += rng.gauss(0, 0.09); step = L / n; p = [p[0] + step * math.cos(a), p[1] + step * math.sin(a)]; pts.append(tuple(p))
        if depth > 0 and i > 0 and i % 2 == 0 and rng.random() < 0.8:   # fern: leaflets alternate sides at a steady angle, shrinking toward the tip
            side = -side
            lichtenberg(rng, tuple(p), a + side * rng.uniform(0.7, 0.95), L * (1 - i / n) * rng.uniform(0.3, 0.45), depth - 1, out, gen + 1, t0 + (i / n) * 0.35 * (0.7 ** gen))
    out.append((pts, gen, t0, 0.0026 * (0.62 ** gen)))
    return out

def build_L():
    S = {}; w = bpy.data.worlds.new("room"); bpy.context.scene.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.60, 0.66, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.2
    S["flash"] = None
    # hospital sheet with soft folds
    def fz(x, y): return 0.012 * noise2(x, y, 0.12, 1) + 0.006 * math.sin(x * 9 + 2 * noise2(x, y, 0.3, 2))
    sheet = ground_material("sheet", (0.62, 0.72, 0.80), (0.74, 0.82, 0.88), 3.0, 0.8)
    displaced_grid("sheet", 1.5, 160, fz, sheet)
    pillow = principled("pillow", (0.9, 0.9, 0.92), 0.8); ellipsoid("pillow", (-0.1, 0.55, 0.06), (0.5, 0.22, 0.08), pillow)
    # forearm along X (wrist at -X), lying on the sheet; superellipse-ish rings
    skin = principled("armskin", (0.80, 0.58, 0.45), 0.42, coat=0.15)
    skin.node_tree.nodes["Principled BSDF"].inputs["Subsurface Weight"].default_value = 0.0
    def radius(s): return lerp(0.030, 0.042, smoothstep(-0.16, 0.16, s)) * (1 + 0.06 * math.sin((s + 0.16) * 9))
    bm = bmesh.new(); rings = []; NS, NA = 60, 40
    for i in range(NS + 1):
        s = -0.18 + 0.36 * i / NS; r = radius(s)
        rings.append([bm.verts.new((s, r * math.cos(2 * math.pi * j / NA), 0.75 * r * math.sin(2 * math.pi * j / NA) + 0.045)) for j in range(NA)])
    for a, b in zip(rings[:-1], rings[1:]):
        for j in range(NA): bm.faces.new((a[j], a[(j + 1) % NA], b[(j + 1) % NA], b[j]))
    link_obj("forearm", mesh_from_bm("forearm", bm, skin))
    ellipsoid("hand", (-0.235, 0.0, 0.04), (0.07, 0.048, 0.022), skin, rot=(0, 0, 0.1))
    for k in range(4): ellipsoid(f"finger{k}", (-0.32 - 0.004 * k, -0.03 + 0.02 * k, 0.035), (0.045, 0.009, 0.009), skin, rot=(0, 0, 0.12 - 0.06 * k))
    ellipsoid("thumb", (-0.24, -0.06, 0.04), (0.04, 0.011, 0.011), skin, rot=(0, 0, 0.7))
    ellipsoid("elbow", (0.2, 0.0, 0.045), (0.05, 0.047, 0.036), skin)
    sleeve = principled("gown", (0.35, 0.52, 0.62), 0.8); ellipsoid("sleeve", (0.3, 0.02, 0.05), (0.12, 0.065, 0.05), sleeve)
    # fern pattern on the top of the arm
    rng = random.Random(8); branches = []
    lichtenberg(rng, (0.14, 0.004), math.pi + 0.05, 0.25, 3, branches)
    lichtenberg(rng, (0.12, -0.010), math.pi - 0.45, 0.14, 2, branches)
    lichtenberg(rng, (0.13, 0.016), math.pi + 0.5, 0.13, 2, branches)
    fm = faded_emission("fern", (0.9, 0.18, 0.15), 1.2)
    # the fern is darker red skin, not a light: emission low, mixed over a red diffuse
    fm2, nt, out = new_mat("fernskin"); n = nt.nodes; Ln = nt.links
    oi = n.new("ShaderNodeObjectInfo"); p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Base Color"].default_value = (0.55, 0.06, 0.06, 1); p.inputs["Roughness"].default_value = 0.4
    p.inputs["Emission Color"].default_value = (1.0, 0.25, 0.15, 1); e = n.new("ShaderNodeMath"); e.operation = "MULTIPLY"; e.inputs[1].default_value = 0.6; Ln.new(oi.outputs["Alpha"], e.inputs[0]); Ln.new(e.outputs[0], p.inputs["Emission Strength"])
    tr = n.new("ShaderNodeBsdfTransparent"); mx = n.new("ShaderNodeMixShader"); Ln.new(oi.outputs["Alpha"], mx.inputs[0]); Ln.new(tr.outputs[0], mx.inputs[1]); Ln.new(p.outputs[0], mx.inputs[2]); Ln.new(mx.outputs[0], out.inputs[0])
    S["fern"] = []
    for k, (pts, gen, t0, wdt) in enumerate(branches):
        p3 = []
        for (s, th) in pts:
            if not (-0.17 < s < 0.17): break
            r = radius(s) * 1.004; th = th / r; p3.append((s, r * math.sin(th), 0.75 * r * math.cos(th) + 0.045))
        if len(p3) < 3: continue
        ob = curve_obj(f"fern{k}", p3, fm2, wdt); ob.data.bevel_resolution = 0; S["fern"].append((ob, t0, gen))
    S["key"] = light("window", "AREA", (-0.6, -0.5, 0.9), 60, (1.0, 0.96, 0.9), size=0.8, rot=(math.radians(40), 0, math.radians(-50)))
    S["fill"] = light("fillL", "AREA", (0.6, -0.4, 0.4), 12, (0.8, 0.88, 1.0), size=0.6, rot=(math.radians(60), 0, math.radians(55)))
    S["cam"], S["tgt"] = camera(50); S["focus"] = empty("lfocus", (0.0, 0.0, 0.08)); dof(S["cam"], S["focus"], 2.8)
    return S

def update_L(S, t):
    for ob, t0, gen in S["fern"]:
        k = smoothstep(L_GROW0 + t0 * (L_GROW1 - L_GROW0) / 0.6, L_GROW0 + t0 * (L_GROW1 - L_GROW0) / 0.6 + 0.6, t)
        ob.data.bevel_factor_end = k
        set_alpha(ob, (1.0 if k > 0.001 else 0.0) * (1 - 0.92 * smoothstep(L_FADE0, L_FADE1, t)))
    k = smoothstep(0, 4.8, t)
    S["cam"].location = vlerp((0.36, -0.10, 0.36), (0.30, -0.07, 0.30), k)
    S["tgt"].location = vlerp((-0.02, 0.0, 0.045), (0.0, 0.0, 0.045), k)

# ----------------------------------------------------------------------------- shot T: strike two, 1969, through the truck window
SEATED = {"spine": (0.05, 0, 0), "neck": (0.05, 0, 0), "l_hip": (-1.5, -0.08, 0), "r_hip": (-1.5, 0.08, 0), "l_knee": (1.45, 0, 0), "r_knee": (1.45, 0, 0),
          "l_sho": (-1.15, -0.25, 0), "r_sho": (-1.15, 0.25, 0), "l_elb": (-0.45, 0, 0), "r_elb": (-0.45, 0, 0)}
def build_T():
    S = {}; S["flash"] = storm_world((0.06, 0.07, 0.10), (0.42, 0.46, 0.52), 1.0, 0.65); rng = random.Random(13)
    def fz(x, y):   # mountain road on a shoulder: flat road band along x, slope falling away behind (+y)
        road = 1 - smoothstep(3.0, 5.0, abs(y - 0.0))
        return (1 - road) * (0.4 * noise2(x, y, 5, 1) - 0.08 * max(0, y - 4) ** 1.3 + 0.4 * max(0, -y - 11) ** 1.1)   # bank rises only behind the camera
    S["fz"] = fz
    displaced_grid("shoulder", 80, 140, fz, ground_material("verge", (0.10, 0.13, 0.05), (0.22, 0.24, 0.09), 0.35, 0.85))
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=2, y_segments=2, size=1.0)
    ob = link_obj("road", mesh_from_bm("road", bm, ground_material("asphalt", (0.05, 0.05, 0.055), (0.09, 0.09, 0.095), 3.0, 0.35), False)); ob.scale = (40, 2.6, 1); ob.location = (0, 0, 0.01)
    for i in range(14): box(f"dash{i}", (1.5, 0.12, 0.01), (-30 + i * 5, 0.0, 0.02), emissive("paint", (0.9, 0.8, 0.3), 0.6))
    blue_ridge(S, rng, True, fz, tree_box=((-25, 25), (6, 40)))
    # ranger pickup facing -x; the driver's (left) side faces the camera at -y
    paint = principled("truckpaint", (0.16, 0.28, 0.18), 0.25, coat=0.9); trim = principled("trim", (0.75, 0.75, 0.72), 0.3, 0.8)
    tire = principled("tireT", (0.03, 0.03, 0.03), 0.7); glassm = principled("truckglass", (0.05, 0.07, 0.08), 0.03)
    glassm.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.35
    T = empty("truck"); S["truck"] = T; body = []
    def tb(name, dims, loc, mat, rot=(0, 0, 0)):
        ob = box(name, dims, loc, mat, rot=rot, parent=T); body.append(ob); return ob
    tb("hood", (1.15, 1.75, 0.55), (-1.95, 0, 0.95), paint); tb("grille", (0.06, 1.5, 0.4), (-2.55, 0, 0.9), trim)
    tb("cabdoor", (1.45, 1.75, 0.62), (-0.6, 0, 0.98), paint); tb("roof", (1.35, 1.7, 0.08), (-0.55, 0, 1.92), paint)
    for x in (-1.25, 0.12):
        for y in (-0.84, 0.84): tb(f"pillar{x}{y}", (0.09, 0.07, 0.62), (x, y, 1.6), paint)
    tb("bed", (2.1, 1.75, 0.65), (1.25, 0, 0.98), paint); tb("bumper", (0.12, 1.85, 0.16), (-2.58, 0, 0.6), trim)
    box("windshield", (0.05, 1.6, 0.6), (-1.27, 0, 1.6), glassm, rot=(0, -0.35, 0), parent=T); box("backglass", (0.04, 1.55, 0.5), (0.14, 0, 1.6), glassm, parent=T)
    box("passglass", (1.3, 0.03, 0.55), (-0.56, 0.84, 1.6), glassm, parent=T)
    S["pane"] = box("driverglass", (1.3, 0.03, 0.56), (-0.56, -0.84, 1.0), glassm, parent=T)   # rolls up on "Windows up"
    for x in (-1.75, 1.45):
        for y in (-0.82, 0.82): cylinder(f"wheel{x}{y}", 0.42, 0.42, 0.28, (x, y, 0.42), tire, segs=24, rot=(math.pi / 2, 0, 0), parent=T)
        for y in (-0.97, 0.97): ellipsoid(f"hub{x}{y}", (x, y, 0.42), (0.2, 0.02, 0.2), trim, T)
    for y in (-0.6, 0.6): ellipsoid(f"headlamp{y}", (-2.58, y, 1.0), (0.03, 0.12, 0.09), emissive("lampm", (1.0, 0.95, 0.8), 12), T)
    ellipsoid("beacon", (-0.55, 0, 2.02), (0.09, 0.09, 0.07), emissive("amber", (1.0, 0.5, 0.05), 20), T)
    ellipsoid("doorbadge", (-0.55, -0.88, 1.05), (0.16, 0.01, 0.16), principled("badgeT", (0.85, 0.7, 0.3), 0.3, 1.0), T)
    tor = bpy.data.meshes.new("wheelring"); bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=False, segments=24, radius=0.17); bm.to_mesh(tor); bm.free()
    sw = link_obj("steer", tor, T); sw.location = (-1.0, -0.35, 1.38); sw.rotation_euler = (0, -1.1, 0)
    sk = sw.modifiers.new("skin", "SKIN"); sw.data.materials.append(trim)
    for v in sw.data.skin_vertices[0].data: v.radius = (0.018, 0.018)
    # current over the metal shell (strike on the roof): a streaky glowing copy of the body panels
    shell = faded_emission("shellm", (0.6, 0.78, 1.0), 6.0, noise_scale=3.0, streak=True); S["shellmat"] = shell; S["shell"] = []
    for ob in body:
        c = box(ob.name + "_sh", (1, 1, 1), ob.location, shell, rot=ob.rotation_euler, parent=T)
        c.data = ob.data.copy(); c.data.materials.clear(); c.data.materials.append(shell); c.scale = (1.03, 1.03, 1.06); c.visible_shadow = False; S["shell"].append(c)
    S["tirepools"] = [ellipsoid(f"tirepool{x}{y}", (x, y, 0.02), (0.45, 0.3, 0.01), faded_emission(f"tp{x}{y}", (0.6, 0.78, 1.0), 10.0, noise_scale=6.0), T) for x in (-1.75, 1.45) for y in (-0.82, 0.82)]
    # Roy in the driver's seat (figure faces -Y, rotate to face -x)
    sheath = faded_emission("sheathT", (0.6, 0.76, 1.0), 6.0, noise_scale=6.0, streak=True); S["sheath"] = sheath
    S["roy"] = make_roy(sheath)
    S["smoke"] = Puffs("smokeT", smoke_material("smokeTm"), 30)
    S["rain"] = rain("rainT", (-0.5, 3.0, 0), (6, 4, 12), 2200, 0.5, 6, faded_emission("rainTm", (0.8, 0.85, 0.95), 0.18))
    for ob in S["rain"]["obs"]: set_alpha(ob, 1.0)
    bm_ = bolt_material()
    S["bolt1"] = Bolt("boltT1", (-160, 60, 650), (-0.5, -0.35, 1.62), 21, bm_, radius=0.05, nbranch=7, blen=(50, 200), mid=(-7.0, -2.2, 18.0), via=(-0.6, -1.2, 1.72))
    S["bolt2"] = Bolt("boltT2", (120, 160, 650), (-0.55, 0.0, 1.98), 22, bm_, radius=0.06, nbranch=7, blen=(50, 200))
    S["key"] = light("keyT", "SUN", (0, 0, 100), 1.5, (0.75, 0.82, 1.0), size=0.12, rot=(math.radians(50), 0, math.radians(-30)))
    S["fill"] = light("fillT", "AREA", (-1.5, -5, 2.5), 160, (0.85, 0.9, 1.0), size=5, rot=(math.radians(70), 0, 0))
    S["cabflash"] = light("cabflash", "POINT", (-0.5, -0.3, 1.6), 0.0, (0.8, 0.88, 1.0), size=0.3)
    S["strike"] = light("strikeT", "POINT", (-0.5, -3.0, 5.0), 0.0, (0.8, 0.88, 1.0), size=1.0)
    S["cam"], S["tgt"] = camera(32); S["focus"] = empty("focusT"); dof(S["cam"], S["focus"], 4.0)
    return S

def update_T(S, t):
    roy = S["roy"]
    i1, _ = strike_env(t, [T_STRIKE1]); i2, _ = strike_env(t, [T_STRIKE2])
    for b, ts, inten in ((S["bolt1"], T_STRIKE1, i1), (S["bolt2"], T_STRIKE2, i2)):
        grow = smoothstep(ts - 0.08, ts, t); b.set(grow, (0.12 if t < ts else min(1, inten)) if ts - 0.08 < t < ts + 0.6 else 0.0, 1.0)
    S["flash"].outputs[0].default_value = 0.35 * max(i1, i2); S["strike"].data.energy = 6e3 * i2; S["cabflash"].data.energy = 1500 * i1
    # Roy driving; strike two jolts him; afterwards a thumbs-up from inside the cab during the roof strike
    P = blend_pose(SEATED, add_pose(JOLT, {"l_hip": (-1.5, 0, 0), "r_hip": (-1.5, 0, 0), "l_knee": (1.45, 0, 0), "r_knee": (1.45, 0, 0)}), 0.7 * smoothstep(T_STRIKE1, T_STRIKE1 + 0.05, t) * (1 - smoothstep(T_STRIKE1 + 0.4, T_STRIKE1 + 0.8, t)))
    P = add_pose(P, {"neck": (0, 0, 0.5 * smoothstep(T_STRIKE1 + 1.0, T_STRIKE1 + 1.4, t) * (1 - smoothstep(T_THUMB + 1.2, T_THUMB + 1.6, t)))})   # turns to camera
    P = blend_pose(P, {**SEATED, "l_sho": (-2.2, -0.55, 0), "l_elb": (-1.4, 0, 0), "neck": (0.1, 0, 0.5)}, smoothstep(T_THUMB, T_THUMB + 0.35, t))
    roy.pose(P, (-0.45, -0.38, 0.0), math.pi / 2, 1.08)   # +90 deg: the figure's -Y front turns to -x (the hood)
    roy.set_sheath(min(1.0, i1 * 1.1)); S["sheath"].node_tree.nodes["flow"].outputs[0].default_value = t * 9.0
    for b in roy.brows: b.hide_render = t >= T_STRIKE1 + 0.05
    roy.J["hat"].location = (0, 0, 0.11 + 0.08 * math.sin(math.pi * min(1, max(0, t - T_STRIKE1) / 0.4)))
    # window rolls up, then the roof strike: current runs over the shell and into the ground at the tyres
    S["pane"].location.z = lerp(1.0, 1.6, smoothstep(T_WINUP0, T_WINUP1, t))
    sh = smoothstep(T_STRIKE2, T_STRIKE2 + 0.08, t) * (1 - smoothstep(T_STRIKE2 + 0.9, T_STRIKE2 + 1.6, t)) * (0.7 + 0.3 * n1(t * 20, 3))
    for c in S["shell"]: set_alpha(c, sh)
    S["shellmat"].node_tree.nodes["flow"].outputs[0].default_value = t * 3.0
    for p in S["tirepools"]: set_alpha(p, sh * 1.2); p.data.materials[0].node_tree.nodes["flow"].outputs[0].default_value = t * 2.5
    if not S["smoke"].parts:
        S["smoke"].add(T_STRIKE1 + 0.1, (-0.45, -0.55, 1.75), 8, 0.2, 0.5, 0.08, 1.4, 41, 0.2, 0.7)
        S["smoke"].add(T_BROWS, (-0.62, -0.5, 1.73), 7, 0.08, 0.4, 0.05, 1.2, 42, 0.1, 0.9)   # the eyebrows
    S["smoke"].update(t); rain_update(S["rain"], t)
    shake = Vector((n1(t * 31, 1), n1(t * 29, 2), n1(t * 27, 3))) * 0.05 * max(i1, i2)
    # close on the open window, then pull back to the whole truck for the roof strike
    kb = smoothstep(T_WINUP0 - 0.3, T_STRIKE2 - 0.1, t)
    cam = vlerp((-0.15, -3.2, 1.75), (-0.35, -2.7, 1.7), smoothstep(0, T_WINUP0, t)).lerp(Vector((-0.4, -8.6, 2.4)), kb)
    tgt = Vector((-0.75, -0.3, lerp(1.95, 1.75, smoothstep(0, T_WINUP0, t)))).lerp(Vector((-0.5, 0.0, 2.6)), kb)
    S["cam"].location = cam + shake; S["tgt"].location = tgt; S["focus"].location = Vector((-0.5, -0.8, 1.5))

# ----------------------------------------------------------------------------- shot B: strike seven, 1977, fishing -- and the bear
class Bear:
    """Toy black bear on four legs, facing -Y. Walk cycle in pose(); same ellipsoid language as the figures."""
    def __init__(self, name):
        fur = leaf_material("fur", (0.16, 0.10, 0.06), (0.26, 0.17, 0.10), 30.0); tan = principled("muzzle", (0.55, 0.40, 0.26), 0.7)
        dark = principled("bearnose", (0.02, 0.02, 0.02), 0.2, coat=1.0)
        self.root = empty(name); self.body = empty(name + "_body", (0, 0, 0.72), self.root)
        ellipsoid(name + "_torso", (0, 0, 0), (0.38, 0.62, 0.38), fur, self.body)
        ellipsoid(name + "_rump", (0, 0.42, 0.04), (0.36, 0.3, 0.35), fur, self.body)
        self.head = empty(name + "_head", (0, -0.62, 0.22), self.body)
        ellipsoid(name + "_skull", (0, -0.1, 0), (0.24, 0.24, 0.22), fur, self.head)
        ellipsoid(name + "_snout", (0, -0.33, -0.05), (0.11, 0.15, 0.09), tan, self.head)
        ellipsoid(name + "_nose", (0, -0.47, -0.01), (0.045, 0.03, 0.03), dark, self.head)
        for sx in (-1, 1):
            ellipsoid(name + f"_ear{sx}", (0.15 * sx, -0.02, 0.19), (0.07, 0.04, 0.07), fur, self.head)
            ellipsoid(name + f"_eye{sx}", (0.09 * sx, -0.29, 0.07), (0.025, 0.02, 0.025), dark, self.head)
        self.mouth = empty(name + "_mouth", (0, -0.46, -0.1), self.head)
        self.legs = []
        for k, (sx, sy) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
            hip = empty(name + f"_leg{k}", (0.2 * sx, 0.38 * sy, -0.12), self.body)
            ellipsoid(name + f"_legp{k}", (0, 0, -0.26), (0.12, 0.13, 0.3), fur, hip)
            ellipsoid(name + f"_paw{k}", (0, -0.05, -0.55), (0.12, 0.15, 0.06), fur, hip)
            self.legs.append((hip, k))
    def pose(self, loc, heading, phase, amp=0.45, bob=0.04, head_rx=0.0, head_rz=0.0):
        self.root.location = loc; self.root.rotation_euler = (0, 0, heading)
        for hip, k in self.legs:
            ph = phase + (0 if k in (0, 3) else math.pi); hip.rotation_euler = (amp * math.sin(ph), 0, 0)
        self.body.location = (0, 0, 0.72 + bob * abs(math.sin(phase))); self.head.rotation_euler = (head_rx, 0, head_rz)

def build_B():
    S = {}; S["flash"] = storm_world((0.06, 0.07, 0.10), (0.42, 0.46, 0.52), 1.0, 0.65); rng = random.Random(17)
    CX = 2.4   # creek centre line (runs along y)
    def fz(x, y):
        bed = 1 - smoothstep(0.8, 2.0, abs(x - CX - 0.15 * math.sin(y * 0.4)))
        return -0.55 * bed + 0.25 * noise2(x, y, 4, 1) * (1 - bed) + 0.03 * max(0, -x - 2) ** 1.4 + 0.5 * smoothstep(12, 40, y)
    S["fz"] = fz
    displaced_grid("bank", 70, 160, fz, ground_material("bankm", (0.10, 0.13, 0.05), (0.24, 0.25, 0.10), 0.4, 0.85))
    wm, nt, out = new_mat("creek"); n = nt.nodes; L = nt.links
    p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Base Color"].default_value = (0.03, 0.07, 0.08, 1); p.inputs["Roughness"].default_value = 0.05
    tc = n.new("ShaderNodeTexCoord"); nz = n.new("ShaderNodeTexNoise"); nz.noise_dimensions = "4D"; nz.inputs["Scale"].default_value = 2.5; nz.inputs["Detail"].default_value = 4
    mp = n.new("ShaderNodeVectorMath"); mp.operation = "MULTIPLY"; mp.inputs[1].default_value = (3.0, 0.5, 1.0); L.new(tc.outputs["Object"], mp.inputs[0]); L.new(mp.outputs[0], nz.inputs["Vector"])
    fv = n.new("ShaderNodeValue"); fv.name = "flow"; L.new(fv.outputs[0], nz.inputs["W"])
    bp = n.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.35; L.new(nz.outputs["Fac"], bp.inputs["Height"]); L.new(bp.outputs[0], p.inputs["Normal"])
    L.new(p.outputs[0], out.inputs[0]); S["creek"] = wm
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=2, y_segments=2, size=1.0)
    ob = link_obj("creekwater", mesh_from_bm("creekwater", bm, wm, False)); ob.scale = (1.6, 40, 1); ob.location = (CX, 0, -0.38)
    rock = leaf_material("rockB", (0.08, 0.08, 0.085), (0.18, 0.17, 0.16), 3.0)
    S["seat_z"] = None
    for i in range(22):
        x, y = (CX + rng.uniform(-1.6, 1.6), rng.uniform(-3, 14)) if i else (-0.45, 0.15)
        s = rng.uniform(0.25, 0.7) if i else 0.55
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1)
        for v in bm.verts: v.co *= 1 + 0.2 * mnoise.noise(v.co * 1.7 + Vector((i, 3, 0)))
        ob = link_obj(f"rockB{i}", mesh_from_bm(f"rockB{i}", bm, rock, False)); ob.scale = (s * 1.3, s, s * 0.6); ob.location = (x, y, fz(x, y) - s * 0.15)
        if i == 0: S["seat_z"] = fz(x, y) - s * 0.15 + s * 0.6 * 0.9
    blue_ridge(S, rng, True, fz, tree_box=((-20, 20), (3, 35)), keep_clear=lambda x, y: (abs(x - CX) < 3.0) or (abs(x) < 3 and y < 8))
    # Roy on the rock, rod in hand, a caught trout beside him, a stick lying in the grass
    sheath = faded_emission("sheathB", (0.6, 0.76, 1.0), 4.0, noise_scale=6.0, streak=True); S["sheath"] = sheath
    S["roy"] = roy = make_roy(sheath)
    rodm = principled("rod", (0.25, 0.15, 0.08), 0.4)
    S["rod"] = rod = empty("rod", (0, 0, -0.02), roy.J["r_hand"]); cylinder("rodshaft", 0.012, 0.006, 2.2, (0, 0, -1.05), rodm, segs=6, parent=rod)
    S["line"] = curve_obj("fishline", [(0, 0, 0)] * 2, emissive("linem", (0.9, 0.9, 0.9), 0.5), 0.002)
    fishm = leaf_material("trout", (0.35, 0.40, 0.30), (0.70, 0.62, 0.45), 40.0)
    S["fish"] = fish = empty("trout")
    ellipsoid("troutbody", (0, 0, 0), (0.08, 0.28, 0.06), fishm, fish); ellipsoid("trouttail", (0, 0.31, 0), (0.012, 0.08, 0.065), fishm, fish)
    S["stick"] = stick = empty("stick"); cylinder("stickm", 0.025, 0.018, 0.9, (0, 0, 0), principled("stickwood", (0.22, 0.14, 0.08), 0.9), segs=6, parent=stick)
    S["bear"] = Bear("bear")
    S["smoke"] = Puffs("smokeB", smoke_material("smokeBm"), 50)
    S["rain"] = rain("rainB", (1.0, 3.5, 0), (7, 4.5, 12), 2200, 0.5, 7, faded_emission("rainBm", (0.8, 0.85, 0.95), 0.16))
    for ob in S["rain"]["obs"]: set_alpha(ob, 1.0)
    S["bolt"] = Bolt("boltB", (-90, 220, 700), (-0.45, 0.15, S["seat_z"] + 1.5), 31, bolt_material(), radius=0.06, nbranch=8, blen=(60, 220))
    S["key"] = light("keyB", "SUN", (0, 0, 100), 1.7, (0.75, 0.82, 1.0), size=0.12, rot=(math.radians(50), 0, math.radians(35)))
    S["fill"] = light("fillB", "AREA", (-2.5, -6, 3), 220, (0.85, 0.9, 1.0), size=6, rot=(math.radians(70), 0, math.radians(-20)))
    S["strike"] = light("strikeB", "POINT", (0, -3, 8), 0.0, (0.8, 0.88, 1.0), size=1.5)
    S["cam"], S["tgt"] = camera(30); S["focus"] = empty("focusB"); dof(S["cam"], S["focus"], 5.0)
    return S

def bear_path(t):
    """Bear position/heading/gait over the shot: out of the trees across the creek to the trout, bonked, flees."""
    pts = [(B_BEAR0, (4.6, 7.0)), (B_GRAB - 0.3, (0.75, -0.55)), (B_BONK + 0.15, (0.80, -0.50)), (B_BONK + 2.2, (5.5, 6.5))]
    if t <= pts[0][0]: return Vector((*pts[0][1], 0)), 0.0, 0.0, False
    for (t0, a), (t1, b) in zip(pts[:-1], pts[1:]):
        if t <= t1:
            k = (t - t0) / (t1 - t0); k = k if b != a else 0.0
            pos = Vector(a).lerp(Vector(b), k); d = Vector(b) - Vector(a); moving = d.length > 0.2
            heading = math.atan2(d.x, -d.y) if moving else None
            return Vector((pos.x, pos.y, 0)), heading, (t - t0) * (9.0 if t0 > B_BONK else 6.0), moving
    return Vector((*pts[-1][1], 0)), math.atan2(1, -1), (t - B_BONK) * 9.0, True

def update_B(S, t):
    roy, bear, fz = S["roy"], S["bear"], S["fz"]
    inten, _ = strike_env(t, [B_STRIKE]); grow = smoothstep(B_STRIKE - 0.08, B_STRIKE, t)
    S["bolt"].set(grow, (0.12 if t < B_STRIKE else min(1, inten)) if B_STRIKE - 0.08 < t < B_STRIKE + 0.6 else 0.0, 1.0)
    S["flash"].outputs[0].default_value = 0.35 * inten; S["strike"].data.energy = 1e4 * inten
    S["creek"].node_tree.nodes["flow"].outputs[0].default_value = t * 0.8
    # Roy: sitting fishing -> jolt -> dazed, hair smoking -> stands, grabs the stick -> bonk -> holds the trout up
    sit = add_pose(SIT, {"r_sho": (-0.6, 0.15, 0), "r_elb": (-0.6, 0, 0)})
    P = strike_pose(sit, t, [B_STRIKE])
    ks = smoothstep(B_STAND0, B_STAND1, t); P = blend_pose(P, STAND, ks)
    swing = {**STAND, "r_sho": (-3.0, 0.2, 0), "r_elb": (-0.4, 0, 0), "neck": (0.15, 0, 0), "l_sho": (-0.5, -0.4, 0), "l_elb": (-0.8, 0, 0)}
    P = blend_pose(P, swing, smoothstep(B_STAND1 - 0.1, B_BONK - 0.25, t))
    P = blend_pose(P, {**swing, "r_sho": (-1.2, 0.2, 0), "spine": (-0.2, 0, 0)}, smoothstep(B_BONK - 0.25, B_BONK, t) * (1 - smoothstep(B_BONK + 0.3, B_BONK + 0.6, t)))
    P = blend_pose(P, {**STAND, "l_sho": (-2.9, -0.2, 0), "l_elb": (-0.2, 0, 0), "r_sho": (0.1, 0.3, 0), "neck": (0.25, 0, 0)}, smoothstep(B_WIN, B_WIN + 0.4, t))
    rot = lerp(math.pi / 2, math.pi / 2 - 0.9, smoothstep(B_STAND0, B_STAND1, t))   # faces the creek, then turns toward the bear / camera
    roy.pose(P, (-0.45, 0.15, 0), rot, lerp(0.17, 0.95, ks))
    roy.ground_snap(S["seat_z"] if ks < 0.5 else fz(-0.45, 0.15)); bpy.context.view_layer.update()
    roy.set_sheath(min(1.0, inten * 1.1)); S["sheath"].node_tree.nodes["flow"].outputs[0].default_value = t * 9.0
    for b in roy.brows: b.hide_render = True
    roy.hair.scale = (0.19, 0.18, 0.19)
    hat = roy.J["hat"]
    if t < B_STRIKE: hat.location = (0, 0, 0.11); hat.rotation_euler = (0, 0, 0)
    else:
        k = min(t - B_STRIKE, 0.9); hat.location = (0.3 * k, -0.2 * k, 0.11 + 1.6 * k - 2.6 * k * k); hat.rotation_euler = (2.0 * k, 0.5 * k, 3 * k)
        if t - B_STRIKE > 0.9: hat.location = (0, 0, -50)
    # rod: fishing until the strike, then it flies out of his hand into the grass
    S["rod"].hide_render = t > B_STRIKE + 0.25
    for ch in S["rod"].children: ch.hide_render = t > B_STRIKE + 0.25
    S["rod"].rotation_euler = (-0.9, 0, 0)
    bpy.context.view_layer.update()
    tip = S["rod"].matrix_world @ Vector((0, 0, -2.15)); S["line"].hide_render = t > B_STRIKE + 0.25
    for pnt, q in zip(S["line"].data.splines[0].points, (tip, Vector((tip.x + 0.1, tip.y, -0.38)))): pnt.co = (q.x, q.y, q.z, 1.0)
    # the bear
    pos, heading, phase, moving = bear_path(t)
    bonked = t > B_BONK
    if heading is None or (not moving and not bonked):   # standing at the trout: face Roy (and the camera), not away
        d = Vector((-0.45, 0.15)) - Vector((pos.x, pos.y)); heading = math.atan2(d.x, -d.y)
    sniff = 0.25 * math.sin(t * 9) if (not moving and not bonked) else 0.0
    shake = 0.5 * math.sin((t - B_BONK) * 30) * smoothstep(B_BONK, B_BONK + 0.05, t) * (1 - smoothstep(B_BONK + 0.25, B_BONK + 0.4, t))
    bear.pose((pos.x, pos.y, fz(pos.x, pos.y) + (0.18 if abs(pos.x - 2.4) < 1.2 else 0.0)), heading, phase if moving else 0.0, 0.45 if moving else 0.0, 0.04, -0.35 + sniff, shake)
    bear.root.hide_render = t < B_BEAR0
    for o in bear.root.children_recursive: o.hide_render = t < B_BEAR0
    # trout: on the rock beside him; the bear grabs it, drops it when bonked; Roy holds it up at the end
    bpy.context.view_layer.update(); fish = S["fish"]
    if t < B_GRAB: fish.location = (0.45, -0.35, fz(0.45, -0.35) + 0.05); fish.rotation_euler = (0, 0, 0.6)
    elif t < B_BONK + 0.1: fish.matrix_world = Matrix.Translation(bear.mouth.matrix_world.translation) @ Euler((0, 1.4, heading)).to_matrix().to_4x4()
    elif t < B_WIN: k = min(1, (t - B_BONK - 0.1) / 0.35); fish.location = bear.mouth.matrix_world.translation.lerp(Vector((0.6, -0.4, fz(0.6, -0.4) + 0.05)), k)
    else: fish.matrix_world = Matrix.Translation(roy.J["l_hand"].matrix_world.translation + Vector((0, 0, 0.12))) @ Euler((0.0, 0.0, 1.57)).to_matrix().to_4x4() @ Euler((1.5, 0, 0)).to_matrix().to_4x4()
    # stick: in the grass until he stands, then in his right hand
    if t < B_STAND1 - 0.2: S["stick"].location = (-0.1, -0.75, fz(-0.1, -0.75) + 0.03); S["stick"].rotation_euler = (1.57, 0, 0.4)
    else: S["stick"].matrix_world = roy.J["r_hand"].matrix_world @ Matrix.Translation((0, 0, -0.4))
    if not S["smoke"].parts:
        S["smoke"].add(B_STRIKE + 0.08, (-0.45, 0.15, S["seat_z"] + 1.1), 10, 0.35, 0.8, 0.13, 1.6, 71, 0.25, 0.55)
        for k in range(16): S["smoke"].add(B_STRIKE + 0.4 + k * 0.45, lambda: roy.world("head") + Vector((0, 0, 0.18)), 3, 0.06, 0.7, 0.06, 1.3, 80 + k, 0.2, 0.6)   # hair keeps smoking
    S["smoke"].update(t); rain_update(S["rain"], t)
    sh = Vector((n1(t * 31, 1), n1(t * 29, 2), n1(t * 27, 3))) * 0.06 * inten
    k = smoothstep(0, 8.3, t); kb = smoothstep(B_BEAR0, B_GRAB, t)
    S["cam"].location = vlerp((-1.6, -4.3, S["seat_z"] + 1.0), (-1.2, -4.9, S["seat_z"] + 1.2), kb) + sh
    S["tgt"].location = vlerp((0.0, 0.3, S["seat_z"] + 1.4), (0.6, 0.6, S["seat_z"] + 1.25), kb); S["focus"].location = Vector((0.1, -0.1, 1.0))

# ----------------------------------------------------------------------------- render setup + main
SHOTS = {"H": (build_H, update_H), "G": (build_G, update_G), "F": (build_F, update_F), "R": (build_R, update_R), "L": (build_L, update_L),
         "T": (build_T, update_T), "B": (build_B, update_B)}
STATE = {}

def on_frame(scene):
    f = scene.frame_current; SHOTS[SHOT][1](STATE["S"], f / FPS)

def setup_render(res, samples):
    sc = bpy.context.scene; sc.render.engine = "CYCLES"; c = sc.cycles
    c.device = "CPU"; c.samples = samples; c.use_adaptive_sampling = True; c.adaptive_threshold = 0.1; c.adaptive_min_samples = 4
    c.use_denoising = True; c.denoiser = "OPENIMAGEDENOISE"; c.denoising_input_passes = "RGB_ALBEDO_NORMAL"; c.denoising_use_gpu = False
    c.max_bounces = 4; c.diffuse_bounces = 2; c.glossy_bounces = 2; c.transmission_bounces = 2; c.volume_bounces = 0; c.transparent_max_bounces = 10
    c.caustics_reflective = False; c.caustics_refractive = False; c.blur_glossy = 1.0; c.sample_clamp_indirect = 10.0
    sc.render.use_persistent_data = True; sc.render.use_motion_blur = False
    sc.render.resolution_x = res; sc.render.resolution_y = res * 16 // 9; sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGB"; sc.render.image_settings.compression = 20
    sc.render.fps = FPS; sc.view_settings.view_transform = "AgX"
    try: sc.view_settings.look = "AgX - Medium High Contrast"
    except Exception: pass
    sc.view_settings.exposure = {"H": 0.6, "G": 0.6, "F": 0.9, "R": 1.0, "L": -0.6, "T": 0.6, "B": 0.6}[SHOT]
    sc.use_nodes = True; nt = sc.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    rl = nt.nodes.new("CompositorNodeRLayers"); gl = nt.nodes.new("CompositorNodeGlare"); comp = nt.nodes.new("CompositorNodeComposite")
    gl.glare_type = "BLOOM"
    for k, v in (("Threshold", 1.0), ("Strength", 0.35), ("Size", 0.7)):
        try: gl.inputs[k].default_value = v
        except Exception: pass
    nt.links.new(rl.outputs["Image"], gl.inputs["Image"]); nt.links.new(gl.outputs["Image"], comp.inputs["Image"])

def main():
    clear_scene(); STATE["S"] = SHOTS[SHOT][0](); setup_render(ARGS["res"], ARGS["samples"])
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

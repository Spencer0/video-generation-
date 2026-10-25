"""Procedural Blender scene: water in a plastic bag over a Bunsen flame.

Run headless:
  blender -b -noaudio -P pipeline/blender/scene_bag.py -- --shot C --start 0 --end 288 \
      --out videos/001-water-bag/build/frames/C [--res 720] [--samples 32] [--preview]

Everything is generated in code (no .blend file): bag + water meshes are
parametric, bubbles are a tiny deterministic simulation evaluated per frame,
flame flicker / camera moves / melt progress are all functions of the frame
number. No keyframes, so any frame range can be rendered independently and
in parallel across machines.

Shots (frame counts come from build/timeline.json beats):
  A  hook   : water bag, burner ignites mid-shot, slow push-in
  B  empty  : empty bag over the flame melts through
  C  boil   : water bag over flame, nucleation -> rolling boil, slow orbit
  D  hero   : close-up of the rolling boil at the bag bottom
"""
import bpy, bmesh, math, random, sys, os, time
from mathutils import Vector
from mathutils import noise as mnoise

# ----------------------------------------------------------------------------- args
def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    a = {"shot": "C", "start": 0, "end": 1, "out": "/tmp/frames", "res": 576, "samples": 24, "preview": False, "fps": 24}
    i = 0
    while i < len(argv):
        k = argv[i].lstrip("-")
        if k == "preview": a["preview"] = True; i += 1; continue
        v = argv[i + 1]; i += 2
        a[k] = type(a[k])(v) if k in a and not isinstance(a[k], bool) else v
    return a

ARGS = parse_args()
FLAGS = set(os.environ.get("SCENE_FLAGS", "").split(","))  # profiling toggles: nodof,nobubbles,noglare,nodenoise,thresh01,tb6
FPS = ARGS["fps"]
SHOT = ARGS["shot"].upper()
RNG = random.Random(1234)

# ----------------------------------------------------------------------------- helpers
def smoothstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0) if e1 != e0 else 0.0))
    return t * t * (3 - 2 * t)

def lerp(a, b, t): return a + (b - a) * t
def vlerp(a, b, t): return Vector(a).lerp(Vector(b), t)
def ease_in_out(t): return smoothstep(0, 1, t)
def n1(t, seed=0.0):  # smooth 1D noise in [-1, 1]
    return mnoise.noise(Vector((t, seed * 17.17, seed * 3.3))) * 2.0

def clear_scene():
    for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras):
        for x in list(coll): coll.remove(x)

def new_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    return m, nt, out

def metal(name, color=(0.35, 0.36, 0.38), rough=0.35):
    m, nt, out = new_mat(name)
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = (*color, 1); p.inputs["Metallic"].default_value = 1.0
    p.inputs["Roughness"].default_value = rough
    nt.links.new(p.outputs[0], out.inputs[0]); return m

def mesh_obj(name, verts, faces, mat=None, smooth=True, subsurf=0):
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    ob = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(ob)
    if smooth:
        for p in me.polygons: p.use_smooth = True
    if mat: me.materials.append(mat)
    if subsurf:
        md = ob.modifiers.new("subsurf", "SUBSURF"); md.levels = subsurf; md.render_levels = subsurf
    return ob

def add_cylinder(name, r, h, loc, mat, segs=48, rot=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=r, radius2=r, depth=h)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(ob)
    ob.location = loc; ob.rotation_euler = rot; me.materials.append(mat)
    for p in me.polygons: p.use_smooth = True
    md = ob.modifiers.new("bevel", "BEVEL"); md.width = min(r * 0.15, 0.002); md.segments = 2
    return ob

def add_box(name, dims, loc, mat, rot=(0, 0, 0), bevel=0.001):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(ob)
    ob.scale = dims; ob.location = loc; ob.rotation_euler = rot; me.materials.append(mat)
    if bevel:
        md = ob.modifiers.new("bevel", "BEVEL"); md.width = bevel; md.segments = 2
    return ob

# ----------------------------------------------------------------------------- scene constants (metres)
BAG_W = 0.165          # bag width
BAG_H = 0.205          # bag height
BAG_Z0 = 0.262         # bottom seam height above table
WATER_LEVEL = 0.56     # fraction of bag height filled
BURNER_TOP = 0.118
FLAME_H = 0.158        # tip just touches the bag bottom
FILLED = SHOT != "B"
SHOT_DUR = {"A": 104 / 24, "B": 96 / 24, "C": 168 / 24, "D": 168 / 24}  # nominal seconds; paths clamp beyond
T_SHOT = SHOT_DUR[SHOT]
N_RING = 64
N_V = 70

def bag_half_extents(v, filled):
    """Half-width a and half-depth b of the bag cross-section at height fraction v."""
    a = lerp(0.052, BAG_W / 2, smoothstep(0.0, 0.30, v))
    a -= 0.008 * smoothstep(0.86, 1.0, v)                 # pinched by the clamp
    if filled:
        lim = WATER_LEVEL * 1.22
        bulge = 0.041 * (math.sin(math.pi * min(v / lim, 1.0)) ** 0.9 if v < lim else 0.0)
    else:
        bulge = 0.010 * math.sin(math.pi * min(v, 1.0)) ** 0.8
    b = 0.0035 + bulge
    return a, b

def ring_point(u, v, filled, inset=1.0, crinkle=0.0):
    a, b = bag_half_extents(v, filled)
    a *= inset; b *= inset
    p = 2.5  # superellipse exponent -> pillowy
    c, s = math.cos(u), math.sin(u)
    x = a * math.copysign(abs(c) ** (2 / p), c)
    y = b * math.copysign(abs(s) ** (2 / p), s)
    z = BAG_Z0 + BAG_H * v
    if crinkle:
        # film above the water line is loose & crinkled
        w = smoothstep(WATER_LEVEL - 0.05, WATER_LEVEL + 0.12, v) * (1 - smoothstep(0.84, 0.97, v)) if filled else \
            (1 - smoothstep(0.84, 0.97, v)) * smoothstep(0.0, 0.08, v)
        nz = mnoise.noise(Vector((x * 55, y * 55, z * 55))) + 0.5 * mnoise.noise(Vector((x * 130 + 7, y * 130, z * 130)))
        y += nz * crinkle * w
        x += 0.4 * nz * crinkle * w * (1 if x > 0 else -1)
    return Vector((x, y, z))

def build_shell(v0, v1, filled, inset=1.0, crinkle=0.0, cap_bottom=True, cap_top=True, n_v=N_V):
    verts, faces = [], []
    rows = n_v
    for j in range(rows):
        v = lerp(v0, v1, j / (rows - 1))
        for i in range(N_RING):
            u = 2 * math.pi * i / N_RING
            verts.append(ring_point(u, v, filled, inset, crinkle))
    for j in range(rows - 1):
        for i in range(N_RING):
            a = j * N_RING + i; b = j * N_RING + (i + 1) % N_RING
            faces.append((a, b, b + N_RING, a + N_RING))
    if cap_bottom: faces.append(tuple(reversed(range(N_RING))))
    if cap_top: faces.append(tuple(range((rows - 1) * N_RING, rows * N_RING)))
    return verts, faces

# ----------------------------------------------------------------------------- materials
def bag_material():
    m, nt, out = new_mat("bag_plastic"); n = nt.nodes; L = nt.links
    if "simplebag" in FLAGS:
        fr = n.new("ShaderNodeFresnel"); tr = n.new("ShaderNodeBsdfTransparent"); gl = n.new("ShaderNodeBsdfGlossy"); gl.inputs["Roughness"].default_value = 0.1
        mix = n.new("ShaderNodeMixShader"); L.new(fr.outputs[0], mix.inputs[0]); L.new(tr.outputs[0], mix.inputs[1]); L.new(gl.outputs[0], mix.inputs[2]); L.new(mix.outputs[0], out.inputs[0])
        v1 = n.new("ShaderNodeValue"); v1.name = "soot"; v2 = n.new("ShaderNodeValue"); v2.name = "hole"; return m
    tc = n.new("ShaderNodeTexCoord")
    # base: fresnel mix of transparent and glossy -> thin LDPE film
    fr = n.new("ShaderNodeFresnel"); fr.inputs["IOR"].default_value = 1.51
    tr = n.new("ShaderNodeBsdfTransparent"); tr.inputs["Color"].default_value = (0.93, 0.95, 0.97, 1)
    gl = n.new("ShaderNodeBsdfGlossy"); gl.inputs["Roughness"].default_value = 0.10
    bump_tex = n.new("ShaderNodeTexNoise"); bump_tex.inputs["Scale"].default_value = 60; bump_tex.inputs["Detail"].default_value = 2
    bump = n.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.12
    L.new(tc.outputs["Object"], bump_tex.inputs["Vector"]); L.new(bump_tex.outputs["Fac"], bump.inputs["Height"]); L.new(bump.outputs[0], gl.inputs["Normal"])
    mix1 = n.new("ShaderNodeMixShader"); L.new(fr.outputs[0], mix1.inputs[0]); L.new(tr.outputs[0], mix1.inputs[1]); L.new(gl.outputs[0], mix1.inputs[2])
    # ziploc-style coloured seal strip near the top (generated z ~ 0.93..0.965)
    sep = n.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Generated"], sep.inputs[0])
    strip = n.new("ShaderNodeMapRange"); strip.inputs["From Min"].default_value = 0.925; strip.inputs["From Max"].default_value = 0.935
    L.new(sep.outputs["Z"], strip.inputs["Value"])
    strip2 = n.new("ShaderNodeMapRange"); strip2.inputs["From Min"].default_value = 0.968; strip2.inputs["From Max"].default_value = 0.958
    L.new(sep.outputs["Z"], strip2.inputs["Value"])
    smul = n.new("ShaderNodeMath"); smul.operation = "MULTIPLY"; L.new(strip.outputs[0], smul.inputs[0]); L.new(strip2.outputs[0], smul.inputs[1])
    seal = n.new("ShaderNodeBsdfTranslucent"); seal.inputs["Color"].default_value = (0.15, 0.45, 1.0, 1)
    mix2 = n.new("ShaderNodeMixShader"); L.new(smul.outputs[0], mix2.inputs[0]); L.new(mix1.outputs[0], mix2.inputs[1]); L.new(seal.outputs[0], mix2.inputs[2])
    # soot: radial mask from the bottom centre, intensity from a Value node we drive per frame
    dist = n.new("ShaderNodeVectorMath"); dist.operation = "DISTANCE"; dist.inputs[1].default_value = (0, 0, BAG_Z0 + 0.004)
    L.new(tc.outputs["Object"], dist.inputs[0])
    sootmask = n.new("ShaderNodeMapRange"); sootmask.inputs["From Min"].default_value = 0.012; sootmask.inputs["From Max"].default_value = 0.055
    sootmask.inputs["To Min"].default_value = 1.0; sootmask.inputs["To Max"].default_value = 0.0
    L.new(dist.outputs["Value"], sootmask.inputs["Value"])
    sootn = n.new("ShaderNodeTexNoise"); sootn.inputs["Scale"].default_value = 120; L.new(tc.outputs["Object"], sootn.inputs["Vector"])
    sootm = n.new("ShaderNodeMath"); sootm.operation = "MULTIPLY"; L.new(sootmask.outputs[0], sootm.inputs[0]); L.new(sootn.outputs["Fac"], sootm.inputs[1])
    soot_val = n.new("ShaderNodeValue"); soot_val.name = "soot"; soot_val.outputs[0].default_value = 0.0
    sootf = n.new("ShaderNodeMath"); sootf.operation = "MULTIPLY"; L.new(sootm.outputs[0], sootf.inputs[0]); L.new(soot_val.outputs[0], sootf.inputs[1])
    sootb = n.new("ShaderNodeBsdfDiffuse"); sootb.inputs["Color"].default_value = (0.02, 0.018, 0.015, 1)
    mix3 = n.new("ShaderNodeMixShader"); L.new(sootf.outputs[0], mix3.inputs[0]); L.new(mix2.outputs[0], mix3.inputs[1]); L.new(sootb.outputs[0], mix3.inputs[2])
    # melt hole (shot B): radius from Value node 'hole'. inside -> transparent, rim -> glowing bead + char
    hole_val = n.new("ShaderNodeValue"); hole_val.name = "hole"; hole_val.outputs[0].default_value = -1.0
    hn = n.new("ShaderNodeTexNoise"); hn.inputs["Scale"].default_value = 45; hn.inputs["Detail"].default_value = 3; L.new(tc.outputs["Object"], hn.inputs["Vector"])
    hdist = n.new("ShaderNodeMath"); hdist.operation = "SUBTRACT"; L.new(dist.outputs["Value"], hdist.inputs[0]); L.new(hole_val.outputs[0], hdist.inputs[1])
    hnoise = n.new("ShaderNodeMath"); hnoise.operation = "MULTIPLY_ADD"; hnoise.inputs[1].default_value = 0.012; hnoise.inputs[2].default_value = -0.006
    L.new(hn.outputs["Fac"], hnoise.inputs[0])
    hd = n.new("ShaderNodeMath"); hd.operation = "ADD"; L.new(hdist.outputs[0], hd.inputs[0]); L.new(hnoise.outputs[0], hd.inputs[1])  # noisy signed distance to rim
    inside = n.new("ShaderNodeMapRange"); inside.inputs["From Min"].default_value = -0.001; inside.inputs["From Max"].default_value = 0.0015
    L.new(hd.outputs[0], inside.inputs["Value"])                                   # 0 inside hole, 1 outside
    rim = n.new("ShaderNodeMapRange"); rim.inputs["From Min"].default_value = 0.0; rim.inputs["From Max"].default_value = 0.007
    rim.inputs["To Min"].default_value = 1.0; rim.inputs["To Max"].default_value = 0.0; L.new(hd.outputs[0], rim.inputs["Value"])
    char = n.new("ShaderNodeMapRange"); char.inputs["From Min"].default_value = 0.0; char.inputs["From Max"].default_value = 0.03
    char.inputs["To Min"].default_value = 0.9; char.inputs["To Max"].default_value = 0.0; L.new(hd.outputs[0], char.inputs["Value"])
    charb = n.new("ShaderNodeBsdfPrincipled"); charb.inputs["Base Color"].default_value = (0.09, 0.05, 0.02, 1); charb.inputs["Roughness"].default_value = 0.5
    glow = n.new("ShaderNodeEmission"); glow.inputs["Color"].default_value = (1.0, 0.45, 0.08, 1); glow.inputs["Strength"].default_value = 14
    mix4 = n.new("ShaderNodeMixShader"); L.new(char.outputs[0], mix4.inputs[0]); L.new(mix3.outputs[0], mix4.inputs[1]); L.new(charb.outputs[0], mix4.inputs[2])
    mix5 = n.new("ShaderNodeMixShader"); L.new(rim.outputs[0], mix5.inputs[0]); L.new(mix4.outputs[0], mix5.inputs[1]); L.new(glow.outputs[0], mix5.inputs[2])
    hole_tr = n.new("ShaderNodeBsdfTransparent")
    mix6 = n.new("ShaderNodeMixShader"); L.new(inside.outputs[0], mix6.inputs[0]); L.new(hole_tr.outputs[0], mix6.inputs[1]); L.new(mix5.outputs[0], mix6.inputs[2])
    L.new(mix6.outputs[0], out.inputs[0])
    return m

def water_material():
    m, nt, out = new_mat("water"); n = nt.nodes; L = nt.links
    g = n.new("ShaderNodeBsdfGlass"); g.inputs["IOR"].default_value = 1.333; g.inputs["Roughness"].default_value = 0.0
    g.inputs["Color"].default_value = (0.90, 0.97, 1.0, 1)
    L.new(g.outputs[0], out.inputs[0]); return m

def bubble_material():
    m, nt, out = new_mat("bubble"); n = nt.nodes; L = nt.links
    g = n.new("ShaderNodeBsdfGlass"); g.inputs["IOR"].default_value = 1.0 / 1.333; g.inputs["Roughness"].default_value = 0.0
    L.new(g.outputs[0], out.inputs[0]); return m

def flame_material(core=False):
    m, nt, out = new_mat("flame_core" if core else "flame_sheath"); n = nt.nodes; L = nt.links
    tc = n.new("ShaderNodeTexCoord"); sep = n.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Generated"], sep.inputs[0])
    ramp = n.new("ShaderNodeValToRGB"); cr = ramp.color_ramp
    if core:
        cr.elements[0].position = 0.0; cr.elements[0].color = (0.25, 0.45, 1.0, 1)
        cr.elements[1].position = 0.35; cr.elements[1].color = (1.0, 0.80, 0.42, 1)
        e = cr.elements.new(1.0); e.color = (1.0, 0.75, 0.3, 1)
    else:
        cr.elements[0].position = 0.0; cr.elements[0].color = (0.2, 0.35, 1.0, 1)
        cr.elements[1].position = 0.18; cr.elements[1].color = (1.0, 0.85, 0.45, 1)
        e = cr.elements.new(0.55); e.color = (1.0, 0.48, 0.08, 1)
        e = cr.elements.new(1.0); e.color = (1.0, 0.18, 0.02, 1)
    L.new(sep.outputs["Z"], ramp.inputs[0])
    em = n.new("ShaderNodeEmission"); L.new(ramp.outputs["Color"], em.inputs["Color"])
    strength = n.new("ShaderNodeMapRange"); strength.inputs["From Min"].default_value = 0.0; strength.inputs["From Max"].default_value = 1.0
    strength.inputs["To Min"].default_value = (13 if core else 12); strength.inputs["To Max"].default_value = (6 if core else 3)
    L.new(sep.outputs["Z"], strength.inputs["Value"]); L.new(strength.outputs[0], em.inputs["Strength"])
    # transparency: facing factor * animated noise * tip fade
    lw = n.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.6
    facing = n.new("ShaderNodeMath"); facing.operation = "POWER"; facing.inputs[1].default_value = (1.0 if core else 2.2)
    L.new(lw.outputs["Facing"], facing.inputs[0])
    tval = n.new("ShaderNodeValue"); tval.name = "time"; tval.outputs[0].default_value = 0.0
    nz = n.new("ShaderNodeTexNoise"); nz.noise_dimensions = "4D"; nz.inputs["Scale"].default_value = (6 if core else 9); nz.inputs["Detail"].default_value = 2.5
    nz.inputs["Roughness"].default_value = 0.45
    # stretch noise vertically so flame tongues flow upward: scale generated coords
    vm = n.new("ShaderNodeVectorMath"); vm.operation = "MULTIPLY"; vm.inputs[1].default_value = (1.0, 1.0, 0.35)
    # advect upward: subtract time from z
    adv = n.new("ShaderNodeVectorMath"); adv.operation = "SUBTRACT"
    tv = n.new("ShaderNodeCombineXYZ"); L.new(tval.outputs[0], tv.inputs["Z"])
    L.new(tc.outputs["Generated"], vm.inputs[0]); L.new(vm.outputs[0], adv.inputs[0]); L.new(tv.outputs[0], adv.inputs[1])
    L.new(adv.outputs[0], nz.inputs["Vector"]); L.new(tval.outputs[0], nz.inputs["W"])
    nmap = n.new("ShaderNodeMapRange"); nmap.inputs["From Min"].default_value = 0.30; nmap.inputs["From Max"].default_value = 0.75
    L.new(nz.outputs["Fac"], nmap.inputs["Value"])
    tip = n.new("ShaderNodeMapRange"); tip.inputs["From Min"].default_value = (0.75 if core else 0.62); tip.inputs["From Max"].default_value = 1.0
    tip.inputs["To Min"].default_value = 1.0; tip.inputs["To Max"].default_value = 0.0; L.new(sep.outputs["Z"], tip.inputs["Value"])
    base = n.new("ShaderNodeMapRange"); base.inputs["From Min"].default_value = 0.0; base.inputs["From Max"].default_value = 0.08
    L.new(sep.outputs["Z"], base.inputs["Value"])
    m1 = n.new("ShaderNodeMath"); m1.operation = "MULTIPLY"; L.new(facing.outputs[0], m1.inputs[0]); L.new(nmap.outputs[0], m1.inputs[1])
    m2 = n.new("ShaderNodeMath"); m2.operation = "MULTIPLY"; L.new(m1.outputs[0], m2.inputs[0]); L.new(tip.outputs[0], m2.inputs[1])
    m3 = n.new("ShaderNodeMath"); m3.operation = "MULTIPLY"; L.new(m2.outputs[0], m3.inputs[0]); L.new(base.outputs[0], m3.inputs[1])
    if core:
        m4 = n.new("ShaderNodeMath"); m4.operation = "MULTIPLY_ADD"; m4.inputs[1].default_value = 0.6; m4.inputs[2].default_value = 0.4
        L.new(m3.outputs[0], m4.inputs[0]); alpha = m4.outputs[0]
    else:
        alpha = m3.outputs[0]
    tr = n.new("ShaderNodeBsdfTransparent")
    mix = n.new("ShaderNodeMixShader"); L.new(alpha, mix.inputs[0]); L.new(tr.outputs[0], mix.inputs[1]); L.new(em.outputs[0], mix.inputs[2])
    L.new(mix.outputs[0], out.inputs[0])
    m.blend_method = "BLEND"
    return m

# ----------------------------------------------------------------------------- geometry
def build_flame_mesh(name, R_base, R_mid, height, mat, segs=40, rows=36):
    verts, faces = [], []
    for j in range(rows):
        h = j / (rows - 1)
        r = R_base * (1 - h) ** 0.35 + R_mid * (math.sin(math.pi * h) ** 1.5) * (1 - h) ** 0.25
        r = max(r * (1 - smoothstep(0.93, 1.0, h)) + 0.0004, 0.0004)
        for i in range(segs):
            u = 2 * math.pi * i / segs
            verts.append((r * math.cos(u), r * math.sin(u), h * height))
    for j in range(rows - 1):
        for i in range(segs):
            a = j * segs + i; b = j * segs + (i + 1) % segs
            faces.append((a, b, b + segs, a + segs))
    faces.append(tuple(range(segs - 1, -1, -1)))
    faces.append(tuple(range((rows - 1) * segs, rows * segs)))
    ob = mesh_obj(name, verts, faces, mat, smooth=True, subsurf=1)
    ob.location = (0, 0, BURNER_TOP)
    ob.visible_shadow = False
    return ob

def build_world():
    w = bpy.data.worlds["World"] if "World" in bpy.data.worlds else bpy.data.worlds.new("World")
    bpy.context.scene.world = w; w.use_nodes = True
    bg = w.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.004, 0.005, 0.008, 1); bg.inputs[1].default_value = 1.0

def build_set():
    S = {}
    build_world()
    # table: dark slate, subtle gloss so the flame reflects
    m, nt, out = new_mat("table"); p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = (0.03, 0.031, 0.036, 1); p.inputs["Roughness"].default_value = 0.22
    tn = nt.nodes.new("ShaderNodeTexNoise"); tn.inputs["Scale"].default_value = 9; tn.inputs["Detail"].default_value = 8
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.04
    nt.links.new(tn.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs[0], p.inputs["Normal"])
    nt.links.new(p.outputs[0], out.inputs[0])
    S["table"] = add_box("table", (3, 3, 0.02), (0, 0, -0.01), m, bevel=0)
    # backdrop: dark, far, catches the blue rim light
    m, nt, out = new_mat("backdrop"); p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = (0.012, 0.014, 0.022, 1); p.inputs["Roughness"].default_value = 0.85
    nt.links.new(p.outputs[0], out.inputs[0])
    S["backdrop"] = add_box("backdrop", (6, 0.02, 4), (0, 1.9, 1.2), m, bevel=0)
    steel = metal("steel", (0.42, 0.43, 0.45), 0.3)
    dark = metal("dark_metal", (0.12, 0.12, 0.13), 0.45)
    brass = metal("brass", (0.6, 0.45, 0.2), 0.35)
    # Bunsen burner
    add_cylinder("burner_base", 0.052, 0.012, (0, 0, 0.006), dark, segs=64)
    add_cylinder("burner_tube", 0.0115, BURNER_TOP - 0.012, (0, 0, (BURNER_TOP + 0.012) / 2), steel)
    add_cylinder("burner_collar", 0.016, 0.022, (0, 0, 0.040), brass)
    add_cylinder("burner_inlet", 0.004, 0.05, (0.0, -0.03, 0.02), brass, rot=(math.radians(90), 0, 0))
    # lab stand: base plate + rod + arm + clamp jaws pinching the bag top
    add_box("stand_base", (0.17, 0.11, 0.012), (-0.25, 0.08, 0.006), dark, bevel=0.002)
    add_cylinder("stand_rod", 0.0065, 0.62, (-0.25, 0.08, 0.31), steel)
    clamp_z = BAG_Z0 + BAG_H - 0.006
    add_cylinder("stand_arm", 0.005, 0.30, (-0.10, 0.04, clamp_z), steel, rot=(0, math.radians(90), math.radians(-15)))
    add_box("clamp_boss", (0.03, 0.03, 0.045), (-0.25, 0.08, clamp_z), dark, bevel=0.003)
    for sgn in (-1, 1):
        add_box(f"jaw{sgn}", (0.09, 0.012, 0.022), (0.0, sgn * 0.0095, clamp_z), dark, bevel=0.002)
    add_box("jaw_screw", (0.014, 0.05, 0.014), (0.05, 0.0, clamp_z + 0.004), brass, bevel=0.002)
    # bag + water
    bag_mat = bag_material()
    bv, bf = build_shell(0.0, 1.0, FILLED, crinkle=(0.004 if FILLED else 0.0045))
    S["bag"] = mesh_obj("bag", bv, bf, bag_mat, subsurf=(1 if "lowsub" in FLAGS else 2))
    if FILLED:
        wv, wf = build_shell(0.0, WATER_LEVEL, True, inset=0.975, n_v=44)
        S["water"] = mesh_obj("water", wv, wf, water_material(), subsurf=(1 if "lowsub" in FLAGS else 2))
    # melt shape key (shot B): film near the bottom shrinks back up toward the heat
    if SHOT == "B":
        bag = S["bag"]; bag.shape_key_add(name="Basis")
        sk = bag.shape_key_add(name="melt"); sk.value = 0.0
        c = Vector((0, 0, BAG_Z0))
        for i, v in enumerate(bag.data.vertices):
            d = (v.co - c).length; w = (1 - smoothstep(0.0, 0.11, d)) ** 1.5
            if w > 0:
                nzv = mnoise.noise(v.co * 90)
                sk.data[i].co = v.co + Vector((v.co.x * -0.35 * w, nzv * 0.01 * w, 0.045 * w + 0.004 * nzv))
        S["melt_key"] = sk
    # flame: sheath + core
    S["flame"] = build_flame_mesh("flame", 0.0105, 0.0175, FLAME_H, flame_material(False))
    S["flame_core"] = build_flame_mesh("flame_core", 0.0075, 0.009, FLAME_H * 0.62, flame_material(True), rows=24)
    if "noflame" in FLAGS:
        S["flame"].scale = (0.001,0.001,0.001); S["flame_core"].scale = (0.001,0.001,0.001)
    # lights
    def light(name, typ, loc, energy, color, size=1.0, rot=(0, 0, 0)):
        ld = bpy.data.lights.new(name, typ); ld.energy = energy; ld.color = color
        if typ == "AREA": ld.size = size
        if typ == "POINT": ld.shadow_soft_size = size
        ob = bpy.data.objects.new(name, ld); bpy.context.collection.objects.link(ob); ob.location = loc; ob.rotation_euler = rot
        return ob
    S["flame_light"] = light("flame_light", "POINT", (0, 0, BURNER_TOP + 0.07), 14.0, (1.0, 0.56, 0.22), size=0.03)
    S["flame_light2"] = light("flame_light2", "POINT", (0, 0, BURNER_TOP + 0.13), 7.0, (1.0, 0.5, 0.18), size=0.04)
    S["key"] = light("key", "AREA", (0.55, -0.6, 0.75), 10.0, (1.0, 0.9, 0.8), size=0.9, rot=(math.radians(48), 0, math.radians(42)))
    S["rim"] = light("rim", "AREA", (-0.6, 0.55, 0.6), 40.0, (0.35, 0.55, 1.0), size=0.5, rot=(math.radians(-55), 0, math.radians(-135)))
    S["fill"] = light("fill", "AREA", (-0.5, -0.7, 0.3), 2.5, (0.6, 0.75, 1.0), size=1.5, rot=(math.radians(70), 0, math.radians(-35)))
    if "fewlights" in FLAGS:
        for k in ("fill", "flame_light2"): S[k].hide_render = True
    # bubble pool
    S["bubbles"] = []
    bmat = bubble_material()
    if FILLED and "nobubbles" not in FLAGS:
        for i in range(110):
            bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
            me = bpy.data.meshes.new(f"bubble{i}"); bm.to_mesh(me); bm.free(); me.materials.append(bmat)
            for p in me.polygons: p.use_smooth = True
            ob = bpy.data.objects.new(f"bubble{i}", me); bpy.context.collection.objects.link(ob)
            ob.hide_render = True; ob.visible_shadow = False
            S["bubbles"].append(ob)
    # camera
    cd = bpy.data.cameras.new("cam"); cam = bpy.data.objects.new("cam", cd); bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    tgt = bpy.data.objects.new("cam_target", None); bpy.context.collection.objects.link(tgt)
    con = cam.constraints.new("TRACK_TO"); con.target = tgt; con.track_axis = "TRACK_NEGATIVE_Z"; con.up_axis = "UP_Y"
    cd.dof.use_dof = "nodof" not in FLAGS; cd.dof.focus_object = tgt
    S["cam"], S["cam_target"] = cam, tgt
    return S

# ----------------------------------------------------------------------------- bubble simulation
class Bubbles:
    """Deterministic boil: bubbles nucleate on the bag bottom near the flame,
    grow while attached, detach, rise with a wobble and pop at the surface."""
    def __init__(self, rate_fn, t0=-3.0, t1=20.0, seed=7):
        rng = random.Random(seed)
        self.items = []
        t = t0
        while t < t1:
            r = rate_fn(t)
            t += min(rng.expovariate(max(r, 1e-6)), 0.05)
            if rate_fn(t) <= 0 or rng.random() > min(1.0, rate_fn(t) / max(r, 1e-6)): continue
            x = max(-0.045, min(0.045, rng.gauss(0, 0.017)))
            v0 = rng.uniform(0.02, 0.13)
            side = rng.choice((-1, 1))
            rmax = rng.uniform(0.0012, 0.0036) * (1.0 + 0.6 * smoothstep(5, 20, rate_fn(t)))
            self.items.append(dict(t=t, x=x, v0=v0, side=side, r=rmax, grow=rng.uniform(0.25, 0.7),
                                   speed=rng.uniform(0.10, 0.17), wob=rng.uniform(0, 6.28), wf=rng.uniform(6, 11)))
        self.z_surface = BAG_Z0 + BAG_H * WATER_LEVEL

    def state(self, b, t):
        """-> (pos, radius) or None if not alive at time t."""
        dt = t - b["t"]
        if dt < 0: return None
        a, bb = bag_half_extents(b["v0"], True)
        z0 = BAG_Z0 + BAG_H * b["v0"]
        if dt < b["grow"]:
            r = b["r"] * (0.15 + 0.85 * (dt / b["grow"]) ** 0.6)
            y = b["side"] * (bb * 0.975 - r)
            return Vector((b["x"], y, z0 + r * 0.4)), r
        tr = dt - b["grow"]
        z = z0 + b["speed"] * tr + 0.5 * 0.25 * tr * tr
        r = b["r"]
        if z > self.z_surface - r * 0.5:
            # pop: shrink over ~70 ms
            over = (z - (self.z_surface - r * 0.5)) / b["speed"]
            if over > 0.07: return None
            r *= max(0.0, 1 - over / 0.07); z = self.z_surface - b["r"] * 0.5
        v = (z - BAG_Z0) / BAG_H
        a2, b2 = bag_half_extents(v, True)
        x = b["x"] + 0.006 * math.sin(tr * b["wf"] + b["wob"]) * min(1, tr * 2)
        x = max(-a2 * 0.9 + r, min(a2 * 0.9 - r, x))
        ymax = max(b2 * 0.975 - r, 0.0)
        y = b["side"] * ymax * (0.9 - 0.3 * min(1, tr * 1.5))
        return Vector((x, y, z)), r

def boil_rate_C(t):   # bubbles per second over the shot-C clock (t in seconds from shot start)
    return 0.0 if t < 1.1 else 3.0 * smoothstep(1.1, 2.8, t) + 24 * smoothstep(2.8, 5.0, t) + 21 * smoothstep(5.0, 7.0, t)

def boil_rate_D(t): return 48.0

# ----------------------------------------------------------------------------- per-frame update
def shot_update(S, frame, sim):
    t = frame / FPS
    cam, tgt = S["cam"], S["cam_target"]
    flame_on, flame_scale, ignite = True, 1.0, 1.0
    bag_mat = S["bag"].data.materials[0].node_tree.nodes
    soot = 0.0; hole = -1.0; melt = 0.0
    bag_center = Vector((0, 0, BAG_Z0 + BAG_H * 0.42))
    bottom = Vector((0, 0, BAG_Z0 + 0.03))
    if SHOT == "A":
        k = ease_in_out(min(t / T_SHOT, 1.0))
        cam.location = vlerp((0.30, -0.56, 0.42), (0.24, -0.46, 0.38), k)
        tgt.location = vlerp(bag_center + Vector((0, 0, -0.02)), bag_center - Vector((0, 0, 0.05)), k)
        cam.data.lens = lerp(30, 33, k); cam.data.dof.aperture_fstop = 4.0
        t_ign = 2.45
        if t < t_ign: flame_on = False
        else:
            ignite = smoothstep(0, 0.22, t - t_ign)
            flame_scale = lerp(0.0, 1.0, ignite) * (1 + 0.35 * (1 - smoothstep(0.2, 0.6, t - t_ign)))
    elif SHOT == "B":
        k = ease_in_out(min(t / T_SHOT, 1.0))
        cam.location = vlerp((0.26, -0.50, 0.36), (0.22, -0.44, 0.34), k)
        tgt.location = vlerp(bottom + Vector((0, 0, 0.05)), bottom + Vector((0, 0, 0.04)), k)
        cam.data.lens = 36; cam.data.dof.aperture_fstop = 4.0
        m0, m1 = 0.8, 1.8
        melt = smoothstep(m0, m1 + 0.3, t) ** 0.8
        hole = -1.0 if t < m0 + 0.1 else lerp(0.0, 0.075, smoothstep(m0 + 0.1, m1 + 0.1, t) ** 0.9)
        S["melt_key"].value = melt
    elif SHOT == "C":
        k = min(t / T_SHOT, 1.0)
        ang = math.radians(lerp(-28, 22, k))
        rad = lerp(0.42, 0.52, ease_in_out(k)); h = lerp(0.30, 0.40, ease_in_out(k))
        cam.location = Vector((rad * math.sin(ang), -rad * math.cos(ang), h))
        tgt.location = vlerp(bottom + Vector((0, 0, 0.01)), bag_center - Vector((0, 0, 0.03)), ease_in_out(k))
        cam.data.lens = lerp(42, 34, ease_in_out(k)); cam.data.dof.aperture_fstop = 2.8
        soot = 0.55 * smoothstep(2.0, 11.0, t)
    elif SHOT == "D":
        k = ease_in_out(min(t / T_SHOT, 1.0))
        cam.location = vlerp((0.16, -0.30, 0.30), (0.20, -0.27, 0.315), k)
        tgt.location = vlerp(bottom + Vector((0.0, 0, 0.0)), bottom + Vector((0.0, 0, 0.015)), k)
        cam.data.lens = 48; cam.data.dof.aperture_fstop = 2.2
        soot = 0.55
    # flame flicker
    fl, fc = S["flame"], S["flame_core"]
    for ob in (fl, fc):
        ob.hide_render = not flame_on
    if flame_on and "noflame" not in FLAGS:
        sz = flame_scale * (1 + 0.10 * n1(t * 2.6, 1) + 0.05 * n1(t * 7.0, 2))
        sxy = flame_scale * (1 + 0.06 * n1(t * 3.1, 3))
        fl.scale = (sxy, sxy, sz); fc.scale = (sxy, sxy, sz * (1 + 0.06 * n1(t * 9, 4)))
        lean = (math.radians(3.0 * n1(t * 1.7, 5)), math.radians(3.0 * n1(t * 1.9, 6)), 0)
        fl.rotation_euler = lean; fc.rotation_euler = lean
        for ob in (fl, fc):
            ob.data.materials[0].node_tree.nodes["time"].outputs[0].default_value = t * 1.6
    e = (1 + 0.28 * n1(t * 4.0, 8) + 0.1 * n1(t * 13, 9)) * (ignite if flame_on else 0.0)
    S["flame_light"].data.energy = 14.0 * e; S["flame_light2"].data.energy = 7.0 * e
    S["flame_light"].hide_render = not flame_on; S["flame_light2"].hide_render = not flame_on
    bag_mat["soot"].outputs[0].default_value = soot
    bag_mat["hole"].outputs[0].default_value = hole
    # bubbles
    if sim is not None:
        pool = S["bubbles"]; used = 0
        for b in sim.items:
            if b["t"] > t or b["t"] < t - 3.0: continue
            st = sim.state(b, t)
            if st is None or used >= len(pool): continue
            pos, r = st
            ob = pool[used]; used += 1
            ob.hide_render = False; ob.location = pos; ob.scale = (r, r, r)
        for ob in pool[used:]:
            ob.hide_render = True

# ----------------------------------------------------------------------------- render setup
def setup_render(res, samples):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"; c = sc.cycles
    c.device = "CPU"; c.samples = samples; c.use_adaptive_sampling = True; c.adaptive_threshold = 0.1; c.adaptive_min_samples = 4
    c.use_denoising = "nodenoise" not in FLAGS; c.denoiser = "OPENIMAGEDENOISE"; c.denoising_input_passes = "RGB_ALBEDO_NORMAL"
    c.denoising_use_gpu = False; c.denoising_prefilter = "ACCURATE"
    c.max_bounces = 6; c.diffuse_bounces = 2; c.glossy_bounces = 2; c.transmission_bounces = 6; c.volume_bounces = 0; c.transparent_max_bounces = 10
    c.caustics_reflective = False; c.caustics_refractive = False; c.blur_glossy = 1.5
    c.sample_clamp_indirect = 8.0
    c.use_light_tree = True
    sc.render.use_persistent_data = True
    sc.render.resolution_x = res; sc.render.resolution_y = res * 16 // 9; sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGB"; sc.render.image_settings.compression = 20
    sc.render.film_transparent = False
    sc.render.fps = FPS
    sc.view_settings.view_transform = "AgX"
    try: sc.view_settings.look = "AgX - Medium High Contrast"
    except Exception: pass
    sc.view_settings.exposure = -0.2
    # compositor bloom around the flame
    sc.use_nodes = "noglare" not in FLAGS; nt = sc.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    rl = nt.nodes.new("CompositorNodeRLayers"); gl = nt.nodes.new("CompositorNodeGlare"); comp = nt.nodes.new("CompositorNodeComposite")
    gl.glare_type = "BLOOM"
    for k, v in (("Threshold", 1.2), ("Strength", 0.22), ("Size", 0.62), ("Saturation", 0.9)):
        try: gl.inputs[k].default_value = v
        except Exception: pass
    try: gl.quality = "HIGH"
    except Exception: pass
    nt.links.new(rl.outputs["Image"], gl.inputs["Image"]); nt.links.new(gl.outputs["Image"], comp.inputs["Image"])

def main():
    clear_scene()
    S = build_set()
    setup_render(ARGS["res"], ARGS["samples"])
    sim = None
    if SHOT == "C": sim = Bubbles(boil_rate_C, t0=0.0, t1=max(ARGS["end"] / FPS, T_SHOT) + 1)
    if SHOT == "D": sim = Bubbles(boil_rate_D, t0=-3.0, t1=max(ARGS["end"] / FPS, T_SHOT) + 1, seed=11)
    if SHOT == "A": pass
    os.makedirs(ARGS["out"], exist_ok=True)
    sc = bpy.context.scene
    frames = [ARGS["start"]] if ARGS["preview"] else range(ARGS["start"], ARGS["end"])
    for f in frames:
        path = os.path.join(ARGS["out"], f"{SHOT}_{f:04d}.png")
        if os.path.exists(path) and not ARGS["preview"]:
            continue
        sc.frame_set(f)
        shot_update(S, f, sim)
        sc.render.filepath = path
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        print(f"FRAME {SHOT} {f} {time.time() - t0:.1f}s", flush=True)

main()

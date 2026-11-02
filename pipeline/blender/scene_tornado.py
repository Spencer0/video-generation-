"""Procedural Blender scene: a toy-diorama farm being eaten by a tornado (video 006).

Run headless:
  blender -b -noaudio -P pipeline/blender/scene_tornado.py -- --shot A --start 0 --end 150 \
      --out videos/006-tornado/build/frames/A [--res 720] [--samples 16] [--fps 30] [--preview] [--tracks-only]

Look: bright, saturated toy diorama (tilt-shift DoF, plastic-ish Principled materials), a pale stormy sky,
a bumpy cloud deck, a wispy grey condensation funnel and a brown dust skirt. Everything kinematic:
  funnel  = polar grid (rings x segments) whose vertices are recomputed per frame from a radius profile
            R(z) and a wandering axis; the shader scrolls noise around the funnel's UV for the spin
  debris  = parented primitives (blocky cow, trampoline, pickup, gnome, mailbox, sofa, chair, planks, tires,
            stop sign) orbiting on a Rankine-style vortex: inner items faster (angular rate ~ 1/r^2), tumbling
  tube    = shot R: a translucent horizontal vortex tube with orbiting leaves that stands up (rotation about X)
Shots (nominal lengths in SHOT_DUR; A is periodic so the assembler can wrap it and the loop beat lands on frame 0):
  A  hero wide: farm, funnel, debris; period 5 s (debris orbits = integer cycles)
  R  roll + tilt: tube rolls for ~3.8 s, then stands up into the cloud
  N  squeeze: funnel and debris radii shrink to ~1/3, angular speed rises as 1/s^2 (angular momentum)
  C  cow close-up: camera rides the cow's orbit, funnel wheeling behind
Tracks: for every frame in --start..--end the screen position (1080x1920 px) and depth of named objects
(cow, trampoline, gnome, truck) are written to <out>/../../tracks/<shot>.json so the overlay can stick
labels to them (render_overlays.py injects window.TRACK).
"""
import bpy, bmesh, math, random, sys, os, time, json
from mathutils import Vector, Euler
from mathutils import noise as mnoise
from bpy_extras.object_utils import world_to_camera_view

def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    a = {"shot": "A", "start": 0, "end": 1, "out": "/tmp/frames", "res": 720, "samples": 16, "preview": False, "fps": 30, "tracks-only": False}
    i = 0
    while i < len(argv):
        k = argv[i].lstrip("-")
        if k in ("preview", "tracks-only"): a[k] = True; i += 1; continue
        v = argv[i + 1]; i += 2
        a[k] = type(a[k])(v) if k in a and not isinstance(a[k], bool) else v
    return a

ARGS = parse_args(); FPS = ARGS["fps"]; SHOT = ARGS["shot"].upper()
SHOT_DUR = {"A": 5.0, "R": 7.0, "N": 5.0, "C": 2.5}
T_SHOT = SHOT_DUR[SHOT]; T_PERIOD = 5.0          # debris orbit period (A, C, N share it)
H_CLOUD = 12.0                                     # cloud deck height
FLAGS = set(os.environ.get("SCENE_FLAGS", "").split(","))

def smoothstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0) if e1 != e0 else 0.0)); return t * t * (3 - 2 * t)
def lerp(a, b, t): return a + (b - a) * t
def n1(t, seed=0.0): return mnoise.noise(Vector((t, seed * 17.17, seed * 3.3))) * 2.0

def clear_scene():
    for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras, bpy.data.curves):
        for x in list(coll): coll.remove(x)
def new_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    return m, nt, nt.nodes.new("ShaderNodeOutputMaterial")
def set_in(node, key, val):
    try: node.inputs[key].default_value = val
    except Exception: pass
def toy(name, color, rough=0.45, coat=0.35, metallic=0.0):
    """Plastic toy look: saturated base colour, medium roughness, a little clear coat."""
    m, nt, out = new_mat(name); p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = (*color, 1); p.inputs["Roughness"].default_value = rough; p.inputs["Metallic"].default_value = metallic
    set_in(p, "Coat Weight", coat); set_in(p, "Coat Roughness", 0.1)
    nt.links.new(p.outputs[0], out.inputs[0]); return m
def link_obj(name, data):
    ob = bpy.data.objects.new(name, data); bpy.context.collection.objects.link(ob); return ob
def mesh_obj(name, bm, mat, smooth=True):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if smooth:
        for p in me.polygons: p.use_smooth = True
    ob = link_obj(name, me)
    if mat: me.materials.append(mat)
    return ob
def box(name, dims, loc, mat, parent=None, rot=(0, 0, 0), bevel=0.0):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * dims[0], v.co.y * dims[1], v.co.z * dims[2]))
    ob = mesh_obj(name, bm, mat, smooth=False); ob.location = loc; ob.rotation_euler = rot
    if bevel: md = ob.modifiers.new("bevel", "BEVEL"); md.width = bevel; md.segments = 2
    if parent: ob.parent = parent
    return ob
def cyl(name, r, h, loc, mat, parent=None, rot=(0, 0, 0), segs=24, r2=None):
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=r, radius2=r if r2 is None else r2, depth=h)
    ob = mesh_obj(name, bm, mat); ob.location = loc; ob.rotation_euler = rot
    if parent: ob.parent = parent
    return ob
def ball(name, r, loc, mat, parent=None, segs=24):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=segs // 2, radius=r)
    ob = mesh_obj(name, bm, mat); ob.location = loc
    if parent: ob.parent = parent
    return ob
def torus(name, R, r, loc, mat, parent=None, rot=(0, 0, 0)):
    bm = bmesh.new(); segs, rings = 32, 12; verts = []
    for i in range(segs):
        a = 2 * math.pi * i / segs; ring = []
        for j in range(rings):
            b = 2 * math.pi * j / rings; ring.append(bm.verts.new(((R + r * math.cos(b)) * math.cos(a), (R + r * math.cos(b)) * math.sin(a), r * math.sin(b))))
        verts.append(ring)
    for i in range(segs):
        for j in range(rings):
            bm.faces.new((verts[i][j], verts[(i + 1) % segs][j], verts[(i + 1) % segs][(j + 1) % rings], verts[i][(j + 1) % rings]))
    ob = mesh_obj(name, bm, mat); ob.location = loc; ob.rotation_euler = rot
    if parent: ob.parent = parent
    return ob
def empty(name, loc=(0, 0, 0), parent=None):
    ob = link_obj(name, None); ob.location = loc
    if parent: ob.parent = parent
    return ob

# ----------------------------------------------------------------------------- materials
def cow_hide():
    """White with black patches: thresholded noise in object space."""
    m, nt, out = new_mat("cow_hide"); n = nt.nodes; L = nt.links
    p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Roughness"].default_value = 0.5; set_in(p, "Coat Weight", 0.3)
    tc = n.new("ShaderNodeTexCoord"); nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 2.2; nz.inputs["Detail"].default_value = 2.0; nz.inputs["Roughness"].default_value = 0.4
    L.new(tc.outputs["Object"], nz.inputs["Vector"])
    ramp = n.new("ShaderNodeValToRGB"); ramp.color_ramp.interpolation = "CONSTANT"
    ramp.color_ramp.elements[0].color = (0.95, 0.95, 0.95, 1); ramp.color_ramp.elements[1].position = 0.56; ramp.color_ramp.elements[1].color = (0.02, 0.02, 0.025, 1)
    L.new(nz.outputs["Fac"], ramp.inputs[0]); L.new(ramp.outputs[0], p.inputs["Base Color"]); L.new(p.outputs[0], out.inputs[0]); return m

def field_material():
    """Grass/wheat patchwork: low-frequency noise between two greens and a straw yellow, plus a dirt road along X."""
    m, nt, out = new_mat("field"); n = nt.nodes; L = nt.links
    p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Roughness"].default_value = 0.9
    tc = n.new("ShaderNodeTexCoord")
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.08; nz.inputs["Detail"].default_value = 3.0; L.new(tc.outputs["Object"], nz.inputs["Vector"])
    ramp = n.new("ShaderNodeValToRGB"); e = ramp.color_ramp.elements
    e[0].position = 0.35; e[0].color = (0.22, 0.45, 0.12, 1); e[1].position = 0.65; e[1].color = (0.75, 0.62, 0.22, 1)
    mid = ramp.color_ramp.elements.new(0.5); mid.color = (0.40, 0.55, 0.16, 1)
    L.new(nz.outputs["Fac"], ramp.inputs[0])
    fine = n.new("ShaderNodeTexNoise"); fine.inputs["Scale"].default_value = 3.0; fine.inputs["Detail"].default_value = 4.0; L.new(tc.outputs["Object"], fine.inputs["Vector"])
    fr = n.new("ShaderNodeMapRange"); fr.inputs["From Min"].default_value = 0.3; fr.inputs["From Max"].default_value = 0.7; fr.inputs["To Min"].default_value = 0.8; fr.inputs["To Max"].default_value = 1.15
    L.new(fine.outputs["Fac"], fr.inputs["Value"])
    mix = n.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"; mix.inputs[0].default_value = 1.0
    L.new(ramp.outputs[0], mix.inputs[6]); L.new(fr.outputs[0], mix.inputs[7])
    # road: |y + 7| < 1.1 -> dirt
    sep = n.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Object"], sep.inputs[0])
    ad = n.new("ShaderNodeMath"); ad.operation = "ADD"; ad.inputs[1].default_value = 7.0; L.new(sep.outputs["Y"], ad.inputs[0])
    ab = n.new("ShaderNodeMath"); ab.operation = "ABSOLUTE"; L.new(ad.outputs[0], ab.inputs[0])
    lt = n.new("ShaderNodeMath"); lt.operation = "LESS_THAN"; lt.inputs[1].default_value = 1.1; L.new(ab.outputs[0], lt.inputs[0])
    road = n.new("ShaderNodeMix"); road.data_type = "RGBA"; road.inputs[7].default_value = (0.42, 0.33, 0.22, 1)
    L.new(lt.outputs[0], road.inputs[0]); L.new(mix.outputs[2], road.inputs[6])
    L.new(road.outputs[2], p.inputs["Base Color"]); L.new(p.outputs[0], out.inputs[0]); return m

def funnel_material(name, base_alpha=1.0, spin_dir=1.0):
    """Wispy condensation funnel: grey Principled mixed with Transparent. Alpha = (opaque centre, see-through edge) x
    streaky noise that scrolls around the UV (u = angle, v = height). The scroll offset is a Value node set per frame."""
    m, nt, out = new_mat(name); n = nt.nodes; L = nt.links
    p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Roughness"].default_value = 1.0; set_in(p, "Specular IOR Level", 0.2)
    tc = n.new("ShaderNodeTexCoord")
    off = n.new("ShaderNodeValue"); off.name = "scroll"; off.outputs[0].default_value = 0.0
    comb = n.new("ShaderNodeCombineXYZ"); L.new(off.outputs[0], comb.inputs["X"])
    mp = n.new("ShaderNodeMapping"); mp.vector_type = "POINT"; mp.inputs["Scale"].default_value = (3.0, 1.0, 1.0); L.new(tc.outputs["UV"], mp.inputs["Vector"]); L.new(comb.outputs[0], mp.inputs["Location"])
    # tilt the streaks into a spiral: rotate UV by ~20 degrees
    mp.inputs["Rotation"].default_value = (0, 0, math.radians(18) * spin_dir)
    st = n.new("ShaderNodeTexNoise"); st.inputs["Scale"].default_value = 1.0; st.inputs["Detail"].default_value = 5.0; st.inputs["Roughness"].default_value = 0.55
    sc = n.new("ShaderNodeMapping"); sc.inputs["Scale"].default_value = (2.0, 9.0, 1.0); L.new(mp.outputs[0], sc.inputs["Vector"]); L.new(sc.outputs[0], st.inputs["Vector"])   # long vertical streaks
    sr = n.new("ShaderNodeMapRange"); sr.inputs["From Min"].default_value = 0.35; sr.inputs["From Max"].default_value = 0.65; sr.inputs["To Min"].default_value = 0.6; sr.inputs["To Max"].default_value = 1.4; sr.clamp = True
    L.new(st.outputs["Fac"], sr.inputs["Value"])
    lw = n.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.5
    edge = n.new("ShaderNodeMath"); edge.operation = "MULTIPLY_ADD"; edge.inputs[1].default_value = -1.0; edge.inputs[2].default_value = 1.5; edge.use_clamp = True
    L.new(lw.outputs["Facing"], edge.inputs[0])
    alpha = n.new("ShaderNodeMath"); alpha.operation = "MULTIPLY"; alpha.use_clamp = True; L.new(edge.outputs[0], alpha.inputs[0]); L.new(sr.outputs[0], alpha.inputs[1])
    alpha2 = n.new("ShaderNodeMath"); alpha2.operation = "MULTIPLY"; alpha2.inputs[1].default_value = base_alpha; alpha2.use_clamp = True; L.new(alpha.outputs[0], alpha2.inputs[0])
    # colour: pale grey, darker in the streak troughs
    cr = n.new("ShaderNodeMapRange"); cr.inputs["From Min"].default_value = 0.6; cr.inputs["From Max"].default_value = 1.4; cr.inputs["To Min"].default_value = 0.22; cr.inputs["To Max"].default_value = 0.68
    L.new(sr.outputs[0], cr.inputs["Value"])
    col = n.new("ShaderNodeCombineColor"); L.new(cr.outputs[0], col.inputs[0]); L.new(cr.outputs[0], col.inputs[1])
    cb = n.new("ShaderNodeMath"); cb.operation = "MULTIPLY"; cb.inputs[1].default_value = 1.06; L.new(cr.outputs[0], cb.inputs[0]); L.new(cb.outputs[0], col.inputs[2])   # a hair of blue
    L.new(col.outputs[0], p.inputs["Base Color"])
    tr = n.new("ShaderNodeBsdfTransparent"); mix = n.new("ShaderNodeMixShader")
    L.new(alpha2.outputs[0], mix.inputs[0]); L.new(tr.outputs[0], mix.inputs[1]); L.new(p.outputs[0], mix.inputs[2]); L.new(mix.outputs[0], out.inputs[0])
    m.blend_method = "BLEND"
    return m

def dust_material():
    """Brown dust skirt: transparent with a scrolling noise alpha, dense at the bottom, fading up."""
    m, nt, out = new_mat("dust"); n = nt.nodes; L = nt.links
    p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Base Color"].default_value = (0.42, 0.30, 0.18, 1); p.inputs["Roughness"].default_value = 1.0; set_in(p, "Specular IOR Level", 0.0)
    tc = n.new("ShaderNodeTexCoord"); off = n.new("ShaderNodeValue"); off.name = "scroll"; off.outputs[0].default_value = 0.0
    comb = n.new("ShaderNodeCombineXYZ"); L.new(off.outputs[0], comb.inputs["X"])
    mp = n.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (4.0, 2.0, 1.0); L.new(tc.outputs["UV"], mp.inputs["Vector"]); L.new(comb.outputs[0], mp.inputs["Location"])
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 1.0; nz.inputs["Detail"].default_value = 4.0; L.new(mp.outputs[0], nz.inputs["Vector"])
    sep = n.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["UV"], sep.inputs[0])
    fade = n.new("ShaderNodeMapRange"); fade.inputs["From Min"].default_value = 0.1; fade.inputs["From Max"].default_value = 0.85; fade.inputs["To Min"].default_value = 1.0; fade.inputs["To Max"].default_value = 0.0; fade.clamp = True
    L.new(sep.outputs["Y"], fade.inputs["Value"])
    nr = n.new("ShaderNodeMapRange"); nr.inputs["From Min"].default_value = 0.35; nr.inputs["From Max"].default_value = 0.7; nr.inputs["To Min"].default_value = 0.0; nr.inputs["To Max"].default_value = 1.4; nr.clamp = True
    L.new(nz.outputs["Fac"], nr.inputs["Value"])
    a = n.new("ShaderNodeMath"); a.operation = "MULTIPLY"; a.use_clamp = True; L.new(nr.outputs[0], a.inputs[0]); L.new(fade.outputs[0], a.inputs[1])
    lw = n.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.4
    edge = n.new("ShaderNodeMath"); edge.operation = "MULTIPLY_ADD"; edge.inputs[1].default_value = -1.2; edge.inputs[2].default_value = 1.1; edge.use_clamp = True; L.new(lw.outputs["Facing"], edge.inputs[0])
    a2 = n.new("ShaderNodeMath"); a2.operation = "MULTIPLY"; a2.use_clamp = True; L.new(a.outputs[0], a2.inputs[0]); L.new(edge.outputs[0], a2.inputs[1])
    tr = n.new("ShaderNodeBsdfTransparent"); mix = n.new("ShaderNodeMixShader")
    L.new(a2.outputs[0], mix.inputs[0]); L.new(tr.outputs[0], mix.inputs[1]); L.new(p.outputs[0], mix.inputs[2]); L.new(mix.outputs[0], out.inputs[0])
    return m

def cloud_material():
    """Cloud deck underside: grey-blue, a little emissive so it never goes black, lumpy via noise colour."""
    m, nt, out = new_mat("cloud"); n = nt.nodes; L = nt.links
    p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Roughness"].default_value = 1.0; set_in(p, "Specular IOR Level", 0.0)
    tc = n.new("ShaderNodeTexCoord"); nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.12; nz.inputs["Detail"].default_value = 5.0; L.new(tc.outputs["Object"], nz.inputs["Vector"])
    ramp = n.new("ShaderNodeValToRGB"); e = ramp.color_ramp.elements; e[0].position = 0.3; e[0].color = (0.36, 0.38, 0.43, 1); e[1].position = 0.7; e[1].color = (0.72, 0.74, 0.78, 1)
    L.new(nz.outputs["Fac"], ramp.inputs[0]); L.new(ramp.outputs[0], p.inputs["Base Color"])
    em = n.new("ShaderNodeEmission"); L.new(ramp.outputs[0], em.inputs["Color"]); em.inputs["Strength"].default_value = 0.35
    add = n.new("ShaderNodeAddShader"); L.new(p.outputs[0], add.inputs[0]); L.new(em.outputs[0], add.inputs[1]); L.new(add.outputs[0], out.inputs[0]); return m

# ----------------------------------------------------------------------------- geometry
def polar_grid_uv(name, mat, na=56, nz=48):
    """Open tube of nz+1 rings x na segments with UVs u = angle, v = ring index / nz. Vertex order: ring-major."""
    bm = bmesh.new(); rings = [[bm.verts.new((0, 0, 0)) for _ in range(na)] for _ in range(nz + 1)]
    uv = bm.loops.layers.uv.new("UVMap")
    for j in range(nz):
        for i in range(na):
            f = bm.faces.new((rings[j][i], rings[j][(i + 1) % na], rings[j + 1][(i + 1) % na], rings[j + 1][i]))
            us = [i / na, (i + 1) / na, (i + 1) / na, i / na]; vs = [j / nz, j / nz, (j + 1) / nz, (j + 1) / nz]
            if i == na - 1: us = [i / na, 1.0, 1.0, i / na]
            for lp, u, v in zip(f.loops, us, vs): lp[uv].uv = (u, v)
    ob = mesh_obj(name, bm, mat); ob["na"] = na; ob["nz"] = nz; return ob

def set_rings(ob, fn):
    """fn(j, i, a) -> (x, y, z) for ring j (0 = bottom) segment i at angle a."""
    me = ob.data; na, nz = ob["na"], ob["nz"]; k = 0
    for j in range(nz + 1):
        for i in range(na):
            me.vertices[k].co = fn(j, i, 2 * math.pi * i / na); k += 1
    me.update()

def grid_plane(name, size, segs, mat, zfn=None):
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=segs, y_segments=segs, size=size)
    if zfn:
        for v in bm.verts: v.co.z = zfn(v.co.x, v.co.y)
    return mesh_obj(name, bm, mat, smooth=True)

# ----------------------------------------------------------------------------- props
def build_cow(name="cow"):
    hide = cow_hide(); pink = toy("pink", (0.95, 0.55, 0.62)); blk = toy("black", (0.03, 0.03, 0.035)); horn = toy("horn", (0.92, 0.85, 0.65))
    root = empty(name)
    box("body", (1.3, 0.62, 0.68), (0, 0, 0), hide, root, bevel=0.03)
    box("head", (0.5, 0.46, 0.46), (0.78, 0, 0.18), hide, root, bevel=0.03)
    box("muzzle", (0.18, 0.36, 0.22), (1.06, 0, 0.06), pink, root)
    box("nostril1", (0.04, 0.06, 0.05), (1.15, 0.09, 0.08), blk, root); box("nostril2", (0.04, 0.06, 0.05), (1.15, -0.09, 0.08), blk, root)
    box("eye1", (0.06, 0.07, 0.07), (0.98, 0.17, 0.3), blk, root); box("eye2", (0.06, 0.07, 0.07), (0.98, -0.17, 0.3), blk, root)
    box("ear1", (0.1, 0.16, 0.06), (0.75, 0.3, 0.36), hide, root, rot=(0.4, 0, 0)); box("ear2", (0.1, 0.16, 0.06), (0.75, -0.3, 0.36), hide, root, rot=(-0.4, 0, 0))
    cyl("horn1", 0.035, 0.18, (0.78, 0.14, 0.46), horn, root, rot=(-0.5, 0, 0), segs=8); cyl("horn2", 0.035, 0.18, (0.78, -0.14, 0.46), horn, root, rot=(0.5, 0, 0), segs=8)
    for k, (x, y) in enumerate([(0.45, 0.2), (0.45, -0.2), (-0.45, 0.2), (-0.45, -0.2)]): box(f"leg{k}", (0.17, 0.17, 0.5), (x, y, -0.55), hide, root)
    box("udder", (0.3, 0.3, 0.14), (-0.2, 0, -0.38), pink, root, bevel=0.03)
    box("tail", (0.5, 0.05, 0.05), (-0.85, 0, 0.2), hide, root, rot=(0, 0.5, 0))
    return root
def build_trampoline():
    root = empty("trampoline"); pad = toy("pad", (0.08, 0.1, 0.14), rough=0.8); blue = toy("tramp_blue", (0.1, 0.35, 0.85)); st = toy("steel", (0.75, 0.75, 0.78), rough=0.3, metallic=0.8)
    torus("rim", 1.0, 0.07, (0, 0, 0), blue, root); cyl("mat", 0.92, 0.03, (0, 0, 0), pad, root, segs=40)
    for k in range(6):
        a = 2 * math.pi * k / 6; cyl(f"leg{k}", 0.035, 0.7, (0.95 * math.cos(a), 0.95 * math.sin(a), -0.38), st, root, segs=8)
    return root
def build_truck():
    root = empty("truck"); red = toy("truck_red", (0.85, 0.12, 0.1)); glass = toy("glass", (0.6, 0.8, 0.9), rough=0.1); blk = toy("tire", (0.05, 0.05, 0.05), rough=0.8); chrome = toy("chrome", (0.8, 0.8, 0.8), rough=0.2, metallic=1.0)
    box("bed", (1.9, 0.9, 0.4), (-0.35, 0, 0.1), red, root, bevel=0.04); box("cab", (0.8, 0.86, 0.5), (0.5, 0, 0.55), red, root, bevel=0.04)
    box("win", (0.5, 0.8, 0.3), (0.55, 0, 0.6), glass, root); box("hood", (0.55, 0.86, 0.35), (1.1, 0, 0.1), red, root, bevel=0.04)
    box("bumper", (0.1, 0.9, 0.12), (1.4, 0, -0.08), chrome, root)
    for k, (x, y) in enumerate([(0.8, 0.5), (0.8, -0.5), (-0.7, 0.5), (-0.7, -0.5)]): cyl(f"wheel{k}", 0.26, 0.2, (x, y, -0.18), blk, root, rot=(math.pi / 2, 0, 0), segs=20)
    return root
def build_gnome():
    root = empty("gnome"); red = toy("gnome_red", (0.85, 0.1, 0.08)); skin = toy("skin", (0.95, 0.72, 0.58)); blue = toy("gnome_blue", (0.15, 0.3, 0.75)); white = toy("beard", (0.95, 0.95, 0.95), rough=0.8); brown = toy("boots", (0.3, 0.18, 0.1))
    cyl("body", 0.3, 0.55, (0, 0, 0.0), blue, root, r2=0.22); ball("head", 0.22, (0, 0, 0.42), skin, root); ball("beard", 0.2, (0.08, 0, 0.3), white, root)
    cyl("hat", 0.24, 0.6, (0, 0, 0.78), red, root, r2=0.0); ball("nose", 0.06, (0.22, 0, 0.44), skin, root); box("boots", (0.35, 0.4, 0.12), (0.04, 0, -0.32), brown, root)
    return root
def build_mailbox():
    root = empty("mailbox"); grey = toy("mb_grey", (0.45, 0.47, 0.5), rough=0.3, metallic=0.6); wood = toy("post", (0.45, 0.3, 0.16)); red = toy("flag", (0.9, 0.1, 0.1))
    box("box", (0.6, 0.32, 0.2), (0, 0, 0.3), grey, root); cyl("top", 0.16, 0.6, (0, 0, 0.4), grey, root, rot=(0, math.pi / 2, 0)); box("post", (0.1, 0.1, 0.9), (0, 0, -0.25), wood, root)
    box("flag", (0.2, 0.02, 0.06), (0.1, 0.18, 0.5), red, root)
    return root
def build_sofa():
    root = empty("sofa"); m = toy("sofa", (0.85, 0.55, 0.12), rough=0.8, coat=0.0)
    box("seat", (1.6, 0.8, 0.4), (0, 0, 0), m, root, bevel=0.06); box("back", (1.6, 0.25, 0.55), (0, 0.3, 0.42), m, root, bevel=0.06)
    box("arm1", (0.25, 0.8, 0.6), (0.7, 0, 0.1), m, root, bevel=0.06); box("arm2", (0.25, 0.8, 0.6), (-0.7, 0, 0.1), m, root, bevel=0.06)
    return root
def build_chair():
    root = empty("chair"); wh = toy("chair_white", (0.92, 0.92, 0.9), rough=0.3); st = toy("chair_str", (0.1, 0.5, 0.3))
    box("seat", (0.7, 0.7, 0.05), (0, 0, 0), st, root); box("back", (0.7, 0.05, 0.6), (0, 0.33, 0.35), st, root)
    for k, (x, y) in enumerate([(0.3, 0.3), (0.3, -0.3), (-0.3, 0.3), (-0.3, -0.3)]): cyl(f"leg{k}", 0.025, 0.6, (x, y, -0.3), wh, root, segs=8)
    cyl("frame", 0.025, 0.7, (0.33, 0.33, 0.35), wh, root, segs=8); cyl("frame2", 0.025, 0.7, (-0.33, 0.33, 0.35), wh, root, segs=8)
    return root
def build_stop_sign():
    root = empty("stopsign"); red = toy("sign_red", (0.8, 0.08, 0.08), rough=0.3); st = toy("pole", (0.6, 0.6, 0.62), rough=0.3, metallic=0.7); wh = toy("sign_white", (0.95, 0.95, 0.95))
    cyl("sign", 0.45, 0.04, (0, 0, 0.9), red, root, rot=(math.pi / 2, 0, 0), segs=8); cyl("ring", 0.4, 0.05, (0, -0.005, 0.9), wh, root, rot=(math.pi / 2, 0, 0), segs=8)
    cyl("sign_face", 0.33, 0.06, (0, -0.01, 0.9), red, root, rot=(math.pi / 2, 0, 0), segs=8)
    cyl("pole", 0.035, 1.8, (0, 0, 0), st, root, segs=10)
    return root
def build_plank(k):
    root = empty(f"plank{k}"); m = toy(f"plank{k}", (0.55 + 0.1 * (k % 3), 0.36, 0.18), rough=0.8, coat=0.0)
    box("p", (1.6 + 0.4 * (k % 2), 0.22, 0.05), (0, 0, 0), m, root); return root
def build_tire(k):
    root = empty(f"tire{k}"); torus("t", 0.38, 0.14, (0, 0, 0), toy(f"tire{k}", (0.05, 0.05, 0.05), rough=0.85, coat=0.0), root); return root
def build_leaf(k, mat):
    root = empty(f"leaf{k}"); box("l", (0.5, 0.3, 0.015), (0, 0, 0), mat, root); return root

def build_farm(S):
    wh = toy("house_white", (0.95, 0.93, 0.88)); roof = toy("roof", (0.35, 0.2, 0.18), rough=0.7); barn = toy("barn_red", (0.75, 0.12, 0.1)); trim = toy("trim", (0.95, 0.95, 0.95))
    silo = toy("silo", (0.78, 0.8, 0.82), rough=0.35, metallic=0.4); trunk = toy("trunk", (0.4, 0.26, 0.14)); leaf = toy("leaves", (0.18, 0.5, 0.14)); fence = toy("fence", (0.9, 0.88, 0.8))
    def house(x, y, w, d, h, rotz, m, mroof):
        r = empty(f"house_{x}_{y}", (x, y, 0)); r.rotation_euler = (0, 0, rotz)
        box("walls", (w, d, h), (0, 0, h / 2), m, r)
        bm = bmesh.new(); hw, hd, hh = w / 2 + 0.15, d / 2 + 0.15, h * 0.55   # gable roof prism along X
        v = [bm.verts.new(p) for p in [(-hw, -hd, h), (hw, -hd, h), (hw, hd, h), (-hw, hd, h), (-hw, 0, h + hh), (hw, 0, h + hh)]]
        bm.faces.new((v[0], v[1], v[5], v[4])); bm.faces.new((v[3], v[2], v[5], v[4])); bm.faces.new((v[0], v[3], v[4])); bm.faces.new((v[1], v[2], v[5])); bm.faces.new((v[0], v[1], v[2], v[3]))
        ro = mesh_obj("roof", bm, mroof, smooth=False); ro.parent = r
        return r
    house(7.5, 6.0, 3.2, 2.6, 2.2, 0.15, wh, roof)
    b = house(-8.0, 7.5, 4.5, 3.4, 3.0, -0.2, barn, trim); box("door", (0.05, 1.4, 1.8), (2.3, 0, 0.9), trim, b)
    cyl("silo", 1.1, 6.0, (-11.5, 9.0, 3.0), silo, segs=28); ball("silo_cap", 1.1, (-11.5, 9.0, 6.0), silo)
    rng = random.Random(4)
    for k in range(14):
        x, y = rng.uniform(-22, 22), rng.uniform(5, 26)
        if math.hypot(x, y) < 5.5: continue
        h = rng.uniform(1.2, 2.2); cyl(f"trunk{k}", 0.12, h, (x, y, h / 2), trunk, segs=8); ball(f"crown{k}", rng.uniform(0.8, 1.3), (x, y, h + 0.5), leaf, segs=16)
    for k in range(-9, 10):   # fence along the road (y = -5.6)
        cyl(f"post{k}", 0.05, 0.8, (k * 2.2, -5.6, 0.4), fence, segs=6)
    box("rail", (42, 0.05, 0.08), (0, -5.6, 0.62), fence); box("rail2", (42, 0.05, 0.08), (0, -5.6, 0.32), fence)
    # a few props still on the ground near the house: a tractor tire, planks (storm damage)
    tr = build_tire(9); tr.location = (5.0, 2.5, 0.2); tr.rotation_euler = (math.pi / 2, 0, 0.6)

# ----------------------------------------------------------------------------- set
def build_world():
    w = bpy.data.worlds["World"] if "World" in bpy.data.worlds else bpy.data.worlds.new("World")
    bpy.context.scene.world = w; w.use_nodes = True; nt = w.node_tree; n = nt.nodes; L = nt.links
    bg = n["Background"]; tc = n.new("ShaderNodeTexCoord"); sep = n.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Generated"], sep.inputs[0])
    # Generated for the world = direction; Z in -1..1. Bright warm horizon, pale blue-green zenith, darker below.
    ramp = n.new("ShaderNodeValToRGB"); e = ramp.color_ramp.elements
    e[0].position = 0.42; e[0].color = (0.55, 0.52, 0.45, 1); e[1].position = 0.52; e[1].color = (1.0, 0.92, 0.72, 1)
    z = ramp.color_ramp.elements.new(0.75); z.color = (0.55, 0.66, 0.72, 1); top = ramp.color_ramp.elements.new(1.0); top.color = (0.42, 0.50, 0.58, 1)
    mr = n.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = -1.0; mr.inputs["From Max"].default_value = 1.0; L.new(sep.outputs["Z"], mr.inputs["Value"])
    L.new(mr.outputs[0], ramp.inputs[0]); L.new(ramp.outputs[0], bg.inputs[0]); bg.inputs[1].default_value = 1.0

def light(name, typ, loc, energy, color, size=1.0, target=(0, 0, 4), angle=None):
    ld = bpy.data.lights.new(name, typ); ld.energy = energy; ld.color = color
    if typ == "AREA": ld.size = size
    if typ == "SUN" and angle is not None: ld.angle = angle
    ob = link_obj(name, ld); ob.location = loc; ob.visible_camera = False
    d = Vector(target) - Vector(loc); ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler(); return ob

def build_set():
    S = {}; build_world(); rng = random.Random(6)
    S["ground"] = grid_plane("ground", 140, 2, field_material())
    if SHOT != "R":
        # cloud deck: lumpy underside, lowered wall cloud around the funnel
        def cz(x, y):
            r = math.hypot(x, y); lumps = 1.3 * mnoise.noise(Vector((x * 0.09, y * 0.09, 0.7))) + 0.5 * mnoise.noise(Vector((x * 0.25, y * 0.25, 2.1)))
            return H_CLOUD + lumps - 2.2 * math.exp(-(r / 7.0) ** 2)
        S["cloud"] = grid_plane("cloud", 100, 110, cloud_material(), cz); S["cloud"].visible_shadow = False
    else:
        def cz(x, y): return H_CLOUD + 1.0 + 1.3 * mnoise.noise(Vector((x * 0.09, y * 0.09, 0.7)))
        S["cloud"] = grid_plane("cloud", 70, 60, cloud_material(), cz); S["cloud"].visible_shadow = False
    build_farm(S)
    # funnel (two shells) + dust skirt
    S["fm"] = funnel_material("funnel_in", 1.0, 1.0); S["fm2"] = funnel_material("funnel_out", 0.55, 1.0)
    S["funnel"] = polar_grid_uv("funnel", S["fm"]); S["funnel2"] = polar_grid_uv("funnel2", S["fm2"], na=48, nz=36)
    if "noshell2" in FLAGS: S["funnel2"].hide_render = True
    S["dm"] = dust_material(); S["dust"] = polar_grid_uv("dust", S["dm"], na=48, nz=14)
    for o in (S["funnel"], S["funnel2"], S["dust"]): o.visible_shadow = False
    # debris: (builder, orbit radius, base height, height amplitude, orbit cycles per period, tumble cycles, phase)
    specs = [("cow", build_cow, 2.4, 4.0, 0.5, 2, (1, 2, 0), -math.pi / 2), ("trampoline", build_trampoline, 3.6, 6.0, 0.8, 1, (1, 0, 1), 2.1),
             ("truck", build_truck, 3.9, 2.6, 0.5, 1, (0, 1, 1), 4.0), ("gnome", build_gnome, 1.9, 7.2, 0.7, 3, (2, 0, 1), 1.0),
             ("mailbox", build_mailbox, 3.0, 5.1, 0.6, 2, (1, 1, 0), 3.3), ("sofa", build_sofa, 4.4, 3.4, 0.5, 1, (0, 1, 0), 5.2),
             ("chair", build_chair, 2.7, 8.3, 0.6, 2, (1, 2, 1), 0.7), ("stopsign", build_stop_sign, 3.3, 7.6, 0.7, 2, (2, 0, 1), 2.6)]
    for k in range(6): specs.append((f"plank{k}", lambda k=k: build_plank(k), 2.2 + 0.5 * (k % 3), 1.8 + 1.5 * k, 0.5, 2 if k % 2 else 3, (1 + k % 2, 2 - k % 2, 1), 0.9 * k))
    for k in range(3): specs.append((f"tire{k}", lambda k=k: build_tire(k), 3.1 + 0.4 * k, 2.4 + 2.6 * k, 0.6, 2, (1, 1 + k % 2, 0), 1.7 * k + 0.4))
    S["debris"] = []
    for name, fn, r, z, az, n, tum, ph in specs:
        ob = fn(); sc = 1.8 if name == "cow" else 1.5; ob.scale = (sc, sc, sc); S["debris"].append({"ob": ob, "name": name, "r": r, "z": z, "az": az, "n": n, "tum": tum, "ph": ph})
    if SHOT == "R":
        for d in S["debris"]: d["ob"].hide_render = True; [setattr(c, "hide_render", True) for c in d["ob"].children_recursive]
        for o in (S["funnel"], S["funnel2"], S["dust"]): o.hide_render = True
        # vortex tube along local Y with leaves orbiting it
        S["tm"] = funnel_material("tube", 1.0, 1.0); S["tube"] = polar_grid_uv("tube", S["tm"], na=48, nz=40); S["tube"].visible_shadow = False
        lm = toy("leaf", (0.62, 0.66, 0.14), rough=0.8, coat=0.0); S["leaves"] = []
        rng2 = random.Random(11)
        for k in range(40):
            lf = build_leaf(k, lm); lf.parent = S["tube"]; S["leaves"].append({"ob": lf, "y": rng2.uniform(-6.2, 6.2), "r": rng2.uniform(1.35, 1.9), "ph": rng2.uniform(0, 2 * math.pi), "spin": rng2.uniform(2, 5)})
    # lights: warm low sun from front-left (rakes the funnel), big soft sky fill from above-right
    S["sun"] = light("sun", "SUN", (-30, -40, 28), 5.0, (1.0, 0.93, 0.82), target=(0, 0, 4), angle=math.radians(3))
    S["fill"] = light("fill", "AREA", (25, -30, 20), 2500.0, (0.85, 0.92, 1.0), size=30.0, target=(0, 0, 5))
    cam_d = bpy.data.cameras.new("cam"); cam = link_obj("cam", cam_d); cam_d.sensor_fit = "VERTICAL"; cam_d.sensor_height = 36.0
    tgt = empty("cam_target"); cam.constraints.new("TRACK_TO").target = tgt
    cam.constraints[0].track_axis = "TRACK_NEGATIVE_Z"; cam.constraints[0].up_axis = "UP_Y"
    cam_d.dof.use_dof = "nodof" not in FLAGS; cam_d.dof.aperture_fstop = 2.8
    focus = empty("focus"); focus.location = (0, 0, 4); cam_d.dof.focus_object = focus
    S["cam"], S["cam_target"], S["focus"] = cam, tgt, focus
    bpy.context.scene.camera = cam
    return S

# ----------------------------------------------------------------------------- kinematics
def funnel_radius(z, s=1.0, H=H_CLOUD):
    """Condensation funnel profile: narrow near the ground, flaring into the wall cloud. s scales the radii (shot N)."""
    u = max(0.0, min(1.0, z / H)); return s * (0.5 + 2.9 * u ** 1.7 + 0.5 * u ** 8)

def axis_offset(z, t, amp=1.0, H=H_CLOUD):
    """Where the funnel axis is at height z: the base wanders on a slow circle (period T_PERIOD), the top stays put."""
    k = max(0.0, 1 - z / H) ** 1.6; ph = 2 * math.pi * t / T_PERIOD
    return Vector((amp * 0.9 * math.sin(ph) + 0.25 * math.sin(2 * ph + 1.0) * k, amp * 0.9 * math.cos(ph) * 0.8 + 0.2 * math.sin(3 * ph) * k, 0)) * k

def update_funnel(S, t, s=1.0):
    H = H_CLOUD + 0.8
    def fn_in(j, i, a):
        z = H * j / S["funnel"]["nz"]; o = axis_offset(z, t)
        r = funnel_radius(z, s) * (1 + 0.07 * mnoise.noise(Vector((math.cos(a) * 1.3, math.sin(a) * 1.3, z * 0.5 - t * 1.5))) )
        return (o.x + r * math.cos(a), o.y + r * math.sin(a), z)
    set_rings(S["funnel"], fn_in)
    def fn_out(j, i, a):
        z = H * j / S["funnel2"]["nz"]; o = axis_offset(z, t)
        r = funnel_radius(z, s) * 1.28 * (1 + 0.1 * mnoise.noise(Vector((math.cos(a) * 1.1 + 5, math.sin(a) * 1.1, z * 0.4 + t * 0.9))))
        return (o.x + r * math.cos(a), o.y + r * math.sin(a), z)
    set_rings(S["funnel2"], fn_out)
    def fn_dust(j, i, a):
        u = j / S["dust"]["nz"]; z = 2.4 * u * s ** 0.5; o = axis_offset(0, t)
        r = s * (3.4 * (1 - u) ** 0.5 + 0.9) * (1 + 0.12 * mnoise.noise(Vector((math.cos(a) * 2 + 9, math.sin(a) * 2, u * 3 - t * 2))))
        return (o.x + r * math.cos(a), o.y + r * math.sin(a), z)
    set_rings(S["dust"], fn_dust)
    # spin: scroll the streak noise around the UV. Integer cycles per period keep shot A seamless.
    S["fm"].node_tree.nodes["scroll"].outputs[0].default_value = -2.0 * t / T_PERIOD * 1.0
    S["fm2"].node_tree.nodes["scroll"].outputs[0].default_value = -1.0 * t / T_PERIOD * 1.0
    S["dm"].node_tree.nodes["scroll"].outputs[0].default_value = 2.0 * t / T_PERIOD * 1.0

def squeeze_scale(t):
    """Shot N: funnel radius scale over the shot (fat wedge -> rope)."""
    return lerp(1.55, 0.5, smoothstep(0.6, 4.4, t))

def orbit_angle(d, t):
    """Debris azimuth. Shot A/C: integer cycles per period. Shot N: angular rate ~ 1/s^2 (angular momentum conserved)."""
    w0 = 2 * math.pi * d["n"] / T_PERIOD
    if SHOT != "N": return d["ph"] + w0 * t
    th, dt, tt = d["ph"], 1 / 240.0, 0.0   # quadrature from the shot start, deterministic per frame
    while tt < t: th += w0 / squeeze_scale(tt) ** 2 * dt; tt += dt
    return th

def update_debris(S, t, s=1.0):
    base = axis_offset(0, t)
    for d in S["debris"]:
        a = orbit_angle(d, t); r = d["r"] * s; zz = d["z"] + d["az"] * math.sin(2 * math.pi * (2 if d["n"] > 1 else 1) * t / T_PERIOD + d["ph"])
        o = axis_offset(zz, t)
        ob = d["ob"]; ob.location = (o.x + r * math.cos(a), o.y + r * math.sin(a), zz)
        tx, ty, tz = d["tum"]; w = 2 * math.pi / T_PERIOD * (1 if SHOT != "N" else 1 / s ** 1.5)
        tph = 0.0 if d["name"] == "cow" else d["ph"]   # the cow starts upright and broadside (frame 0 is the cover)
        ob.rotation_euler = (tx * w * t + tph, ty * w * t + 0.5 * tph, tz * w * t + a + math.pi / 2)   # tangential heading + tumble
        if SHOT == "C" and d["name"] == "cow":   # close-up: keep the cow's flank and face toward the riding camera, a gentle roll only
            ob.rotation_euler = (0.35 * math.sin(2 * math.pi * t / T_PERIOD), 0.25 * math.sin(4 * math.pi * t / T_PERIOD + 1.0), a + 0.9)   # 3/4 view: face turned toward the camera

def update_tube(S, t):
    """Shot R: horizontal vortex tube along local Y, rolling; from T_STAND it rotates about X into the vertical and rises."""
    T_STAND0, T_STAND1 = 3.9, 6.3
    k = smoothstep(T_STAND0, T_STAND1, t)
    tube = S["tube"]; L = 13.0
    def fn(j, i, a):
        u = j / tube["nz"]; y = (u - 0.5) * L
        r = 1.35 * (1 + 0.08 * math.sin(u * 9 + t * 2.0) + 0.06 * mnoise.noise(Vector((math.cos(a), math.sin(a), u * 4 - t)))) * (0.75 + 0.25 * math.sin(math.pi * u) ** 0.4)
        r *= lerp(1.0, 0.55 + 0.8 * u, k)   # as it stands up it tapers toward the ground end
        return (r * math.cos(a), y, r * math.sin(a))
    set_rings(tube, fn)
    tube.rotation_euler = (math.radians(90) * k, 0, 0)
    tube.location = (0, 2.0, lerp(3.4, 6.6, k))
    S["tm"].node_tree.nodes["scroll"].outputs[0].default_value = 0.0
    # rolling: UV u (angle) scroll via leaves, and the noise rotates about the axis: rotate the UV scroll on x
    S["tm"].node_tree.nodes["scroll"].outputs[0].default_value = -0.55 * t
    for lf in S["leaves"]:
        a = lf["ph"] + 2 * math.pi * 0.55 * t   # top moves +x: rotation about +y with positive rate
        rr = lf["r"]; lf["ob"].location = (rr * math.sin(a), lf["y"], rr * math.cos(a))
        lf["ob"].rotation_euler = (0, a + math.pi / 2, lf["spin"] * t)

def update(t):
    S = STATE["S"]; cam, tgt = S["cam"], S["cam_target"]
    if SHOT in ("A", "C"): t = t % T_PERIOD
    jitter = lambda k: 0.06 * math.sin(2 * math.pi * 3 * t / T_PERIOD + k) + 0.04 * math.sin(2 * math.pi * 5 * t / T_PERIOD + 2 * k)   # periodic handheld
    if SHOT == "A":
        update_funnel(S, t); update_debris(S, t)
        cam.location = (0.6 + jitter(0), -17.0, 3.2 + jitter(1)); tgt.location = (0.0 + jitter(2), 0.0, 6.0); cam.data.lens = 24
        S["focus"].location = (0, 0, 4.5)
    elif SHOT == "N":
        s = squeeze_scale(t); update_funnel(S, t, s); update_debris(S, t, s)
        cam.location = (-1.0 + 0.3 * math.sin(t), -18.0, 3.2); tgt.location = (0.0, 0.0, 6.0); cam.data.lens = 24
        S["focus"].location = (0, 0, 4.5)
    elif SHOT == "C":
        update_funnel(S, t); update_debris(S, t)
        cow = next(d for d in S["debris"] if d["name"] == "cow"); cp = Vector(cow["ob"].location)
        a = orbit_angle(cow, t); out = Vector((math.cos(a), math.sin(a), 0))   # radial direction: camera sits outside the cow's orbit, slightly ahead
        cam.location = cp + out * 6.4 + Vector((-math.sin(a), math.cos(a), 0)) * 2.6 + Vector((0, 0, 1.4))
        tgt.location = cp + Vector((0, 0, 0.1)); cam.data.lens = 32; cam.data.dof.aperture_fstop = 2.0
        S["focus"].location = cp
    elif SHOT == "R":
        update_tube(S, t)
        cam.location = (-11.0, -12.5, 4.5 + 0.3 * math.sin(t * 0.7)); tgt.location = (0.5, 2.0, lerp(4.0, 6.5, smoothstep(3.9, 6.3, t))); cam.data.lens = 32
        S["focus"].location = (0, 2, 4)

STATE = {}
def on_frame(scene):
    f = scene.frame_current_final if hasattr(scene, "frame_current_final") else scene.frame_current
    update(f / FPS)

def setup_render(res, samples):
    sc = bpy.context.scene; sc.render.engine = "CYCLES"; c = sc.cycles
    c.device = "CPU"; c.samples = samples; c.use_adaptive_sampling = True; c.adaptive_threshold = 0.1; c.adaptive_min_samples = 4
    c.use_denoising = True; c.denoiser = "OPENIMAGEDENOISE"; c.denoising_input_passes = "RGB_ALBEDO_NORMAL"; c.denoising_use_gpu = False
    c.max_bounces = 4; c.diffuse_bounces = 2; c.glossy_bounces = 2; c.transmission_bounces = 2; c.volume_bounces = 0; c.transparent_max_bounces = 10
    c.caustics_reflective = False; c.caustics_refractive = False; c.blur_glossy = 1.0; c.sample_clamp_indirect = 6.0
    sc.render.use_persistent_data = True; sc.render.use_motion_blur = "noblur" not in FLAGS; sc.render.motion_blur_shutter = 0.5
    sc.render.resolution_x = res; sc.render.resolution_y = res * 16 // 9; sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGB"; sc.render.image_settings.compression = 20
    sc.render.fps = FPS; sc.view_settings.view_transform = "AgX"
    try: sc.view_settings.look = "AgX - Punchy"
    except Exception: pass
    sc.view_settings.exposure = 0.2
    sc.use_nodes = False

TRACKED = ("cow", "trampoline", "gnome", "truck", "stopsign")
def export_tracks(frames):
    """Screen position (1080x1920 px, y down) + camera depth of the tracked debris for every frame -> build/tracks/<shot>.json."""
    sc = bpy.context.scene; S = STATE["S"]; out = {}
    objs = {d["name"]: d["ob"] for d in S["debris"] if d["name"] in TRACKED}
    for f in frames:
        sc.frame_set(f); bpy.context.view_layer.update(); row = {}
        for name, ob in objs.items():
            if ob.hide_render: continue
            co = world_to_camera_view(sc, S["cam"], ob.matrix_world.translation)
            row[name] = [round(co.x * 1080, 1), round((1 - co.y) * 1920, 1), round(co.z, 2)]
        out[str(f)] = row
    tdir = os.path.normpath(os.path.join(ARGS["out"], "..", "..", "tracks")); os.makedirs(tdir, exist_ok=True)
    path = os.path.join(tdir, f"{SHOT}.json"); prev = {}
    if os.path.exists(path):
        try: prev = json.load(open(path))
        except Exception: prev = {}
    prev.update(out); json.dump(prev, open(path, "w")); print(f"TRACKS {SHOT} {len(out)} frames -> {path}", flush=True)

def main():
    clear_scene(); STATE["S"] = build_set(); setup_render(ARGS["res"], ARGS["samples"])
    bpy.app.handlers.frame_change_pre.clear(); bpy.app.handlers.frame_change_pre.append(on_frame)
    os.makedirs(ARGS["out"], exist_ok=True); sc = bpy.context.scene
    frames = [ARGS["start"]] if ARGS["preview"] else list(range(ARGS["start"], ARGS["end"]))
    if SHOT != "R": export_tracks(frames)
    if ARGS["tracks-only"]: return
    for f in frames:
        path = os.path.join(ARGS["out"], f"{SHOT}_{f:04d}.png")
        if os.path.exists(path) and not ARGS["preview"]: continue
        sc.frame_set(f); sc.render.filepath = path
        t0 = time.time(); bpy.ops.render.render(write_still=True)
        print(f"FRAME {SHOT} {f} {time.time() - t0:.1f}s", flush=True)

main()

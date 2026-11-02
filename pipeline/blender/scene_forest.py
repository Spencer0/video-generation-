"""Procedural Blender scene: how a forest is born (video 006), a 120-year succession timelapse on a
block of land cut open like a cake (the "You Built It" format: soil block, cut face toward the camera).

Run headless:
  blender -b -noaudio -P pipeline/blender/scene_forest.py -- --shot H --start 0 --end 107 \
      --out videos/006-forest-born/build/frames/H [--res 576] [--samples 16] [--fps 30] [--preview]
  blender -b -noaudio -P pipeline/blender/scene_forest.py -- --list     # shot frame counts + build/forest_events.json

Units: metres, Z up, the ground at z ~ 0. The block spans x -12..12, y 0..16, z -8..0; the cut face is y = 0 and the
camera always sits at y < 0. Everything is a pure function of the timelapse YEAR, which comes from the real timeline
(build/timeline.json, the beat ids map to year ranges in script.json "years"), so the on-screen counter matches:
  year(t) is linear inside a beat; the ask + loop beats rewind to year 0 with a quintic ease so the last frame
  equals frame 0 (seamless loop).
Shots are video-time ranges (one or two per beat, see SHOTS) with their own always-moving camera; every shot
frame f shows video time t0 + f/fps.

Succession model (old-field, eastern North America; see the fact notes in videos/006-forest-born/BRIEF.md):
  weeds (annuals, wind seeds)   spawn yr 0.2-6, live 1 yr         die of age
  grasses + wildflowers         spawn yr 1.5-12                   die when shaded (> 0.55 crown cover)
  shrubs (bird-dispersed)       spawn yr 8-30, 2-3 m              die when shaded (> 0.7) or old (25-45 yr)
  pioneers (birch 60 % / pine)  spawn yr 10-45, 11-14 m, fast     die when a taller climax tree shades them,
                                                                   by self-thinning, or at 45-70 yr; then brown,
                                                                   drop the crown, stand dead, fall, rot into litter
  climax (oak / maple)          spawn yr 25-80, 17-22 m, slow     never die within 130 yr
The cut face shows a topsoil band that thickens with the years, roots (curves lying on the face) growing with
their trees, and stones. The top surface blends bare dirt -> grass -> leaf litter (Poly Haven CC0 textures in
/home/user/tools/textures, see README).
"""
import bpy, bmesh, math, random, sys, os, time, json
import numpy as np
from mathutils import Vector, Euler
from mathutils import noise as mnoise

def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    a = {"shot": "H", "start": 0, "end": 1, "out": "/tmp/frames", "res": 576, "samples": 16, "preview": False, "fps": 30, "list": False, "vid": "006-forest-born"}
    i = 0
    while i < len(argv):
        k = argv[i].lstrip("-")
        if k in ("preview", "list"): a[k] = True; i += 1; continue
        v = argv[i + 1]; i += 2
        a[k] = type(a[k])(v) if k in a and not isinstance(a[k], bool) else v
    return a

ARGS = parse_args(); FPS = ARGS["fps"]; SHOT = ARGS["shot"].upper()
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VD = os.path.join(ROOT, "videos", ARGS["vid"])
TL = json.load(open(os.path.join(VD, "build", "timeline.json")))
SCRIPT = json.load(open(os.path.join(VD, "script.json")))
YEARS = SCRIPT["years"]; BEATS = {b["id"]: b for b in TL["beats"]}
TEX = os.environ.get("TEXTURES", "/home/user/tools/textures")
BX, BY, BZ = 12.0, 16.0, 8.0            # block half-width, depth, height
SEED = 6

# ----------------------------------------------------------------------------- time: video seconds -> timelapse year
def smoothstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0) if e1 != e0 else 0.0)); return t * t * (3 - 2 * t)
def smoother(u): u = max(0.0, min(1.0, u)); return u * u * u * (u * (u * 6 - 15) + 10)
def lerp(a, b, t): return a + (b - a) * t
def vlerp(a, b, t): return Vector(a).lerp(Vector(b), t)

def year_at(t):
    """Timelapse year at video time t (seconds). Linear inside each beat between the script's year knots;
    the ask beat rewinds from its start year to 0 across ask + loop with a quintic ease (near-still at the end)."""
    for b in TL["beats"]:
        if t < b["end"] or b is TL["beats"][-1]:
            y0, y1 = YEARS[b["id"]]
            if b["id"] == "ask":
                T0, T1 = b["start"], BEATS["loop"]["end"]; return y0 * (1 - smoother((t - T0) / (T1 - T0)))
            if b["id"] == "loop": return 0.0
            return y0 + (y1 - y0) * max(0.0, min(1.0, (t - b["start"]) / b["duration"]))
    return 0.0

def shot_span(beat, f0=0, f1=None, until=None):
    b = BEATS[beat]; t0 = b["start"] + f0 / FPS
    t1 = BEATS[until]["end"] if until else (b["end"] if f1 is None else b["start"] + f1 / FPS)
    return t0, t1
SHOTS = {   # id: video-time span (the assembler's bg_plan maps each beat onto these at offset 0; P2/C2 are mid-beat cuts)
    "H": shot_span("hook"), "W": shot_span("weeds"), "G": shot_span("grass"), "S": shot_span("shrubs"),
    "P1": shot_span("pioneers", 0, 90), "P2": shot_span("pioneers", 90), "C1": shot_span("climax", 0, 84), "C2": shot_span("climax", 84),
    "Y": shot_span("why"), "R": shot_span("ask", until="loop")}
def shot_frames(s): t0, t1 = SHOTS[s]; return int(round((t1 - t0) * FPS))

# ----------------------------------------------------------------------------- camera: always moving, one framing per shot
CAM_H0 = ((-6.0, -40.0, 6.5), (0.0, 7.0, -1.2), 28, 11.0)
def cam_pose(shot, u):
    """(location, look-at, lens mm, f-stop) for shot at fraction u of the shot; the glide is eased."""
    e = smoothstep(0, 1, u)
    if shot == "H": return vlerp(CAM_H0[0], (-4.5, -36.0, 6.8), e), Vector(CAM_H0[1]), 28, 11.0
    if shot == "W": return vlerp((-4.6, -6.5, 1.35), (-3.4, -6.0, 1.2), e), vlerp((-2.6, 2.4, 0.2), (-2.1, 2.6, 0.2), e), 35, 4.0
    if shot == "G": return vlerp((1.5, -24.0, 0.6), (-1.5, -23.5, 0.3), e), Vector((0.0, 4.0, -1.6)), 32, 8.0
    if shot == "S": return vlerp((-20.0, -20.0, 4.8), (-17.0, -19.0, 5.6), e), Vector((0.0, 6.0, 0.9)), 35, 8.0
    if shot == "P1": return vlerp((5.0, -30.0, 4.0), (5.0, -34.0, 9.0), e), vlerp((0.0, 7.0, 1.5), (0.0, 7.0, 4.0), e), 28, 11.0
    if shot == "P2": return vlerp((-2.0, -2.6, 1.0), (0.2, -2.6, 1.1), e), Vector((0.0, 8.0, 7.5)), 24, 5.6
    if shot == "C1": return vlerp((4.0, -13.0, -0.6), (2.0, -12.0, -0.3), e), Vector((0.0, 2.0, -1.7)), 35, 5.6
    if shot == "C2": return vlerp((-9.0, -30.0, 16.0), (-8.0, -38.0, 18.0), e), Vector((0.0, 8.0, 4.0)), 28, 11.0
    if shot == "Y": return vlerp((-14.0, -34.0, 13.0), (12.0, -34.0, 13.0), e), Vector((0.0, 8.0, 4.0)), 28, 11.0
    if shot == "R":   # rewind: glide from the why shot's end pose back to the hook's first frame (quintic, lands still)
        q = smoother(u); return vlerp((12.0, -34.0, 13.0), CAM_H0[0], q), vlerp((0.0, 8.0, 4.0), CAM_H0[1], q), 28, 11.0
    raise SystemExit("unknown shot " + shot)

# ----------------------------------------------------------------------------- blender helpers
def clear_scene():
    for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras, bpy.data.curves, bpy.data.images):
        for x in list(coll): coll.remove(x)
def link_obj(name, data):
    ob = bpy.data.objects.new(name, data); bpy.context.collection.objects.link(ob); return ob
def mesh_obj(name, bm, mats, smooth=True):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if smooth:
        for p in me.polygons: p.use_smooth = True
    for m in (mats if isinstance(mats, (list, tuple)) else [mats]):
        if m: me.materials.append(m)
    return me
def new_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    return m, nt, nt.nodes.new("ShaderNodeOutputMaterial")
def set_in(node, key, val):
    try: node.inputs[key].default_value = val
    except Exception: pass
def node(nt, typ, **kw):
    n = nt.nodes.new(typ)
    for k, v in kw.items(): setattr(n, k, v)
    return n
def math_node(nt, op, a, b=None, clamp=False):
    n = node(nt, "ShaderNodeMath", operation=op); n.use_clamp = clamp
    for i, v in enumerate((a, b)):
        if v is None: continue
        if isinstance(v, (int, float)): n.inputs[i].default_value = v
        else: nt.links.new(v, n.inputs[i])
    return n.outputs[0]
def mix_rgb(nt, fac, a, b):
    n = node(nt, "ShaderNodeMix", data_type="RGBA", blend_type="MIX")
    for sock, v in (("Factor", fac), (6, a), (7, b)):
        if isinstance(v, (int, float)): n.inputs[sock].default_value = v
        elif isinstance(v, tuple): n.inputs[sock].default_value = v
        else: nt.links.new(v, n.inputs[sock])
    return n.outputs[2]
def value_node(nt, name, v=0.0):
    n = node(nt, "ShaderNodeValue", name=name, label=name); n.outputs[0].default_value = v; return n
def load_image(name, kind, srgb):
    p = os.path.join(TEX, name, kind + ".jpg")
    if not os.path.exists(p): return None
    img = bpy.data.images.load(p, check_existing=True); img.colorspace_settings.name = "sRGB" if srgb else "Non-Color"; return img
def tex_set(nt, name, vec, scale, tint=None):
    """Poly Haven texture set as BOX-projected image nodes on `vec`. Returns (color, normal_vector_or_None, roughness_or_None)."""
    mp = node(nt, "ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1 / scale, 1 / scale, 1 / scale); nt.links.new(vec, mp.inputs["Vector"])
    out = []
    for kind, srgb in (("diffuse", True), ("normal", False), ("rough", False)):
        img = load_image(name, kind, srgb)
        if img is None: out.append(None); continue
        it = node(nt, "ShaderNodeTexImage", projection="BOX", projection_blend=0.3); it.image = img; nt.links.new(mp.outputs[0], it.inputs["Vector"])
        s = it.outputs["Color"]
        if kind == "normal":
            nm = node(nt, "ShaderNodeNormalMap"); nm.inputs["Strength"].default_value = 0.8; nt.links.new(s, nm.inputs["Color"]); s = nm.outputs["Normal"]
        elif kind == "diffuse" and tint is not None:
            s = mix_rgb(nt, 1.0, s, s); mul = node(nt, "ShaderNodeMix", data_type="RGBA", blend_type="MULTIPLY"); mul.inputs["Factor"].default_value = 1.0
            nt.links.new(s, mul.inputs[6]); mul.inputs[7].default_value = (*tint, 1); s = mul.outputs[2]
        out.append(s)
    if out[0] is None:   # texture missing: flat fallback so the render still works
        c = node(nt, "ShaderNodeRGB"); c.outputs[0].default_value = (*(tint or (0.4, 0.3, 0.2)), 1); out[0] = c.outputs[0]
    return out

# ----------------------------------------------------------------------------- materials
def ground_material():
    """One material for the block. Normal.z > 0.5 -> the top (dirt -> grass -> litter by the GRASS / LITTER values, patchy);
    else the cut face: excavated soil with a topsoil band (TOPSOIL metres, noisy edge, root streaks), stones at depth."""
    m, nt, out = new_mat("ground"); L = nt.links
    tc = node(nt, "ShaderNodeTexCoord"); obj = tc.outputs["Object"]
    geo = node(nt, "ShaderNodeNewGeometry"); nz = node(nt, "ShaderNodeSeparateXYZ"); L.new(geo.outputs["Normal"], nz.inputs[0])
    is_top = math_node(nt, "GREATER_THAN", nz.outputs["Z"], 0.5)
    pos = node(nt, "ShaderNodeSeparateXYZ"); L.new(obj, pos.inputs[0]); z = pos.outputs["Z"]
    GRASS, LITTER, TOPSOIL = value_node(nt, "GRASS", 0.0), value_node(nt, "LITTER", 0.0), value_node(nt, "TOPSOIL", 0.1)
    # --- top
    dirt_c, dirt_n, dirt_r = tex_set(nt, "dirt_floor", obj, 3.0, tint=(0.50, 0.40, 0.30))
    grass_c, grass_n, grass_r = tex_set(nt, "grass_ground", obj, 2.6)
    lit_c, lit_n, lit_r = tex_set(nt, "forest_leaves_03", obj, 2.2)
    patch = node(nt, "ShaderNodeTexNoise"); patch.inputs["Scale"].default_value = 0.35; patch.inputs["Detail"].default_value = 3.0; L.new(obj, patch.inputs["Vector"])
    patch2 = node(nt, "ShaderNodeTexNoise"); patch2.inputs["Scale"].default_value = 0.6; patch2.inputs["Detail"].default_value = 3.0; patch2.inputs["Roughness"].default_value = 0.7; L.new(obj, patch2.inputs["Vector"])
    # f = clamp(V*1.6 - 0.3 + (noise-0.5)*k): the cover arrives in patches, not as one fade
    def patchy(V, nse, k, gain=1.6, off=-0.3):
        a = math_node(nt, "MULTIPLY", V, gain); a = math_node(nt, "ADD", a, off)
        b = math_node(nt, "SUBTRACT", nse, 0.5); b = math_node(nt, "MULTIPLY", b, k)
        return math_node(nt, "ADD", a, b, clamp=True)
    f_g = patchy(GRASS.outputs[0], patch.outputs["Fac"], 1.2)
    f_l = patchy(LITTER.outputs[0], patch2.outputs["Fac"], 1.0)
    top_c = mix_rgb(nt, f_l, mix_rgb(nt, f_g, dirt_c, grass_c), lit_c)
    top_n = mix_rgb(nt, f_l, mix_rgb(nt, f_g, dirt_n, grass_n), lit_n) if (dirt_n and grass_n and lit_n) else None
    top_r = mix_rgb(nt, f_l, mix_rgb(nt, f_g, dirt_r or (0.8, 0.8, 0.8, 1), grass_r or (0.7, 0.7, 0.7, 1)), lit_r or (0.75, 0.75, 0.75, 1))
    # --- cut face
    soil_c, soil_n, soil_r = tex_set(nt, "excavated_soil_wall", obj, 3.5)
    edge = node(nt, "ShaderNodeTexNoise"); edge.inputs["Scale"].default_value = 1.4; edge.inputs["Detail"].default_value = 4.0; L.new(obj, edge.inputs["Vector"])
    band = math_node(nt, "ADD", z, TOPSOIL.outputs[0])                       # z + D  (>0 inside the topsoil band)
    band = math_node(nt, "ADD", band, math_node(nt, "MULTIPLY", math_node(nt, "SUBTRACT", edge.outputs["Fac"], 0.5), 0.35))
    m_top = math_node(nt, "MULTIPLY", band, 12.0, clamp=True)                 # soft edge over ~8 cm
    hm = node(nt, "ShaderNodeMix", data_type="RGBA", blend_type="MULTIPLY"); hm.inputs["Factor"].default_value = 1.0
    L.new(soil_c, hm.inputs[6]); hm.inputs[7].default_value = (0.17, 0.11, 0.07, 1); humus = hm.outputs[2]
    streak = node(nt, "ShaderNodeTexNoise"); streak.inputs["Scale"].default_value = 9.0; streak.inputs["Detail"].default_value = 2.0
    smap = node(nt, "ShaderNodeMapping"); smap.inputs["Scale"].default_value = (6.0, 6.0, 0.6); L.new(obj, smap.inputs["Vector"]); L.new(smap.outputs[0], streak.inputs["Vector"])
    roots = math_node(nt, "GREATER_THAN", streak.outputs["Fac"], 0.62)
    humus = mix_rgb(nt, math_node(nt, "MULTIPLY", roots, 0.5), humus, (0.72, 0.62, 0.45, 1))   # pale root threads in the dark band
    deep = math_node(nt, "MULTIPLY", math_node(nt, "ADD", z, 3.0), -0.25, clamp=True)        # 0 above z=-3, 1 at z=-7
    vor = node(nt, "ShaderNodeTexVoronoi"); vor.inputs["Scale"].default_value = 1.8; vor.inputs["Randomness"].default_value = 1.0; L.new(obj, vor.inputs["Vector"])
    stone = math_node(nt, "LESS_THAN", vor.outputs["Distance"], 0.13)
    stone = math_node(nt, "MULTIPLY", stone, deep)
    lower = mix_rgb(nt, deep, soil_c, mix_rgb(nt, 0.45, soil_c, (0.52, 0.48, 0.42, 1)))
    lower = mix_rgb(nt, math_node(nt, "MULTIPLY", stone, 0.6), lower, (0.36, 0.33, 0.29, 1))
    face_c = mix_rgb(nt, m_top, lower, humus)
    face_r = mix_rgb(nt, m_top, soil_r or (0.85, 0.85, 0.85, 1), (0.95, 0.95, 0.95, 1))
    # --- combine
    p = node(nt, "ShaderNodeBsdfPrincipled"); set_in(p, "Specular IOR Level", 0.25)
    L.new(mix_rgb(nt, is_top, face_c, top_c), p.inputs["Base Color"])
    L.new(mix_rgb(nt, is_top, face_r, top_r), p.inputs["Roughness"])
    if soil_n is not None and top_n is not None:
        nmix = node(nt, "ShaderNodeMix", data_type="VECTOR"); L.new(is_top, nmix.inputs["Factor"]); L.new(soil_n, nmix.inputs[4]); L.new(top_n, nmix.inputs[5]); L.new(nmix.outputs[1], p.inputs["Normal"])
    L.new(p.outputs[0], out.inputs[0]); return m

def leaf_material(name, color, brown=(0.45, 0.30, 0.12), var=0.12, sheen=0.3):
    """Foliage: species colour with per-instance hue variation (Object Info Random) and a noise mottle; Object colour R -> brown."""
    m, nt, out = new_mat(name); L = nt.links
    oi = node(nt, "ShaderNodeObjectInfo"); tc = node(nt, "ShaderNodeTexCoord")
    nse = node(nt, "ShaderNodeTexNoise"); nse.inputs["Scale"].default_value = 14.0; nse.inputs["Detail"].default_value = 3.0; L.new(tc.outputs["Object"], nse.inputs["Vector"])
    base = (*color, 1); lighter = (min(1, color[0] * 1.35 + 0.05), min(1, color[1] * 1.25 + 0.03), color[2] * 1.1, 1)
    c = mix_rgb(nt, nse.outputs["Fac"], base, lighter)
    c = mix_rgb(nt, math_node(nt, "MULTIPLY", oi.outputs["Random"], var), c, (color[0] * 1.3, color[1] * 1.15, color[2] * 0.6, 1))
    col = node(nt, "ShaderNodeSeparateColor"); L.new(oi.outputs["Color"], col.inputs[0])
    c = mix_rgb(nt, col.outputs["Red"], c, (*brown, 1))
    p = node(nt, "ShaderNodeBsdfPrincipled"); p.inputs["Roughness"].default_value = 0.75; set_in(p, "Specular IOR Level", 0.2)
    set_in(p, "Sheen Weight", sheen); set_in(p, "Subsurface Weight", 0.0)
    fine = node(nt, "ShaderNodeTexNoise"); fine.inputs["Scale"].default_value = 60.0; fine.inputs["Detail"].default_value = 2.0; fine.inputs["Roughness"].default_value = 0.6; L.new(tc.outputs["Object"], fine.inputs["Vector"])
    bump = node(nt, "ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.5; bump.inputs["Distance"].default_value = 0.05; L.new(fine.outputs["Fac"], bump.inputs["Height"]); L.new(bump.outputs[0], p.inputs["Normal"])
    L.new(c, p.inputs["Base Color"]); L.new(p.outputs[0], out.inputs[0]); return m

def bark_material(name, tex, tint, scale=1.2, rough=0.8):
    m, nt, out = new_mat(name); L = nt.links; tc = node(nt, "ShaderNodeTexCoord")
    c, n, r = tex_set(nt, tex, tc.outputs["Object"], scale, tint=tint)
    oi = node(nt, "ShaderNodeObjectInfo"); col = node(nt, "ShaderNodeSeparateColor"); L.new(oi.outputs["Color"], col.inputs[0])
    c = mix_rgb(nt, col.outputs["Blue"], c, (0.40, 0.37, 0.33, 1))     # Object colour B -> dead grey wood
    p = node(nt, "ShaderNodeBsdfPrincipled"); p.inputs["Roughness"].default_value = rough; set_in(p, "Specular IOR Level", 0.2)
    L.new(c, p.inputs["Base Color"])
    if n is not None: L.new(n, p.inputs["Normal"])
    L.new(p.outputs[0], out.inputs[0]); return m

def birch_material():
    """White bark with dark horizontal lenticel streaks (stretched noise), grey when dead."""
    m, nt, out = new_mat("birch"); L = nt.links; tc = node(nt, "ShaderNodeTexCoord")
    mp = node(nt, "ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1.0, 1.0, 14.0); L.new(tc.outputs["Object"], mp.inputs["Vector"])
    nse = node(nt, "ShaderNodeTexNoise"); nse.inputs["Scale"].default_value = 6.0; nse.inputs["Detail"].default_value = 2.0; L.new(mp.outputs[0], nse.inputs["Vector"])
    streak = math_node(nt, "GREATER_THAN", nse.outputs["Fac"], 0.60)
    c = mix_rgb(nt, streak, (0.86, 0.84, 0.78, 1), (0.12, 0.10, 0.09, 1))
    pos = node(nt, "ShaderNodeSeparateXYZ"); L.new(tc.outputs["Object"], pos.inputs[0])
    c = mix_rgb(nt, math_node(nt, "MULTIPLY", math_node(nt, "SUBTRACT", 0.25, pos.outputs["Z"]), 4.0, clamp=True), c, (0.25, 0.20, 0.16, 1))   # dark, rough base
    oi = node(nt, "ShaderNodeObjectInfo"); col = node(nt, "ShaderNodeSeparateColor"); L.new(oi.outputs["Color"], col.inputs[0])
    c = mix_rgb(nt, col.outputs["Blue"], c, (0.45, 0.42, 0.38, 1))
    p = node(nt, "ShaderNodeBsdfPrincipled"); p.inputs["Roughness"].default_value = 0.7; set_in(p, "Specular IOR Level", 0.2); L.new(c, p.inputs["Base Color"]); L.new(p.outputs[0], out.inputs[0]); return m

def grass_material():
    """Blades: dark base to light tip (object-space Z), Object colour R -> straw brown."""
    m, nt, out = new_mat("grass"); L = nt.links; tc = node(nt, "ShaderNodeTexCoord"); pos = node(nt, "ShaderNodeSeparateXYZ"); L.new(tc.outputs["Object"], pos.inputs[0])
    zz = math_node(nt, "MULTIPLY", pos.outputs["Z"], 1.8, clamp=True)
    c = mix_rgb(nt, zz, (0.08, 0.17, 0.04, 1), (0.42, 0.62, 0.16, 1))
    oi = node(nt, "ShaderNodeObjectInfo"); c = mix_rgb(nt, math_node(nt, "MULTIPLY", oi.outputs["Random"], 0.25), c, (0.55, 0.60, 0.18, 1))
    col = node(nt, "ShaderNodeSeparateColor"); L.new(oi.outputs["Color"], col.inputs[0]); c = mix_rgb(nt, col.outputs["Red"], c, (0.62, 0.50, 0.22, 1))
    p = node(nt, "ShaderNodeBsdfPrincipled"); p.inputs["Roughness"].default_value = 0.55; set_in(p, "Specular IOR Level", 0.3); set_in(p, "Sheen Weight", 0.4)
    L.new(c, p.inputs["Base Color"]); L.new(p.outputs[0], out.inputs[0]); return m

def flower_material():
    """Stem green; head = Object colour RGB when blooming (Object colour alpha), green bud otherwise. Material index 1 = head."""
    m, nt, out = new_mat("flowerhead"); L = nt.links; oi = node(nt, "ShaderNodeObjectInfo")
    c = mix_rgb(nt, oi.outputs["Alpha"], (0.25, 0.42, 0.12, 1), oi.outputs["Color"])
    p = node(nt, "ShaderNodeBsdfPrincipled"); p.inputs["Roughness"].default_value = 0.6; L.new(c, p.inputs["Base Color"]); L.new(p.outputs[0], out.inputs[0]); return m

def plain(name, color, rough=0.6, spec=0.3):
    m, nt, out = new_mat(name); p = node(nt, "ShaderNodeBsdfPrincipled"); p.inputs["Base Color"].default_value = (*color, 1); p.inputs["Roughness"].default_value = rough
    set_in(p, "Specular IOR Level", spec); nt.links.new(p.outputs[0], out.inputs[0]); return m

def rock_material():
    m, nt, out = new_mat("rock"); L = nt.links; tc = node(nt, "ShaderNodeTexCoord")
    nse = node(nt, "ShaderNodeTexNoise"); nse.inputs["Scale"].default_value = 3.0; nse.inputs["Detail"].default_value = 6.0; L.new(tc.outputs["Object"], nse.inputs["Vector"])
    c = mix_rgb(nt, nse.outputs["Fac"], (0.10, 0.09, 0.08, 1), (0.30, 0.27, 0.23, 1))
    bump = node(nt, "ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.4; bump.inputs["Distance"].default_value = 0.03; L.new(nse.outputs["Fac"], bump.inputs["Height"])
    p = node(nt, "ShaderNodeBsdfDiffuse"); p.inputs["Roughness"].default_value = 0.6; L.new(c, p.inputs["Color"]); L.new(bump.outputs[0], p.inputs["Normal"]); L.new(p.outputs[0], out.inputs[0]); return m

def cloud_shadow_material():
    """Shadow-only plane high above: transparent where the noise is low, opaque patches (clouds) elsewhere. OFFSET drives the drift."""
    m, nt, out = new_mat("cloudshadow"); L = nt.links; tc = node(nt, "ShaderNodeTexCoord")
    mp = node(nt, "ShaderNodeMapping", name="cloudmap"); mp.inputs["Scale"].default_value = (0.012, 0.012, 1.0); L.new(tc.outputs["Object"], mp.inputs["Vector"])
    nse = node(nt, "ShaderNodeTexNoise"); nse.inputs["Scale"].default_value = 1.0; nse.inputs["Detail"].default_value = 4.0; nse.inputs["Roughness"].default_value = 0.6; L.new(mp.outputs[0], nse.inputs["Vector"])
    f = math_node(nt, "SUBTRACT", nse.outputs["Fac"], 0.56); f = math_node(nt, "MULTIPLY", f, 7.0, clamp=True)
    tr = node(nt, "ShaderNodeBsdfTransparent"); df = node(nt, "ShaderNodeBsdfDiffuse")
    mix = node(nt, "ShaderNodeMixShader"); L.new(f, mix.inputs[0]); L.new(tr.outputs[0], mix.inputs[1]); L.new(df.outputs[0], mix.inputs[2]); L.new(mix.outputs[0], out.inputs[0])
    m.blend_method = "BLEND"; return m

# ----------------------------------------------------------------------------- geometry
def ground_z(x, y):
    return 0.07 * mnoise.noise(Vector((x * 0.35, y * 0.35, 1.7))) + 0.03 * mnoise.noise(Vector((x * 1.3, y * 1.3, 4.1)))

def build_block(mat):
    bm = bmesh.new(); nx, ny = 48, 32
    bmesh.ops.create_grid(bm, x_segments=nx, y_segments=ny, size=1.0)
    for v in bm.verts:
        x = v.co.x * BX; y = (v.co.y + 1.0) * 0.5 * BY; v.co = Vector((x, y, ground_z(x, y)))
    bm.verts.ensure_lookup_table(); edges = [e for e in bm.edges if e.is_boundary]
    r = bmesh.ops.extrude_edge_only(bm, edges=edges)
    nv = [g for g in r["geom"] if isinstance(g, bmesh.types.BMVert)]
    for v in nv: v.co.z = -BZ
    bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = mesh_obj("block", bm, mat, smooth=False)
    for p in me.polygons: p.use_smooth = p.normal.z > 0.5
    return link_obj("block", me)

def noisy_sphere(bm, center, r, amp, seed, subdiv=2, fine=0.0):
    g = bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=r)["verts"]
    for v in g:
        q = Vector((v.co.x / r * 1.6 + seed, v.co.y / r * 1.6, v.co.z / r * 1.6 + seed * 0.3))
        n = mnoise.noise(q) + fine * mnoise.noise(q * 4.0 + Vector((7.1, 3.3, 1.9)))
        v.co = v.co * (1 + amp * n) + Vector(center)
    return g

def blade(bm, base, az, length, width, bend, lean, segs=4):
    """One grass blade: a strip of quads from base, leaning outward by `lean`, curling over by `bend`, tapering to the tip."""
    ca, sa = math.cos(az), math.sin(az); prev = None
    for i in range(segs + 1):
        u = i / segs; w = width * (1 - u * 0.85); out = lean * u + bend * u * u; z = length * u * (1 - 0.35 * bend * u * u)
        c = Vector(base) + Vector((ca * out, sa * out, z)); side = Vector((-sa, ca, 0)) * w
        a = bm.verts.new(c - side); b = bm.verts.new(c + side)
        if prev: bm.faces.new((prev[0], prev[1], b, a))
        prev = (a, b)

def make_tuft(variant, mat):
    rng = random.Random(100 + variant); bm = bmesh.new()
    for i in range(rng.randint(14, 22)):
        az = rng.uniform(0, 2 * math.pi); blade(bm, (rng.uniform(-0.03, 0.03), rng.uniform(-0.03, 0.03), 0), az, rng.uniform(0.28, 0.55), rng.uniform(0.008, 0.014), rng.uniform(0.08, 0.25), rng.uniform(0.02, 0.1))
    return mesh_obj(f"tuft{variant}", bm, mat)

def make_weed(variant, mat):
    """Annual weed: a rosette of broader leaves plus a stem with a seed head (variant 1 is taller and stem-dominated)."""
    rng = random.Random(200 + variant); bm = bmesh.new(); tall = variant == 1
    n = rng.randint(5, 8)
    for i in range(n):
        az = 2 * math.pi * i / n + rng.uniform(-0.3, 0.3)
        blade(bm, (0, 0, 0.01), az, rng.uniform(0.12, 0.22) * (0.7 if tall else 1), rng.uniform(0.02, 0.035), rng.uniform(0.1, 0.2), rng.uniform(0.04, 0.1), segs=5)
    h = rng.uniform(0.35, 0.6) if tall else rng.uniform(0.18, 0.3)
    g = bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.006, radius2=0.003, depth=h)["verts"]
    for v in g: v.co.z += h / 2
    if tall:
        for k in range(4):
            zz = h * (0.35 + 0.15 * k); blade(bm, (0, 0, zz), rng.uniform(0, 2 * math.pi), 0.12, 0.018, 0.1, 0.05, segs=3)
    noisy_sphere(bm, (0, 0, h), 0.02 if not tall else 0.03, 0.3, variant, 1)
    return mesh_obj(f"weed{variant}", bm, mat)

def make_flower(variant, mats):
    rng = random.Random(300 + variant); bm = bmesh.new(); h = rng.uniform(0.3, 0.5)
    g = bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.005, radius2=0.004, depth=h)["verts"]
    for v in g: v.co.z += h / 2
    for i in range(4): blade(bm, (0, 0, 0.01), 2 * math.pi * i / 4 + rng.uniform(-0.3, 0.3), 0.1, 0.012, 0.1, 0.05, segs=3)
    stem_faces = set(bm.faces)
    head = noisy_sphere(bm, (0, 0, h + 0.01), 0.045, 0.15, variant, 2)
    for f in bm.faces:
        if f not in stem_faces: f.material_index = 1
    for v in head: v.co.z = h + (v.co.z - h) * 0.55 + 0.005
    return mesh_obj(f"flower{variant}", bm, mats)

def make_shrub(variant, mats):
    """Leaf blobs on short twigs; unit size ~1.3 m wide, 1.0 m tall. Material 0 = leaves, 1 = wood."""
    rng = random.Random(400 + variant); bm = bmesh.new()
    n = rng.randint(6, 9); wood = []
    for i in range(n):
        a = rng.uniform(0, 2 * math.pi); rr = rng.uniform(0.1, 0.42); z = rng.uniform(0.35, 0.75); r = rng.uniform(0.22, 0.36)
        c = (rr * math.cos(a), rr * math.sin(a) * 0.85, z)
        noisy_sphere(bm, c, r, 0.3, variant * 10 + i, 3, fine=0.6)
        tw = bmesh.ops.create_cone(bm, cap_ends=True, segments=5, radius1=0.02, radius2=0.01, depth=math.hypot(c[0], c[1], c[2]))["verts"]
        d = Vector(c); q = d.to_track_quat("Z", "Y")
        for v in tw: v.co = q @ (v.co + Vector((0, 0, d.length / 2))); wood.append(v)
    woodv = set(wood)
    for f in bm.faces:
        if all(v in woodv for v in f.verts): f.material_index = 1
    return mesh_obj(f"shrub{variant}", bm, mats)

def make_trunk(name, mat, r0, r1, bend=0.0, segs=12, top=1.0):
    """Trunk along +Z with a gentle lean/curve; radius r0 at the base, r1 at the top (unit scale: tree height 1, trunk ends at `top`)."""
    bm = bmesh.new(); rings = []; n = 8
    for i in range(n + 1):
        u = i / n; r = lerp(r0, r1, u ** 0.8); z = u * top; off = bend * u * u
        ring = [bm.verts.new((r * math.cos(2 * math.pi * k / segs) + off, r * math.sin(2 * math.pi * k / segs), z)) for k in range(segs)]
        rings.append(ring)
    for i in range(n):
        for k in range(segs): bm.faces.new((rings[i][k], rings[i][(k + 1) % segs], rings[i + 1][(k + 1) % segs], rings[i + 1][k]))
    bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
    return mesh_obj(name, bm, mat)

def make_crown(name, kind, mat, seed=0):
    """Crown mesh in unit-tree space (height 1): blobs for broadleaves, cone tiers for pine."""
    rng = random.Random(500 + seed); bm = bmesh.new()
    if kind == "pine":   # tiers of flattened lumpy ellipsoids, shrinking to the tip
        for i in range(8):
            u = i / 7; z0 = 0.30 + 0.66 * u; r = lerp(0.17, 0.04, u ** 0.9)
            g = noisy_sphere(bm, (0, 0, 0), r, 0.3, seed * 5 + i, 2, fine=0.6)
            for v in g: v.co = Vector((v.co.x, v.co.y, v.co.z * 0.45 + z0))
    else:
        spec = {"birch": (0.62, 0.16, 0.32, 6, 0.22), "oak": (0.62, 0.30, 0.30, 11, 0.26), "maple": (0.64, 0.27, 0.34, 10, 0.24)}[kind]
        zc, rx, rz, n, rb = spec
        for i in range(n):
            a = rng.uniform(0, 2 * math.pi); rr = rng.uniform(0, 1) ** 0.6 * rx * 0.8; z = zc + rng.uniform(-rz * 0.7, rz * 0.7) * (1 - rr / rx) ** 0.3
            r = rb * rng.uniform(0.6, 1.0) * (0.75 + 0.25 * (1 - abs(z - zc) / rz))
            noisy_sphere(bm, (rr * math.cos(a), rr * math.sin(a), z), r, 0.32, seed * 7 + i, 3, fine=0.6)
    return mesh_obj(name, bm, mat)

def make_stone(variant, mat):
    bm = bmesh.new(); noisy_sphere(bm, (0, 0, 0), 1.0, 0.35, 70 + variant, 2); return mesh_obj(f"stone{variant}", bm, mat)

def root_curve(name, x, depth, spread, mat, seed):
    """Roots lying on the cut face (y = -0.05, just in front of it): a tap root plus laterals, as POLY splines; grown with bevel_factor_end."""
    rng = random.Random(seed); cu = bpy.data.curves.new(name, "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = 0.02; cu.bevel_resolution = 3; cu.fill_mode = "FULL"
    cu.use_fill_caps = True; cu.bevel_factor_mapping_end = "SPLINE"
    def spline(pts, r0, r1):
        sp = cu.splines.new("POLY"); sp.points.add(len(pts) - 1); sp.use_smooth = True
        for i, (p, q) in enumerate(zip(sp.points, pts)): p.co = (q[0], q[1], q[2], 1.0); p.radius = lerp(r0, r1, i / (len(pts) - 1))
    n = 9; main = []
    for i in range(n):
        u = i / (n - 1); main.append((x + spread * 0.25 * math.sin(u * 5 + seed) * u, -0.05, -0.02 - depth * u))
    spline(main, 1.0, 0.15)
    for k in range(rng.randint(2, 4)):
        s = rng.choice((-1, 1)); z0 = -0.05 - depth * rng.uniform(0.05, 0.5); L = spread * rng.uniform(0.5, 1.0); pts = []
        for i in range(6):
            u = i / 5; pts.append((x + s * L * u + 0.15 * math.sin(u * 7 + k), -0.05, z0 - depth * 0.55 * u - 0.1 * math.sin(u * 4 + seed)))
        spline(pts, 0.55, 0.1)
    cu.materials.append(mat); ob = link_obj(name, cu); return ob

# ----------------------------------------------------------------------------- the population (deterministic, seeded)
def growth(age, tau, k=1.6): return 0.0 if age <= 0 else (1 - math.exp(-age / tau)) ** k
def np_growth(age, tau, k=1.6): return np.where(age <= 0, 0.0, (1 - np.exp(-np.maximum(age, 0) / tau)) ** k)

def make_population():
    rng = random.Random(SEED); P = {"trees": [], "shrubs": [], "grass": [], "weeds": [], "flowers": []}
    def pt(front_bias=1.0, margin=0.3):
        u = rng.random() ** front_bias; return rng.uniform(-BX + margin, BX - margin), 0.25 + (BY - 0.25 - margin) * u
    # trees: pioneers then climax, Poisson-disc-ish spacing (reject too-close pairs)
    def place(n, dmin, kind_fn, tries=4000):
        out = []
        for _ in range(tries):
            if len(out) >= n: break
            x, y = pt(1.0, 0.6)
            if all(math.hypot(x - o["x"], y - o["y"]) >= dmin for o in out): out.append(kind_fn(x, y))
        return out
    def pioneer(x, y):
        birch = rng.random() < 0.6
        return dict(kind="birch" if birch else "pine", cls="pioneer", x=x, y=y, rot=rng.uniform(0, 6.28), t_spawn=10 + 35 * rng.random() ** 1.4,
                    Hmax=rng.uniform(11, 14) if birch else rng.uniform(10, 13), Rmax=1.0, tau=rng.uniform(10, 14), lifespan=rng.uniform(40, 62),
                    thin=(30 + rng.uniform(0, 40)) if rng.random() < 0.6 else 999.0, death=999.0, lean=rng.uniform(0, 6.28))
    def climax(x, y):
        oak = rng.random() < 0.5
        return dict(kind="oak" if oak else "maple", cls="climax", x=x, y=y, rot=rng.uniform(0, 6.28), t_spawn=25 + 55 * rng.random() ** 1.6,
                    Hmax=rng.uniform(17, 22), Rmax=1.0, tau=rng.uniform(28, 36), lifespan=999.0, thin=999.0, death=999.0, lean=0.0)
    P["trees"] = place(150, 1.6, pioneer) + place(34, 4.2, climax)
    P["shrubs"] = [dict(var=rng.randrange(3), x=x, y=y, rot=rng.uniform(0, 6.28), s=rng.uniform(1.6, 3.0), t_spawn=8 + 22 * rng.random() ** 1.3, lifespan=rng.uniform(25, 45), death=999.0)
                   for x, y in (pt(1.0, 0.5) for _ in range(110))]
    P["grass"] = [dict(var=rng.randrange(3), x=x, y=y, rot=rng.uniform(0, 6.28), s=rng.uniform(0.8, 1.4), t_spawn=1.5 + 7.5 * rng.random() ** 1.2, death=999.0)
                  for x, y in (pt(1.8, 0.15) for _ in range(1700))]
    P["weeds"] = [dict(var=rng.randrange(3), x=x, y=y, rot=rng.uniform(0, 6.28), s=rng.uniform(0.7, 1.3), t_spawn=0.2 + 5.5 * rng.random() ** 2.2)
                  for x, y in (pt(1.6, 0.15) for _ in range(900))]
    P["flowers"] = [dict(var=rng.randrange(2), x=x, y=y, rot=rng.uniform(0, 6.28), s=rng.uniform(0.8, 1.3), t_spawn=2.5 + 9 * rng.random() ** 1.3,
                         color=rng.choice([(1.0, 0.85, 0.1), (0.95, 0.95, 0.9), (0.6, 0.35, 0.9), (0.95, 0.5, 0.2)]), ph=rng.random(), death=999.0)
                    for x, y in (pt(1.5, 0.2) for _ in range(560))]
    # ---- deaths from shade (numpy over years): crown cover = exp(-(d / r)^2) summed over trees taller than the victim
    T = P["trees"]; tx = np.array([t["x"] for t in T]); ty = np.array([t["y"] for t in T]); tsp = np.array([t["t_spawn"] for t in T])
    tH = np.array([t["Hmax"] for t in T]); ttau = np.array([t["tau"] for t in T]); is_cl = np.array([t["cls"] == "climax" for t in T])
    years = np.arange(0, 131, 0.5)
    def tree_state(Y, death):
        g = np_growth(Y - tsp, ttau); H = tH * g; R = crown_r(H, is_cl); alive = Y < death; return H * alive, R * alive
    # pioneers: shaded by taller climax trees (> 1 m taller, cover > 0.5), self-thinning, or age
    death = np.array([min(t["t_spawn"] + t["lifespan"], t["thin"]) for t in T])
    for Y in years:
        H, R = tree_state(Y, death); cl = is_cl & (H > 1.0)
        d2 = (tx[:, None] - tx[None, cl]) ** 2 + (ty[:, None] - ty[None, cl]) ** 2
        cover = np.exp(-d2 / np.maximum(R[None, cl], 0.3) ** 2) * (H[None, cl] > H[:, None] + 1.0)
        shade = cover.sum(1); hit = (~is_cl) & (shade > 0.5) & (death > Y) & (H > 0.5)
        death[hit] = Y
    for t, d in zip(T, death): t["death"] = float(d)
    # ground plants: first year the cover of any tree taller than them exceeds a threshold
    for key, thr, hmin in (("grass", 0.55, 0.3), ("flowers", 0.45, 0.3), ("shrubs", 0.7, 2.0), ("weeds", 0.45, 0.3)):
        G = P[key]; gx = np.array([g["x"] for g in G]); gy = np.array([g["y"] for g in G]); gd = np.full(len(G), 999.0)
        for Y in years:
            H, R = tree_state(Y, death); on = H > hmin
            if not on.any(): continue
            d2 = (gx[:, None] - tx[None, on]) ** 2 + (gy[:, None] - ty[None, on]) ** 2
            shade = (np.exp(-d2 / np.maximum(R[None, on], 0.3) ** 2)).sum(1)
            hit = (shade > thr) & (gd > Y); gd[hit] = Y
        for g, d in zip(G, gd):
            if key == "weeds": g["shade_death"] = float(d)
            else: g["death"] = float(min(d, g["t_spawn"] + g["lifespan"]) if "lifespan" in g else d)
    return P

def crown_r(H, is_cl):
    """Crown radius from height: pioneers slender (0.17 H), climax trees broad (0.28 H)."""
    return np.where(is_cl, 0.28, 0.17) * H

# ----------------------------------------------------------------------------- build the world
STATE = {}
def light(name, typ, loc, energy, color, angle=None, target=(0, 6, 0)):
    ld = bpy.data.lights.new(name, typ); ld.energy = energy; ld.color = color
    if angle is not None: ld.angle = angle
    ob = link_obj(name, ld); ob.location = loc; d = Vector(target) - Vector(loc); ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler(); return ob

def build_world():
    w = bpy.data.worlds["World"] if "World" in bpy.data.worlds else bpy.data.worlds.new("World"); bpy.context.scene.world = w; w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    out = node(nt, "ShaderNodeOutputWorld"); bg = node(nt, "ShaderNodeBackground"); bg.inputs[1].default_value = 1.0
    tc = node(nt, "ShaderNodeTexCoord"); sep = node(nt, "ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    # Generated for the world = the view direction (-1..1); z = 0 is the horizon. Bright hazy horizon to saturated blue zenith, soft clouds.
    up = math_node(nt, "MULTIPLY", sep.outputs["Z"], 2.2, clamp=True)
    sky = mix_rgb(nt, math_node(nt, "POWER", up, 0.55), (0.90, 0.94, 0.99, 1), (0.28, 0.50, 0.92, 1))
    cl = node(nt, "ShaderNodeTexNoise"); cl.inputs["Scale"].default_value = 2.2; cl.inputs["Detail"].default_value = 6.0; cl.inputs["Roughness"].default_value = 0.62
    mp = node(nt, "ShaderNodeMapping", name="skymap"); mp.inputs["Scale"].default_value = (1.0, 1.0, 2.5); nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"]); nt.links.new(mp.outputs[0], cl.inputs["Vector"])
    cf = math_node(nt, "SUBTRACT", cl.outputs["Fac"], 0.50); cf = math_node(nt, "MULTIPLY", cf, 5.0, clamp=True); cf = math_node(nt, "MULTIPLY", cf, math_node(nt, "MULTIPLY", sep.outputs["Z"], 6.0, clamp=True))
    sky = mix_rgb(nt, cf, sky, (0.99, 0.99, 1.0, 1))
    below = math_node(nt, "LESS_THAN", sep.outputs["Z"], 0.0)
    down = math_node(nt, "MULTIPLY", sep.outputs["Z"], -1.5, clamp=True)
    col = mix_rgb(nt, below, sky, mix_rgb(nt, down, (0.72, 0.76, 0.80, 1), (0.50, 0.55, 0.62, 1)))   # below the horizon: neutral haze, lights the block's underside softly
    nt.links.new(col, bg.inputs[0]); nt.links.new(bg.outputs[0], out.inputs[0])

def build_set():
    S = {}; build_world(); rng = random.Random(SEED + 1)
    S["block"] = build_block(ground_material())
    rock = rock_material()
    stones = [make_stone(i, rock) for i in range(3)]
    for i in range(14):   # stones half-buried in the cut face, a few on the surface
        ob = link_obj(f"stone_{i}", stones[i % 3]); r = rng.uniform(0.15, 0.55)
        if i < 10: ob.location = (rng.uniform(-BX + 1, BX - 1), r * 0.62, rng.uniform(-7.2, -0.8))
        else: ob.location = (rng.uniform(-BX + 1, BX - 1), rng.uniform(0.5, BY - 1), -r * 0.45); r *= 0.5
        ob.scale = (r, r * rng.uniform(0.7, 1.0), r * rng.uniform(0.6, 0.9)); ob.rotation_euler = (rng.uniform(0, 3), rng.uniform(0, 3), rng.uniform(0, 3))
    # lights: sun from front-left-high (lights the cut face), soft sky fill from the world
    S["sun"] = light("sun", "SUN", (-30, -40, 60), 3.2, (1.0, 0.97, 0.9), angle=math.radians(1.5), target=(0, 6, 0))
    # cloud shadows: a shadow-only plane high above, drifting
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=400.0)
    S["clouds"] = link_obj("clouds", mesh_obj("clouds", bm, cloud_shadow_material(), smooth=False)); S["clouds"].location = (0, 0, 60)
    S["clouds"].visible_camera = False; S["clouds"].visible_diffuse = False; S["clouds"].visible_glossy = False; S["clouds"].visible_transmission = False
    # materials
    M = {"grass": grass_material(), "weed": leaf_material("weedleaf", (0.30, 0.48, 0.12), brown=(0.55, 0.42, 0.2), sheen=0.4),
         "flower_stem": leaf_material("flowerstem", (0.22, 0.40, 0.10), brown=(0.5, 0.4, 0.2)), "flower_head": flower_material(),
         "shrub": leaf_material("shrubleaf", (0.08, 0.26, 0.06), brown=(0.42, 0.28, 0.12)), "twig": plain("twig", (0.25, 0.18, 0.12), 0.8),
         "birch_leaf": leaf_material("birchleaf", (0.24, 0.47, 0.10), brown=(0.62, 0.44, 0.12)), "pine_needle": leaf_material("pineneedle", (0.05, 0.17, 0.09), brown=(0.45, 0.28, 0.12), var=0.08, sheen=0.15),
         "oak_leaf": leaf_material("oakleaf", (0.07, 0.24, 0.05), brown=(0.5, 0.3, 0.1)), "maple_leaf": leaf_material("mapleleaf", (0.14, 0.33, 0.07), brown=(0.6, 0.3, 0.08)),
         "birch_bark": birch_material(), "pine_bark": bark_material("pinebark", "pine_bark", (0.75, 0.55, 0.42), 0.8), "oak_bark": bark_material("oakbark", "jolcham_oak_bark_01", (0.7, 0.68, 0.62), 1.0),
         "maple_bark": bark_material("maplebark", "bark_brown_02", (0.75, 0.70, 0.65), 1.0), "root": plain("root", (0.42, 0.30, 0.18), 0.8)}
    S["M"] = M
    meshes = {"tuft": [make_tuft(i, M["grass"]) for i in range(3)], "weed": [make_weed(i, M["weed"]) for i in range(3)],
              "flower": [make_flower(i, [M["flower_stem"], M["flower_head"]]) for i in range(2)], "shrub": [make_shrub(i, [M["shrub"], M["twig"]]) for i in range(3)],
              "trunk": {"birch": make_trunk("trunk_birch", M["birch_bark"], 0.018, 0.004, 0.02, top=0.86), "pine": make_trunk("trunk_pine", M["pine_bark"], 0.022, 0.004, 0.0),
                        "oak": make_trunk("trunk_oak", M["oak_bark"], 0.034, 0.008, 0.03, top=0.82), "maple": make_trunk("trunk_maple", M["maple_bark"], 0.030, 0.007, 0.02, top=0.84)},
              "crown": {k: [make_crown(f"crown_{k}{i}", k, M[{"birch": "birch_leaf", "pine": "pine_needle", "oak": "oak_leaf", "maple": "maple_leaf"}[k]], seed=i) for i in range(2)] for k in ("birch", "pine", "oak", "maple")}}
    P = make_population(); S["P"] = P
    # objects
    for key, mkey in (("grass", "tuft"), ("weeds", "weed"), ("flowers", "flower"), ("shrubs", "shrub")):
        for i, g in enumerate(P[key]):
            ob = link_obj(f"{key}_{i}", meshes[mkey][g["var"]]); ob.location = (g["x"], g["y"], ground_z(g["x"], g["y"]) - 0.01)
            ob.rotation_euler = (0, 0, g["rot"]); ob.scale = (0, 0, 0); ob.hide_render = True; g["ob"] = ob
            if key == "flowers": ob.color = (*g["color"], 1.0)
    for i, t in enumerate(P["trees"]):
        tr = link_obj(f"tree_{i}", meshes["trunk"][t["kind"]]); tr.location = (t["x"], t["y"], ground_z(t["x"], t["y"]) - 0.05); tr.rotation_euler = (0, 0, t["rot"])
        cr = link_obj(f"crown_{i}", meshes["crown"][t["kind"]][i % 2]); cr.parent = tr; cr.rotation_euler = (0, 0, rng.uniform(0, 6.28))
        tr.scale = (0, 0, 0); tr.hide_render = True; cr.hide_render = True; t["ob"] = tr; t["crown"] = cr
        t["root"] = root_curve(f"root_{i}", t["x"], 1.3 if t["cls"] == "pioneer" else 2.4, 1.6 if t["cls"] == "pioneer" else 2.6, M["root"], i) if t["y"] < 1.3 else None
        if t["root"]: t["root"].hide_render = True
    # seeds riding the wind in the first years (and the last, rewinding)
    seed_mat = plain("seed", (0.95, 0.93, 0.88), 0.5); bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0); sm = mesh_obj("seedmesh", bm, seed_mat)
    S["seeds"] = []
    for i in range(70):
        ob = link_obj(f"seed_{i}", sm); S["seeds"].append(dict(ob=ob, x0=rng.uniform(-30, 6), y=rng.uniform(0.5, 12), z0=rng.uniform(0.3, 5.5), ph=rng.uniform(0, 6.28), sp=rng.uniform(0.8, 1.2)))
    # camera
    cam_d = bpy.data.cameras.new("cam"); cam = link_obj("cam", cam_d); cam_d.sensor_fit = "VERTICAL"; cam_d.sensor_height = 36.0; cam_d.clip_end = 500
    cam_d.dof.use_dof = True; focus = link_obj("focus", None); cam_d.dof.focus_object = focus
    S["cam"], S["focus"] = cam, focus; bpy.context.scene.camera = cam
    return S

# ----------------------------------------------------------------------------- per-frame state (pure functions of the year)
def topsoil_depth(Y): return 0.06 + 1.1 * (1 - math.exp(-Y / 50.0))   # diorama-exaggerated so the band visibly thickens
def litter_cover(Y): return smoothstep(28, 70, Y)
def grass_cover(Y): return smoothstep(1.5, 8.0, Y) * (1 - 0.9 * smoothstep(35, 75, Y))

def set_plant(ob, scale, brown=0.0, dead=0.0, bloom=1.0, color=None):
    if (max(scale) if isinstance(scale, tuple) else scale) <= 1e-3:
        if not ob.hide_render: ob.hide_render = True
        return
    if ob.hide_render: ob.hide_render = False
    ob.scale = (scale, scale, scale) if not isinstance(scale, tuple) else scale
    c = color or (brown, 0.0, dead)
    ob.color = (c[0], c[1], c[2], bloom)

def update(t):
    S = STATE["S"]; P = S["P"]; Y = year_at(t); M = S["M"]
    # materials: top cover and the topsoil band
    nt = bpy.data.materials["ground"].node_tree
    nt.nodes["GRASS"].outputs[0].default_value = grass_cover(Y); nt.nodes["LITTER"].outputs[0].default_value = litter_cover(Y); nt.nodes["TOPSOIL"].outputs[0].default_value = topsoil_depth(Y)
    bpy.data.materials["cloudshadow"].node_tree.nodes["cloudmap"].inputs["Location"].default_value = (0.9 * Y + 0.4 * t, 0.25 * Y, 0)
    bpy.context.scene.world.node_tree.nodes["skymap"].inputs["Location"].default_value = (0.02 * Y + 0.004 * t, 0.0, 0)
    # weeds: annuals, one season each; sprout, flower, brown, collapse
    for g in P["weeds"]:
        a = Y - g["t_spawn"]
        if a <= 0 or a > 1.05 or g["t_spawn"] > g.get("shade_death", 999): set_plant(g["ob"], 0); continue
        s = g["s"] * growth(a, 0.12, 1.2) * (1 - smoothstep(0.85, 1.05, a)) ; set_plant(g["ob"], s, brown=smoothstep(0.55, 0.8, a))
    for g in P["grass"]:
        a = Y - g["t_spawn"]; d = Y - g["death"]
        s = g["s"] * growth(a, 0.5, 1.3) * (1 - smoothstep(2.0, 4.0, d)); set_plant(g["ob"], s, brown=smoothstep(0.0, 2.0, d))
    for g in P["flowers"]:
        a = Y - g["t_spawn"]; d = Y - g["death"]; bloom = smoothstep(0.1, 0.25, (Y + g["ph"]) % 1.0) * (1 - smoothstep(0.8, 0.95, (Y + g["ph"]) % 1.0))
        s = g["s"] * growth(a, 0.4, 1.3) * (1 - smoothstep(1.5, 3.0, d)); set_plant(g["ob"], s, bloom=bloom * (1 - smoothstep(0, 1, d)), color=g["color"])
    for g in P["shrubs"]:
        a = Y - g["t_spawn"]; d = Y - g["death"]
        s = g["s"] * growth(a, 5.0, 1.4) * (1 - smoothstep(2.0, 6.0, d)); set_plant(g["ob"], s, brown=smoothstep(0.0, 2.5, d))
    events = []
    for tr in P["trees"]:
        a = Y - tr["t_spawn"]; d = Y - tr["death"]; H = tr["Hmax"] * growth(min(a, tr["death"] - tr["t_spawn"]), tr["tau"])
        ob, cr = tr["ob"], tr["crown"]
        if H < 0.05 or d > 12.0:
            set_plant(ob, 0); cr.hide_render = True
            if tr["root"]: tr["root"].hide_render = True
            continue
        fall = smoothstep(4.0, 5.2, d)
        sink = smoothstep(5.5, 12.0, d)
        set_plant(ob, (H * (1 - 0.35 * sink), H * (1 - 0.35 * sink), H * (1 - 0.85 * sink)), dead=smoothstep(0.5, 3.0, d))
        tilt = math.radians(84) * (fall ** 1.5); ob.rotation_euler = Euler((math.sin(tr["lean"]) * tilt, math.cos(tr["lean"]) * tilt, tr["rot"]), "XYZ")
        ob.location = (tr["x"], tr["y"], ground_z(tr["x"], tr["y"]) - 0.05 - 0.9 * sink * H * 0.06)
        cs = (1 - smoothstep(0.0, 1.6, d)) * smoothstep(0.03, 0.08, H / tr["Hmax"] if tr["Hmax"] else 0)
        if cs <= 1e-3: cr.hide_render = True
        else:
            cr.hide_render = False; cr.scale = (cs, cs, cs); cr.color = (smoothstep(-1.8, 0.0, d), 0, 0, 1)
        if tr["root"]:
            r = tr["root"]; g = H / tr["Hmax"]; r.hide_render = g < 0.02 or sink > 0.9
            r.data.bevel_factor_end = max(0.0, min(1.0, g * 1.1)); r.data.bevel_depth = 0.012 + 0.16 * g * (1 if tr["cls"] == "climax" else 0.45)
            r.data.bevel_depth *= (1 - 0.5 * sink)
    # seeds on the wind: only in the first ~1.6 years (hook, and the tail of the rewind)
    for sd in S["seeds"]:
        ob = sd["ob"]; vis = Y < 1.7
        ob.hide_render = not vis
        if vis:
            tt = Y * 2.4 * sd["sp"]; ob.location = (sd["x0"] + 8.5 * tt, sd["y"], sd["z0"] + 0.5 * math.sin(tt * 2.1 + sd["ph"]) + 0.15 * math.sin(tt * 7 + sd["ph"]))
            ob.scale = (0.07, 0.07, 0.07)
    # camera
    t0, t1 = SHOTS[SHOT]; u = (t - t0) / max(t1 - t0, 1e-6)
    loc, look, lens, fstop = cam_pose(SHOT, u); cam = S["cam"]
    cam.location = loc; cam.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler(); cam.data.lens = lens; cam.data.dof.aperture_fstop = fstop
    S["focus"].location = look

def on_frame(scene):
    f = scene.frame_current; t0, _ = SHOTS[SHOT]; update(t0 + f / FPS)

def setup_render(res, samples):
    sc = bpy.context.scene; sc.render.engine = "CYCLES"; c = sc.cycles
    c.device = "CPU"; c.samples = samples; c.use_adaptive_sampling = True; c.adaptive_threshold = 0.1; c.adaptive_min_samples = 4
    c.use_denoising = True; c.denoiser = "OPENIMAGEDENOISE"; c.denoising_input_passes = "RGB_ALBEDO_NORMAL"; c.denoising_use_gpu = False
    c.max_bounces = 3; c.diffuse_bounces = 1; c.glossy_bounces = 1; c.transmission_bounces = 1; c.volume_bounces = 0; c.transparent_max_bounces = 2   # sunlit exterior + denoise: one diffuse bounce is enough
    c.caustics_reflective = False; c.caustics_refractive = False; c.blur_glossy = 1.0; c.sample_clamp_indirect = 4.0
    sc.render.use_persistent_data = True; sc.render.use_motion_blur = False
    sc.render.resolution_x = res; sc.render.resolution_y = res * 16 // 9; sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGB"; sc.render.image_settings.compression = 20
    sc.render.fps = FPS; sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"   # AgX muted the sky to grey and the greens to pastel
    sc.view_settings.exposure = -0.6
    sc.use_nodes = False

def write_events():
    """build/forest_events.json: shot frame counts and pioneer falls (year) for sfx_cues.py and script.json 'shots'."""
    P = make_population()
    falls = sorted(t["death"] + 4.6 for t in P["trees"] if t["cls"] == "pioneer" and t["death"] < 125)
    ev = {"shots": {s: shot_frames(s) for s in SHOTS}, "spans": {s: list(SHOTS[s]) for s in SHOTS}, "falls": [round(f, 2) for f in falls],
          "n": {k: len(v) for k, v in P.items()}, "bg_plan": {"hook": ["H", 0], "weeds": ["W", 0], "grass": ["G", 0], "shrubs": ["S", 0],
          "pioneers": ["P1", 0, {"cuts": [["P2", 0, 90, shot_frames("P2")]]}], "climax": ["C1", 0, {"cuts": [["C2", 0, 84, shot_frames("C2")]]}],
          "why": ["Y", 0], "ask": ["R", 0], "loop": ["R", BEATS["ask"]["frames"]]}}
    p = os.path.join(VD, "build", "forest_events.json"); json.dump(ev, open(p, "w"), indent=1); print("wrote", p); print(json.dumps(ev["shots"])); print(len(falls), "pioneer falls")

def main():
    if ARGS["list"]: write_events(); return
    t0 = time.time(); clear_scene(); STATE["S"] = build_set(); setup_render(ARGS["res"], ARGS["samples"])
    print(f"BUILD {time.time() - t0:.1f}s, {len(bpy.data.objects)} objects", flush=True)
    bpy.app.handlers.frame_change_pre.clear(); bpy.app.handlers.frame_change_pre.append(on_frame)
    os.makedirs(ARGS["out"], exist_ok=True); sc = bpy.context.scene
    frames = [ARGS["start"]] if ARGS["preview"] else range(ARGS["start"], ARGS["end"] if ARGS["end"] > 0 else shot_frames(SHOT))
    for f in frames:
        path = os.path.join(ARGS["out"], f"{SHOT}_{f:04d}.png")
        if os.path.exists(path) and not ARGS["preview"]: continue
        sc.frame_set(f); sc.render.filepath = path
        t1 = time.time(); bpy.ops.render.render(write_still=True)
        print(f"FRAME {SHOT} {f} {time.time() - t1:.1f}s year {year_at(SHOTS[SHOT][0] + f / FPS):.1f}", flush=True)

main()

"""Video 006: the Odyssey, but everyone is a cat. PS2-era look, fully procedural.

usage: blender -b -P scene_odyssey.py -- --shot A --start 0 --end 88 --out dir [--res 360] [--samples 6] [--fps 30] [--preview]

The look (why it renders in ~1 s/frame on CPU):
  * every material is Emission; lighting is computed in the shader by one shared node group ("PSX":
    colour * (ambient + diffuse * N.L), then linear distance fog). No lights, no bounces, no noise.
  * textures are procedural patterns sampled on SNAPped object coordinates, so they come out as chunky texels.
  * shadows are dark blob discs under characters; render at 360x640 and nearest-neighbour upscale x3.
Shots map 1:1 to beats; events are keyed to spoken words read from the video's timeline.json (W()).
Cats face -Y by default. The ship points +X.
"""
import bpy, bmesh, math, os, sys, json, random, time, argparse
import numpy as np
from mathutils import Vector

ap = argparse.ArgumentParser()
ap.add_argument("--shot", default="A"); ap.add_argument("--start", type=int, default=0); ap.add_argument("--end", type=int, default=1)
ap.add_argument("--out", default="/tmp/ody"); ap.add_argument("--res", type=int, default=360); ap.add_argument("--samples", type=int, default=6)
ap.add_argument("--fps", type=int, default=30); ap.add_argument("--preview", action="store_true")
ARGS = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
SHOT, FPS = ARGS.shot, ARGS.fps
BEAT_OF = {"A": "hook", "B": "home", "C": "cyclops", "D": "winds", "E": "circe", "F": "sirens", "G": "calypso", "H": "suitors", "I": "door"}
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    _tl = json.load(open(os.path.join(ROOT, "videos", "006-cat-odyssey", "build", "timeline.json")))
    BEAT = next(b for b in _tl["beats"] if b["id"] == BEAT_OF[SHOT])
except Exception:
    BEAT = None
def W(word, default, nth=0):
    """Beat-relative spoken time of a word (falls back to `default` without a timeline)."""
    if not BEAT: return default
    n = 0
    for l in BEAT["lines"]:
        for w in l["words"]:
            if "".join(c for c in w["word"].lower() if c.isalnum()) == word:
                if n == nth: return w["start"] - BEAT["start"]
                n += 1
    return default
DUR = BEAT["duration"] if BEAT else 5.0

pi = math.pi
def lerp(a, b, k): return a + (b - a) * k
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def smooth(a, b, x): k = clamp((x - a) / (b - a)); return k * k * (3 - 2 * k)
def vlerp(a, b, k): return tuple(lerp(x, y, k) for x, y in zip(a, b))
def lin(c): return tuple(pow(max(x, 0), 2.2) for x in c[:3])

# ------------------------------------------------------------------ shared lighting group + materials
P = {}
def make_psx():
    g = bpy.data.node_groups.new("PSX", "ShaderNodeTree"); I = g.interface
    I.new_socket(name="Color", in_out="INPUT", socket_type="NodeSocketColor")
    s = I.new_socket(name="Fog", in_out="INPUT", socket_type="NodeSocketFloat"); s.default_value = 1.0
    I.new_socket(name="Color", in_out="OUTPUT", socket_type="NodeSocketColor")
    N, L = g.nodes.new, g.links.new; gi = N("NodeGroupInput"); go = N("NodeGroupOutput")
    geo = N("ShaderNodeNewGeometry"); ld = N("ShaderNodeCombineXYZ"); dot = N("ShaderNodeVectorMath"); dot.operation = "DOT_PRODUCT"
    L(geo.outputs["Normal"], dot.inputs[0]); L(ld.outputs[0], dot.inputs[1])
    cl = N("ShaderNodeClamp"); L(dot.outputs["Value"], cl.inputs["Value"])
    amb, dif, fogc = N("ShaderNodeRGB"), N("ShaderNodeRGB"), N("ShaderNodeRGB")
    sc = N("ShaderNodeVectorMath"); sc.operation = "SCALE"; L(dif.outputs[0], sc.inputs[0]); L(cl.outputs[0], sc.inputs["Scale"])
    ad = N("ShaderNodeVectorMath"); ad.operation = "ADD"; L(sc.outputs[0], ad.inputs[0]); L(amb.outputs[0], ad.inputs[1])
    mu = N("ShaderNodeVectorMath"); mu.operation = "MULTIPLY"; L(gi.outputs["Color"], mu.inputs[0]); L(ad.outputs[0], mu.inputs[1])
    cam = N("ShaderNodeCameraData"); mr = N("ShaderNodeMapRange"); L(cam.outputs["View Z Depth"], mr.inputs[0])
    fm = N("ShaderNodeMath"); fm.operation = "MULTIPLY"; L(mr.outputs[0], fm.inputs[0]); L(gi.outputs["Fog"], fm.inputs[1])
    mix = N("ShaderNodeMixRGB"); L(fm.outputs[0], mix.inputs["Fac"]); L(mu.outputs[0], mix.inputs["Color1"]); L(fogc.outputs[0], mix.inputs["Color2"])
    L(mix.outputs[0], go.inputs[0])
    P.update(group=g, ld=ld, amb=amb, dif=dif, fog=fogc, mr=mr)
def light(d=(0.45, -0.6, 0.66), amb=(0.5, 0.52, 0.6), dif=(0.75, 0.7, 0.6), fog=(0.7, 0.8, 0.95), f0=30.0, f1=160.0):
    v = Vector(d).normalized()
    for i in range(3): P["ld"].inputs[i].default_value = v[i]
    P["amb"].outputs[0].default_value = (*amb, 1); P["dif"].outputs[0].default_value = (*dif, 1); P["fog"].outputs[0].default_value = (*lin(fog), 1)
    P["mr"].inputs[1].default_value = f0; P["mr"].inputs[2].default_value = f1
    bpy.context.scene.world.node_tree.nodes["Background"].inputs[0].default_value = (*lin(fog), 1)

MATS, MAPS = {}, {}
def mat(name, col, kind="flat", col2=None, col3=None, scale=4.0, texel=16.0, axis=2, thr=0.5, thr2=0.8, wob=0.0, alpha=1.0, lit=True, fog=1.0):
    """kind: flat | noise | stripes (bands along `axis`, wobbled by noise) | checker. Patterns use snapped object coords."""
    if name in MATS: return MATS[name]
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear(); N, L = nt.nodes.new, nt.links.new
    out = N("ShaderNodeOutputMaterial"); em = N("ShaderNodeEmission")
    if kind == "flat":
        n = N("ShaderNodeRGB"); n.outputs[0].default_value = (*lin(col), 1); cs = n.outputs[0]
    else:
        tc = N("ShaderNodeTexCoord"); mp = N("ShaderNodeMapping"); L(tc.outputs["Object"], mp.inputs["Vector"]); MAPS[name] = mp
        sn = N("ShaderNodeVectorMath"); sn.operation = "SNAP"; L(mp.outputs[0], sn.inputs[0]); sn.inputs[1].default_value = (1 / texel,) * 3
        if kind == "checker":
            ck = N("ShaderNodeTexChecker"); L(sn.outputs[0], ck.inputs["Vector"]); ck.inputs["Scale"].default_value = scale
            ck.inputs["Color1"].default_value = (*lin(col), 1); ck.inputs["Color2"].default_value = (*lin(col2), 1); cs = ck.outputs["Color"]
        else:
            nz = N("ShaderNodeTexNoise"); L(sn.outputs[0], nz.inputs["Vector"]); nz.inputs["Detail"].default_value = 1.0
            if kind == "noise":
                nz.inputs["Scale"].default_value = scale; fac = nz.outputs[0]
            else:
                nz.inputs["Scale"].default_value = 2.5; sep = N("ShaderNodeSeparateXYZ"); L(sn.outputs[0], sep.inputs[0])
                m1 = N("ShaderNodeMath"); m1.operation = "MULTIPLY_ADD"; L(nz.outputs[0], m1.inputs[0]); m1.inputs[1].default_value = wob; L(sep.outputs[axis], m1.inputs[2])
                m2 = N("ShaderNodeMath"); m2.operation = "MULTIPLY"; L(m1.outputs[0], m2.inputs[0]); m2.inputs[1].default_value = scale
                m3 = N("ShaderNodeMath"); m3.operation = "FRACT"; L(m2.outputs[0], m3.inputs[0]); fac = m3.outputs[0]
            ramp = N("ShaderNodeValToRGB"); cr = ramp.color_ramp; cr.interpolation = "CONSTANT"
            cr.elements[0].position = 0.0; cr.elements[0].color = (*lin(col), 1); cr.elements[1].position = thr; cr.elements[1].color = (*lin(col2), 1)
            if col3: e = cr.elements.new(thr2); e.color = (*lin(col3), 1)
            L(fac, ramp.inputs["Fac"]); cs = ramp.outputs["Color"]
    if lit:
        g = N("ShaderNodeGroup"); g.node_tree = P["group"]; L(cs, g.inputs["Color"]); g.inputs["Fog"].default_value = fog; cs = g.outputs[0]
    L(cs, em.inputs["Color"])
    if alpha < 1:
        tr = N("ShaderNodeBsdfTransparent"); mx = N("ShaderNodeMixShader"); mx.inputs[0].default_value = alpha
        L(tr.outputs[0], mx.inputs[1]); L(em.outputs[0], mx.inputs[2]); L(mx.outputs[0], out.inputs[0])
    else: L(em.outputs[0], out.inputs[0])
    MATS[name] = m; return m

# ------------------------------------------------------------------ geometry helpers
def new_obj(name, bm, m=None, parent=None, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), smooth_=True):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = smooth_
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    if m: me.materials.append(m)
    ob.parent = parent; ob.location = loc; ob.rotation_euler = rot; ob.scale = scale if isinstance(scale, (tuple, list)) else (scale,) * 3
    return ob
def sph(name, m, r, loc=(0, 0, 0), parent=None, seg=8, rings=6, **k):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0); return new_obj(name, bm, m, parent, loc, scale=r, **k)
def ico(name, m, r, loc=(0, 0, 0), parent=None, sub=1, jitter=0.0, seed=1, **k):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0); rng = random.Random(seed)
    for v in bm.verts: v.co *= 1 + rng.uniform(-jitter, jitter)
    k.setdefault("smooth_", False); return new_obj(name, bm, m, parent, loc, scale=r, **k)
def box(name, m, size, loc=(0, 0, 0), parent=None, **k):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0); k.setdefault("smooth_", False); return new_obj(name, bm, m, parent, loc, scale=size, **k)
def cone(name, m, r1, r2, depth, loc=(0, 0, 0), parent=None, seg=6, **k):
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r1, radius2=r2, depth=depth)
    k.setdefault("smooth_", False); return new_obj(name, bm, m, parent, loc, **k)
def empty(name, parent=None, loc=(0, 0, 0), rot=(0, 0, 0)):
    ob = bpy.data.objects.new(name, None); bpy.context.scene.collection.objects.link(ob); ob.parent = parent; ob.location = loc; ob.rotation_euler = rot; return ob
def facing(dx, dy): return math.atan2(dx, -dy)   # z-rotation that turns a cat (default -Y) toward (dx, dy)

# ------------------------------------------------------------------ characters
FURS = {"orange": ((0.95, 0.56, 0.16), (0.72, 0.32, 0.06)), "grey": ((0.62, 0.62, 0.66), (0.34, 0.34, 0.4)), "black": ((0.13, 0.13, 0.16), (0.2, 0.2, 0.24)),
        "white": ((0.96, 0.95, 0.92), (0.86, 0.84, 0.8)), "brown": ((0.5, 0.36, 0.24), (0.3, 0.2, 0.12)), "cream": ((0.93, 0.84, 0.66), (0.78, 0.62, 0.42)),
        "calico": ((0.96, 0.94, 0.9), (0.9, 0.5, 0.14)), "dog": ((0.82, 0.62, 0.36), (0.62, 0.42, 0.2)), "cyclops": ((0.5, 0.52, 0.6), (0.3, 0.31, 0.4))}
def cat(name, fur="orange", size=1.0, parent=None, loc=(0, 0, 0), rz=0.0, eye=(0.62, 0.85, 0.2), species="cat", eyes=2, helmet=False, hat=None, wings=False, shadow=True):
    c1, c2 = FURS[fur]; R = empty(name, parent, loc, (0, 0, rz)); R.scale = (size,) * 3
    if fur == "calico": fm = mat("fur_calico", c1, "noise", c2, (0.15, 0.13, 0.14), scale=1.6, texel=10, thr=0.52, thr2=0.62)
    elif fur in ("white", "black", "dog"): fm = mat("fur_" + fur, c1, "noise", c2, scale=2.0, texel=10, thr=0.55)
    else: fm = mat("fur_" + fur, c1, "stripes", c2, scale=2.6, texel=12, axis=2, thr=0.62, wob=0.5)
    wm = mat("cat_white", (0.97, 0.96, 0.93)); km = mat("cat_black", (0.05, 0.05, 0.07)); pm = mat("cat_pink", (0.95, 0.5, 0.55))
    B = empty(name + "_b", R)
    sph("body", fm, (0.26, 0.24, 0.32), (0, 0, 0.40), B); sph("belly", wm if fur != "black" else fm, (0.17, 0.10, 0.22), (0, -0.165, 0.37), B)
    for s in (-1, 1): sph("foot", wm, (0.10, 0.15, 0.07), (s * 0.14, -0.12, 0.07), R)
    arms = []
    for s in (-1, 1):
        a = empty("arm", B, (s * 0.27, -0.03, 0.60)); sph("arm", fm, (0.075, 0.075, 0.17), (0, 0, -0.13), a); sph("paw", wm, (0.08, 0.08, 0.07), (0, 0, -0.29), a); arms.append(a)
    tail = []; tp = B
    for i in range(3):
        t = empty("tail", tp, (0, 0.2, 0.18) if i == 0 else (0, 0, 0.21), (-1.0 if i == 0 else 0.35, 0, 0)); sph("tail", fm if i < 2 else (wm if fur in ("calico", "orange") else fm), (0.055, 0.055, 0.13), (0, 0, 0.105), t); tail.append(t); tp = t
    H = empty(name + "_h", B, (0, 0, 0.66))
    sph("head", fm, (0.40, 0.34, 0.33), (0, 0, 0.26), H, seg=10, rings=7)
    em = mat("eye_%d_%d" % (int(eye[0] * 99), int(eye[1] * 99)), eye); irises, pupils = [], []
    if species == "cat":
        sph("muzzle", wm, (0.13, 0.08, 0.09), (0, -0.30, 0.17), H); sph("nose", pm, (0.04, 0.03, 0.03), (0, -0.375, 0.21), H)
        for s in (-1, 1): cone("ear", fm, 0.13, 0.0, 0.24, (s * 0.23, 0.02, 0.60), H, seg=4, rot=(0, s * 0.3, 0.78))
    else:   # dog: long snout, floppy ears, tongue
        sph("snout", wm, (0.14, 0.17, 0.12), (0, -0.36, 0.17), H); sph("nose", km, (0.06, 0.05, 0.05), (0, -0.52, 0.22), H)
        tg = box("tongue", pm, (0.08, 0.03, 0.16), (0.02, -0.45, 0.04), H); c2m = mat("dog_ear", c2)
        for s in (-1, 1): sph("ear", c2m, (0.07, 0.12, 0.20), (s * 0.40, 0.0, 0.25), H)
    ex = [0.0] if eyes == 1 else [-0.165, 0.165]; er = 0.16 if eyes == 1 else 0.092
    for x in ex:
        if species == "dog":
            irises.append(sph("eye", km, (0.06, 0.03, 0.07), (x, -0.315, 0.31), H)); pupils.append(sph("glint", wm, (0.018, 0.01, 0.018), (x + 0.02, -0.345, 0.335), H))
        else:
            yy = -0.305 - (0.02 if eyes == 1 else 0); irises.append(sph("eye", em, (er, 0.04, er * 1.08), (x, yy, 0.30), H)); pupils.append(sph("pupil", km, (er * 0.36, 0.03, er * 0.86), (x, yy - 0.025, 0.30), H))
    if helmet:
        bz = mat("bronze", (1.0, 0.84, 0.25), "noise", (0.86, 0.66, 0.14), scale=2.0, texel=8, thr=0.6)
        sph("helmet", bz, (0.43, 0.37, 0.24), (0, 0.02, 0.44), H, seg=10); box("guard", bz, (0.06, 0.05, 0.22), (0, -0.36, 0.40), H)
        cone("crest", mat("crest", (0.85, 0.12, 0.12)), 0.37, 0.37, 0.11, (0, 0.06, 0.50), H, seg=10, rot=(0, pi / 2, 0))
    if hat == "witch":
        hm = mat("witch", (0.42, 0.16, 0.6)); cone("brim", hm, 0.52, 0.52, 0.04, (0, 0, 0.52), H, seg=10); cone("hatc", hm, 0.3, 0.0, 0.7, (0, 0.04, 0.88), H, seg=6, rot=(-0.2, 0, 0))
        cone("band", mat("gold", (0.98, 0.8, 0.2)), 0.31, 0.29, 0.07, (0, 0, 0.57), H, seg=6)
    if hat == "flowers":
        for i in range(7): a = i / 7 * 2 * pi; sph("fl", mat("flower%d" % (i % 2), (1.0, 0.45, 0.65) if i % 2 else (1.0, 0.85, 0.3)), 0.075, (0.3 * math.cos(a), 0.26 * math.sin(a), 0.53), H, seg=6, rings=4)
    if hat == "plugs":
        for s in (-1, 1): sph("plug", mat("wax", (1.0, 0.85, 0.25)), 0.07, (s * 0.37, 0.0, 0.34), H, seg=6, rings=4)
    wg = []
    if wings:
        for s in (-1, 1):
            w = empty("wing", B, (s * 0.12, 0.2, 0.62)); cone("wing", mat("wing", (0.98, 0.97, 1.0)), 0.2, 0.0, 0.7, (s * 0.36, 0, 0.12), w, seg=4, rot=(0, s * 1.2, 0), scale=(1, 0.25, 1)); wg.append(w)
    if shadow: cone("shadow", mat("shadow", (0, 0, 0), alpha=0.35, lit=False), 0.36, 0.36, 0.005, (0, 0, 0.012), R, seg=10)
    return dict(root=R, body=B, head=H, arms=arms, tail=tail, irises=irises, pupils=pupils, wings=wg, size=size, base=tuple(loc), species=species)

def pose(c, t, armL=0.0, armR=0.0, side=0.0, yaw=0.0, pitch=0.0, roll=0.0, wag=0.5, wagf=3.0, lean=0.0, blink=None, pupil=1.0, breathe=True, ph=0.0):
    """armL/armR = forward raise (radians), side = outward raise; blink 0..1 closes the eyes (None = automatic)."""
    c["arms"][0].rotation_euler = (-armL, -side, 0); c["arms"][1].rotation_euler = (-armR, side, 0)
    c["head"].rotation_euler = (pitch, roll, yaw)
    for i, tl in enumerate(c["tail"]): tl.rotation_euler = ((-1.0 if i == 0 else 0.35), wag * math.sin(t * wagf + ph - i * 0.7), 0)
    c["body"].rotation_euler = (lean, 0, 0); c["body"].scale = (1, 1, 1 + (0.025 * math.sin(t * 3.1 + ph) if breathe else 0))
    if blink is None: blink = 1.0 if ((t + ph * 1.7) % 2.9) < 0.11 else 0.0
    for ir, pu in zip(c["irises"], c["pupils"]):
        ir.scale.z = ir.scale.x * 1.08 * max(0.08, 1 - blink) if c["species"] == "cat" else 0.07 * max(0.15, 1 - blink)
        if c["species"] == "cat": pu.scale = (ir.scale.x * 0.36 * pupil, 0.03, ir.scale.x * 0.86 * max(0.05, 1 - blink))
def place(c, loc, rz=None, on=True):
    c["root"].location = loc if on else (0, 0, -500)
    if rz is not None: c["root"].rotation_euler.z = rz

def sheep(name, loc=(0, 0, 0)):
    R = empty(name, None, loc); wool = mat("wool", (0.97, 0.96, 0.92), "noise", (0.84, 0.83, 0.8), scale=3, texel=8); km = mat("cat_black", (0.05, 0.05, 0.07))
    ico("wool", wool, (0.62, 0.42, 0.40), (0, 0, 0.82), R, sub=2, jitter=0.12, seed=hash(name) % 99); H = empty("sh", R, (0.6, 0, 0.9))
    sph("head", km, (0.2, 0.15, 0.17), (0.12, 0, 0.02), H); sph("tuft", wool, (0.14, 0.13, 0.1), (0.04, 0, 0.16), H, seg=6, rings=4)
    for s in (-1, 1): sph("eye", mat("cat_white", (1, 1, 1)), 0.035, (0.26, s * 0.09, 0.07), H, seg=6, rings=4); sph("ear", km, (0.05, 0.1, 0.04), (0.02, s * 0.2, 0.05), H, seg=6, rings=4)
    legs = [empty("leg", R, (x, y, 0.5)) for x in (-0.35, 0.35) for y in (-0.2, 0.2)]
    for l in legs: box("leg", km, (0.09, 0.09, 0.5), (0, 0, -0.25), l)
    cone("shadow", mat("shadow", (0, 0, 0), alpha=0.35, lit=False), 0.75, 0.75, 0.005, (0, 0, 0.012), R, seg=10, scale=(1, 0.65, 1))
    return dict(root=R, head=H, legs=legs)

POOFS = []
def make_poofs(n=14):
    pm = mat("poof", (1, 1, 1), lit=False, alpha=0.9)
    for i in range(n): POOFS.append(ico("poof", pm, 0.4, (0, 0, -500), sub=1, jitter=0.1, seed=i, smooth_=True))
def poof(i, pos, k, r=0.8, drift=(0, 0, 0.6)):
    p = POOFS[i % len(POOFS)]
    if k <= 0 or k >= 1: p.location = (0, 0, -500); return
    p.location = (pos[0] + drift[0] * k, pos[1] + drift[1] * k, pos[2] + drift[2] * k); s = r * math.sin(pi * k ** 0.6); p.scale = (s, s, s * 0.85); p.rotation_euler = (k * 2, i, k * 3)

# ------------------------------------------------------------------ sets
S = {}
def sky(horizon=(0.75, 0.86, 0.98), zenith=(0.2, 0.45, 0.9), sun=True, clouds=True):
    m = bpy.data.materials.new("sky"); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear(); N, L = nt.nodes.new, nt.links.new
    tc = N("ShaderNodeTexCoord"); sep = N("ShaderNodeSeparateXYZ"); L(tc.outputs["Object"], sep.inputs[0]); ramp = N("ShaderNodeValToRGB"); L(sep.outputs[2], ramp.inputs["Fac"])
    cr = ramp.color_ramp; cr.elements[0].position = 0.0; cr.elements[1].position = 0.55; em = N("ShaderNodeEmission"); out = N("ShaderNodeOutputMaterial")
    L(ramp.outputs[0], em.inputs["Color"]); L(em.outputs[0], out.inputs[0]); S["sky_ramp"] = cr
    sph("skydome", m, 400.0, seg=16, rings=12); set_sky(horizon, zenith)
    if sun: S["sun"] = sph("sun", mat("sun", (1.0, 0.97, 0.75), lit=False), 14.0, (150, 260, 120), seg=12, rings=8)
    if clouds:
        cm = mat("cloud", (1, 1, 1), fog=0.0); rng = random.Random(4)
        for i in range(9):
            a = rng.uniform(0, 2 * pi); d = rng.uniform(170, 260); c0 = Vector((d * math.cos(a), d * math.sin(a), rng.uniform(35, 90)))
            for j in range(3): ico("cloud", cm, (rng.uniform(16, 26), rng.uniform(16, 26), rng.uniform(5, 8)), c0 + Vector((rng.uniform(-18, 18), rng.uniform(-18, 18), rng.uniform(-2, 3))), sub=1, jitter=0.15, seed=i * 3 + j)
def set_sky(horizon, zenith):
    S["sky_ramp"].elements[0].color = (*lin(horizon), 1); S["sky_ramp"].elements[1].color = (*lin(zenith), 1)

def sea():
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=56, y_segments=56, size=1.0)
    for v in bm.verts: v.co.x = 230 * v.co.x * (0.12 + 0.88 * abs(v.co.x)); v.co.y = 230 * v.co.y * (0.12 + 0.88 * abs(v.co.y))   # dense near the ship
    wm = mat("water", (0.05, 0.36, 0.72), "noise", (0.1, 0.5, 0.85), (0.55, 0.85, 0.98), scale=0.35, texel=2.5, thr=0.5, thr2=0.69)
    ob = new_obj("sea", bm, wm, smooth_=False); n = len(ob.data.vertices); co = np.zeros(n * 3); ob.data.vertices.foreach_get("co", co)
    S["sea"] = ob; S["sea_xy"] = co.reshape(-1, 3).copy()
def wave(x, y, t, amp=1.0):
    return amp * (0.20 * np.sin(0.33 * x + 1.3 * t) + 0.12 * np.sin(0.55 * y + 0.21 * x + 1.8 * t) + 0.06 * np.sin(1.05 * x - 0.7 * y + 2.4 * t))
def sea_update(t, speed=3.0, amp=1.0, calm_r=5.0):
    b = S["sea_xy"]; x, y = b[:, 0], b[:, 1]; r = np.sqrt(x * x + y * y); k = 0.3 + 0.7 * np.clip((r - calm_r) / 6.0, 0, 1)   # calmer under the hull so waves stay out of the deck
    co = b.copy(); co[:, 2] = wave(x + speed * t, y, t, amp) * k; S["sea"].data.vertices.foreach_set("co", co.ravel()); S["sea"].data.update()
    MAPS["water"].inputs["Location"].default_value = (speed * t, 0.15 * t, 0.3 * t)

def ship(crew_furs=("grey", "black", "calico", "white", "cream", "brown"), plugs=False, hero_at_prow=True):
    R = empty("ship"); wood = mat("hull", (0.5, 0.3, 0.15), "stripes", (0.36, 0.2, 0.09), scale=5.0, texel=24, axis=2, thr=0.82)
    red = mat("shipred", (0.78, 0.16, 0.12)); dark = mat("wood_dark", (0.3, 0.17, 0.08))
    bm = bmesh.new(); n = 11; rows = []
    for i in range(n):
        x = -3.5 + 7.0 * i / (n - 1); w = 1.12 * (1 - (x / 3.75) ** 2) ** 0.55; sheer = 0.75 * abs(x / 3.5) ** 3
        rows.append([bm.verts.new((x, y * w, z + sheer)) for y, z in ((-1, 0.5), (-0.86, -0.05), (0, -0.5), (0.86, -0.05), (1, 0.5))])
    for i in range(n - 1):
        for j in range(4): bm.faces.new((rows[i][j], rows[i + 1][j], rows[i + 1][j + 1], rows[i][j + 1]))
    new_obj("hull", bm, wood, R, smooth_=False)
    box("deck", mat("deck", (0.72, 0.55, 0.32), "stripes", (0.6, 0.44, 0.24), scale=4, texel=16, axis=1, thr=0.85), (5.6, 1.7, 0.06), (0, 0, -0.06), R)
    box("foredeck", dark, (1.3, 1.3, 0.3), (2.55, 0, 0.1), R)
    for i, (dx, dz, a) in enumerate(((3.55, 1.5, 0.25), (3.75, 2.25, -0.25), (3.55, 2.75, -1.0))): box("stem", red, (0.22, 0.2, 0.9), (dx, 0, dz), R, rot=(0, a, 0))
    for i, (dx, dz, a) in enumerate(((-3.55, 1.6, -0.2), (-3.65, 2.4, 0.35), (-3.3, 2.95, 1.1))): box("stern", red, (0.22, 0.2, 1.0), (dx, 0, dz), R, rot=(0, a, 0))
    for s in (-1, 1):   # painted eye on the bow, shields along the rail
        sph("boweye", mat("cat_white", (1, 1, 1)), (0.2, 0.03, 0.14), (2.75, s * 0.74, 0.62), R); sph("boweyep", mat("cat_black", (0, 0, 0)), (0.09, 0.03, 0.09), (2.79, s * 0.77, 0.62), R)
        for i in range(5): cone("shield", mat("shield%d" % (i % 3), ((0.85, 0.2, 0.15), (0.95, 0.75, 0.2), (0.2, 0.4, 0.75))[i % 3]), 0.27, 0.27, 0.05, (-2.2 + i * 0.95, s * (1.13 - 0.02 * (i - 2) ** 2 * 2), 0.42), R, seg=8, rot=(pi / 2, 0, 0))
    cone("mast", dark, 0.09, 0.07, 4.4, (0.2, 0, 2.2), R, seg=6); box("yard", dark, (0.1, 3.5, 0.1), (0.2, 0, 4.1), R)
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=7, y_segments=7, size=1.0)
    sail = new_obj("sail", bm, mat("sail", (0.96, 0.93, 0.84), "stripes", (0.82, 0.18, 0.14), scale=1.25, texel=16, axis=1, thr=0.6), R, (0.3, 0, 2.55), smooth_=True)
    co = np.zeros(len(sail.data.vertices) * 3); sail.data.vertices.foreach_get("co", co); S["sail"] = sail; S["sail_uv"] = co.reshape(-1, 3).copy()
    oars = []
    for s in (-1, 1):
        for i in range(4):
            o = empty("oar", R, (-2.0 + i * 1.1, s * 1.05, 0.5)); box("oar", dark, (0.07, 2.6, 0.07), (0, s * 1.2, 0), o); box("blade", mat("blade", (0.9, 0.85, 0.7)), (0.26, 0.6, 0.05), (0, s * 2.5, 0), o); oars.append((o, s, i))
    crew = []
    for i, f in enumerate(crew_furs):
        x = (-2.2, -2.2, -1.1, -1.1, 1.2, 1.2)[i]; y = (-0.48, 0.48)[i % 2]
        crew.append(cat("crew%d" % i, f, 0.82, R, (x, y, -0.03), rz=facing(1, 0), hat="plugs" if plugs else None, shadow=False))
    hero = cat("hero", "orange", 0.95, R, (2.5, 0, 0.25) if hero_at_prow else (0.62, 0, -0.03), rz=facing(1, 0), helmet=True, shadow=False)
    S.update(ship=R, oars=oars, crew=crew, hero=hero); return R
def ship_update(t, amp=1.0, billow=1.0, row=True, roll=0.0, flap=0.0):
    R = S["ship"]; R.location = (0, 0, 0.42 + 0.10 * amp * math.sin(1.3 * t)); R.rotation_euler = (0.05 * amp * math.sin(1.1 * t + 1) + roll, -0.04 * amp * math.sin(1.3 * t + 0.6), 0)
    uv = S["sail_uv"]; u, v = uv[:, 0], uv[:, 1]; co = np.zeros_like(uv)   # grid x -> ship Y (width), grid y -> Z (height), billow toward +X
    co[:, 1] = u * 1.55; co[:, 2] = v * 1.45; belly = np.cos(u * pi / 2) * np.cos(v * pi / 2 * 0.9)
    co[:, 0] = billow * 0.55 * belly + (0.04 + flap) * np.sin(3 * v + 7 * t + 2 * u) * (1 - v) * 0.5
    S["sail"].data.vertices.foreach_set("co", co.ravel()); S["sail"].data.update()
    for o, s, i in S["oars"]:
        ph = 3.2 * t + i * 0.25; o.rotation_euler = (-s * (0.42 + (0.16 * math.cos(ph) if row else -0.25)), 0, s * (0.4 * math.sin(ph) if row else 0.0))
def crew_row(t, wide=False, scared=0.0):
    for i, c in enumerate(S["crew"]):
        k = math.sin(3.2 * t + i * 0.25 + 0.5)
        pose(c, t, armL=0.9 + 0.35 * k, armR=0.9 + 0.35 * k, lean=0.12 * k, ph=i * 1.3, pupil=1.0 + 1.2 * scared, yaw=scared * 0.5 * math.sin(9 * t + i))

def island(center=(0, 0, 0), r=9.0, palms=3, house=False, hill=True, seed=1):
    R = empty("island", None, center); rng = random.Random(seed)
    cone("sand", mat("sand", (0.96, 0.86, 0.6), "noise", (0.88, 0.76, 0.5), scale=1.2, texel=4), r * 1.25, r, 1.6, (0, 0, -0.2), R, seg=12)
    if hill: ico("hill", mat("grass", (0.3, 0.68, 0.25), "noise", (0.2, 0.55, 0.2), scale=3, texel=5), (r * 0.6, r * 0.45, r * 0.42), (0, r * 0.55, 0.3), R, sub=1, jitter=0.12, seed=seed)
    tr = mat("trunk", (0.55, 0.38, 0.2), "stripes", (0.4, 0.27, 0.13), scale=3, texel=12, thr=0.7); lf = mat("leaf", (0.2, 0.62, 0.22)); S["palms"] = []
    for i in range(palms):
        a = rng.uniform(0.3, 2.8); d = rng.uniform(0.45, 0.8) * r; px, py = d * math.cos(a), d * math.sin(a) * 0.8 + r * 0.1; h = rng.uniform(3.0, 4.2); top = empty("ptop", R, (px + 0.4, py, 0.6 + h))
        cone("trunk", tr, 0.2, 0.13, h, (px + 0.2, py, 0.6 + h / 2), R, seg=5, rot=(0, 0.1, 0))
        for j in range(6): b = j / 6 * 2 * pi; cone("leaf", lf, 0.34, 0.0, 2.0, (0.8 * math.cos(b), 0.8 * math.sin(b), -0.22), top, seg=4, rot=(0, pi / 2 + 0.35, b), scale=(0.3, 1, 1))
        S["palms"].append(top)
    if house:
        box("house", mat("plaster", (0.97, 0.95, 0.88)), (1.8, 1.5, 1.2), (-r * 0.3, r * 0.2, 1.2), R); cone("roof", mat("roof", (0.8, 0.3, 0.18)), 1.5, 0.0, 0.9, (-r * 0.3, r * 0.2, 2.25), R, seg=4, rot=(0, 0, pi / 4))
    return R

def hall(door_y=None):
    box("floor", mat("tiles", (0.86, 0.8, 0.68), "checker", (0.6, 0.3, 0.22), scale=0.5, texel=16), (40, 40, 0.1), (0, 0, -0.05))
    wall = mat("wall", (0.9, 0.82, 0.66), "noise", (0.84, 0.75, 0.58), scale=2, texel=6); col = mat("column", (0.97, 0.95, 0.9), "stripes", (0.82, 0.8, 0.76), scale=5, texel=16, axis=0, thr=0.75)
    box("wall", wall, (40, 0.4, 9), (0, 4.6, 4.5)); box("frieze", mat("frieze", (0.2, 0.35, 0.7), "stripes", (0.95, 0.8, 0.3), scale=1.2, texel=10, axis=0, thr=0.5), (40, 0.45, 0.5), (0, 4.58, 3.6))
    for x in (-7.5, -4.5, -1.5, 1.5, 4.5, 7.5):
        cone("col", col, 0.36, 0.3, 4.6, (x, 3.9, 2.3), seg=8); box("cap", col, (0.95, 0.95, 0.22), (x, 3.9, 4.7)); box("base", col, (0.9, 0.9, 0.2), (x, 3.9, 0.1))
        if x % 3: cone("torch", mat("fire", (1.0, 0.7, 0.2), lit=False), 0.14, 0.0, 0.45, (x + 1.5, 4.3, 2.6), seg=5)
def big_door(y, facing_y=-1):
    """A wall across the room at y with tall double doors; planks, bronze bands, ring handles."""
    wall = mat("wall", (0.9, 0.82, 0.66), "noise", (0.84, 0.75, 0.58), scale=2, texel=6); pl = mat("doorwood", (0.5, 0.3, 0.14), "stripes", (0.38, 0.21, 0.09), scale=2.2, texel=16, axis=0, thr=0.86)
    for sx in (-1, 1): box("dwall", wall, (16, 0.5, 9), (sx * 9.6, y, 4.5))
    box("lintel", wall, (3.4, 0.5, 4.6), (0, y, 6.7)); bz = mat("bronze2", (0.85, 0.62, 0.2))
    box("frame", mat("stonef", (0.75, 0.72, 0.68)), (3.7, 0.6, 0.35), (0, y, 4.55))
    for sx in (-1, 1): box("jamb", mat("stonef", (0.75, 0.72, 0.68)), (0.3, 0.6, 4.4), (sx * 1.72, y, 2.2))
    S["doors"] = []
    for sx in (-1, 1):
        hinge = empty("hinge", None, (sx * 1.58, y + facing_y * 0.1, 0)); d = box("door", pl, (1.56, 0.14, 4.38), (-sx * 0.78, 0, 2.19), hinge)
        for z in (0.7, 2.2, 3.7): box("band", bz, (1.56, 0.17, 0.14), (-sx * 0.78, 0, z), hinge)
        cone("ring", bz, 0.13, 0.13, 0.06, (-sx * 1.3, facing_y * 0.1, 1.75), hinge, seg=8, rot=(pi / 2, 0, 0)); S["doors"].append((hinge, sx))

# ------------------------------------------------------------------ camera
def make_cam():
    cd = bpy.data.cameras.new("cam"); cam = bpy.data.objects.new("cam", cd); bpy.context.scene.collection.objects.link(cam); bpy.context.scene.camera = cam
    cd.shift_y = -0.12; cd.clip_start = 0.05; cd.clip_end = 2000; tgt = empty("camtgt"); c = cam.constraints.new("TRACK_TO"); c.target = tgt; c.track_axis = "TRACK_NEGATIVE_Z"; c.up_axis = "UP_Y"
    S["cam"], S["tgt"] = cam, tgt
def cam(loc, tgt, lens=35.0, shake=0.0, t=0.0, shift=-0.12):
    S["cam"].data.shift_y = shift   # negative = subject higher in frame (captions sit at y=1150, HUD above y=460)
    S["cam"].location = Vector(loc) + shake * Vector((math.sin(t * 37), math.sin(t * 29 + 1), math.sin(t * 43 + 2))); S["tgt"].location = tgt; S["cam"].data.lens = lens

# ------------------------------------------------------------------ shots (each: build() returns update(t), t in seconds from the beat start)
def shot_A():   # hook: hero cat at the prow, ship coming at the camera; snap in on "cat"
    light(); sky(); sea(); ship(); tc = W("cat", 2.0)
    def up(t):
        sea_update(t); ship_update(t); crew_row(t); h = S["hero"]; k = smooth(tc - 0.25, tc + 0.1, t)
        pose(h, t, armL=0.2, armR=1.9 * smooth(0.2, 0.7, t) * (1 - 0.6 * k), side=0.2, yaw=lerp(0.0, -0.75, k), pitch=-0.12, wag=0.7, blink=1.0 if tc + 0.45 < t < tc + 0.58 else 0.0, pupil=lerp(1.0, 1.7, k))
        z = 0.42 + 0.10 * math.sin(1.3 * t)
        cam(vlerp((6.3 - 0.35 * t, -3.2, 1.5), (5.2, -2.3, 1.75 + z * 0.5), k), vlerp((2.1, 0, 1.75), (2.55, 0, 1.5 + z * 0.6), k), lerp(34, 52, k))
    return up

def shot_B():   # home: wide of the ship rowing, then look ahead to Ithaca, which slides away on "ten years"
    light(); sky(); sea(); ship(); isl = island((70, 6, 0), 10, palms=2, house=True, seed=3); tn, tt = W("now", 2.2), W("ten", 4.2)
    def up(t):
        sea_update(t); ship_update(t); crew_row(t); h = S["hero"]; k = smooth(tn - 0.2, tn + 0.5, t); kt = smooth(tt - 0.1, tt + 1.2, t)
        pose(h, t, armR=1.5 * k * (1 - kt), side=0.15, pitch=-0.1 + 0.35 * kt, wag=0.5, pupil=1 + kt * 0.6)
        isl.location = (lerp(34, 150, kt), 3, 0)
        cam(vlerp((1.5 - 0.6 * t, -12.5, 2.4), (-9.5, -2.6, 3.4), k), vlerp((0.3, 0, 2.0), (12, 1.5, 1.6), k), lerp(27, 34, k), shift=lerp(-0.12, -0.22, k))
    return up

def shot_C():   # cyclops: giant one-eyed cat looms over the crew in a cave; then sheep file out with cats clinging underneath
    light(d=(0.5, -0.5, 0.35), amb=(0.2, 0.17, 0.24), dif=(1.0, 0.62, 0.3), fog=(0.05, 0.03, 0.06), f0=9, f1=38)
    rock = mat("rock", (0.42, 0.36, 0.34), "noise", (0.3, 0.26, 0.26), scale=0.6, texel=3)
    ico("cave", rock, (19, 15, 11), (0, 2, 3), sub=3, jitter=0.07, seed=5); cone("cfloor", mat("cavefloor", (0.36, 0.3, 0.27), "noise", (0.28, 0.23, 0.22), scale=0.8, texel=3), 22, 22, 0.1, (0, 0, -0.05), seg=12)
    sph("mouth", mat("daylight", (0.8, 0.92, 1.0), lit=False), (0.3, 3.2, 4.2), (17.5, -2.5, 3.0)); rng = random.Random(2)
    for i in range(9): ico("boulder", rock, rng.uniform(0.5, 1.6), (rng.uniform(-9, 12), rng.uniform(3.5, 7), 0.3), sub=1, jitter=0.2, seed=i)
    fl = [cone("flame", mat("fire", (1.0, 0.7, 0.2), lit=False), 0.4, 0.0, 1.0, (3.6 + i * 0.25, -0.3 - i * 0.2, 0.5), seg=5) for i in range(3)]
    for i in range(4): box("log", mat("wood_dark", (0.3, 0.17, 0.08)), (1.1, 0.16, 0.16), (3.8, -0.5, 0.1), rot=(0, 0, i * 0.8))
    cy = cat("cyclops", "cyclops", 5.2, None, (-1.2, 1.6, 0), eyes=1, eye=(0.95, 0.75, 0.1)); make_poofs(4)
    crew = [cat("c%d" % i, f, 0.8, None, (0, 0, 0), rz=pi) for i, f in enumerate(("orange", "grey", "calico", "black"))]
    crew_pos = [(-0.2, -3.6), (1.0, -4.1), (-1.5, -4.3), (2.0, -3.5)]
    sh = [sheep("sheep%d" % i) for i in range(4)]
    under = [cat("u%d" % i, f, 0.55, s["root"], (0.05, 0, 0.42), shadow=False) for i, (f, s) in enumerate(zip(("orange", "grey", "calico", "black"), sh))]
    for u in under: u["root"].rotation_euler = (pi / 2, 0, pi / 2)   # belly up against the fleece, head toward the sheep's head
    t2 = W("they", 3.0)
    def up(t):
        for i, f in enumerate(fl): f.scale = (1, 1, 0.8 + 0.4 * abs(math.sin(9 * t + i * 2))); f.rotation_euler.z = t * 3 + i
        if t < t2:
            te = W("oneeyed", 0.6); k = smooth(te, te + 0.9, t)
            pose(cy, t, armL=0.15, armR=0.15, pitch=lerp(0.1, 0.42, k), yaw=0.12 * math.sin(1.2 * t), wag=0.5, wagf=1.6, pupil=lerp(0.5, 0.95, k), blink=0.0)
            for i, (c, p) in enumerate(zip(crew, crew_pos)):
                sh_ = 0.03 * math.sin(40 * t + i * 2); place(c, (p[0] + sh_, p[1] - 0.5 * k, 0), 0)
                pose(c, t, armL=1.3 * k, armR=1.3 * k, side=0.5 * k, pitch=0.1, yaw=0.6 * math.sin(3 * t + i) * (1 - k), pupil=1.9, wag=1.2, wagf=18, lean=0.2 * k, ph=i)
            for s in sh: s["root"].location = (0, 0, -500)
            cam(vlerp((1.0, -9.0, 0.6), (0.5, -7.6, 0.55), k), (-1.2, 0.5, lerp(2.4, 3.3, k)), 21, shift=-0.2)
        else:
            u = t - t2
            for c in crew: place(c, None, on=False)
            for i, s in enumerate(sh):
                x = -5.5 + 2.6 * u - i * 2.3 + 4.6; s["root"].location = (x, -3.0, 0.05 * abs(math.sin(8 * u + i))); s["head"].rotation_euler = (0, 0.15 * math.sin(6 * u + i), 0)
                for j, l in enumerate(s["legs"]): l.rotation_euler = (0, 0.5 * math.sin(8 * u + i + j * pi), 0)
                pose(under[i], t, armL=2.6, armR=2.6, side=0.3, pupil=1.7, wag=0.3, pitch=0.3 * math.sin(5 * u + i), ph=i, breathe=False)
            pat = abs(math.sin(2.6 * u))
            pose(cy, t, armL=0.9 + 0.5 * pat, armR=0.2, pitch=0.5, yaw=-0.25 + 0.2 * math.sin(1.3 * u), pupil=0.5, blink=0.55, wag=0.4, wagf=1.5, lean=-0.25)
            cam((2.2 + 0.25 * u, -8.2, 0.75), (1.6 + 0.25 * u, -3.0, 1.15), 30, shift=-0.17)
    return up

def shot_D():   # winds: crew paws at the sack while the hero naps; it bursts; then the ship is blown away from home
    light(); sky(); sea(); ship(); isl = island((60, 5, 0), 10, palms=2, house=True, seed=3); make_poofs(14); R = S["ship"]
    bag = ico("bag", mat("sack", (0.72, 0.55, 0.3), "noise", (0.6, 0.44, 0.22), scale=2, texel=6), 0.5, (1.25, 0, 0.42), R, sub=2, jitter=0.1, seed=3, smooth_=True)
    tie = cone("tie", mat("gold", (0.98, 0.8, 0.2)), 0.13, 0.2, 0.22, (1.25, 0, 0.95), R, seg=6)
    a, b = S["crew"][4], S["crew"][5]; a["root"].location = (0.45, -0.3, -0.03); b["root"].location = (2.0, 0.3, 0.1); b["root"].rotation_euler.z = facing(-1, -0.2)
    to, t3 = W("opens", 3.2), W("they", 4.2)
    def up(t):
        st = smooth(to, to + 0.5, t); wide = t >= t3; amp = 1 + 2.2 * st
        light(amb=vlerp((0.5, 0.52, 0.6), (0.3, 0.3, 0.4), st), dif=vlerp((0.75, 0.7, 0.6), (0.4, 0.4, 0.5), st), fog=vlerp((0.7, 0.8, 0.95), (0.36, 0.38, 0.5), st), f0=lerp(30, 12, st), f1=lerp(160, 90, st))
        set_sky(vlerp((0.75, 0.86, 0.98), (0.4, 0.42, 0.55), st), vlerp((0.2, 0.45, 0.9), (0.12, 0.13, 0.25), st))
        sea_update(t, speed=lerp(3, -9, st), amp=amp); ship_update(t, amp=amp, billow=lerp(1, -1.1, st), row=False, roll=0.22 * st * math.sin(5 * t), flap=0.25 * st)
        crew_row(t, scared=st); k = 1 - st; tap = max(0, math.sin(7 * t)) * k
        pose(a, t, armR=1.2 + 0.7 * tap, armL=0.3 + 1.6 * st, side=0.9 * st, pitch=0.25 * k - 0.3 * st, pupil=1.3 + st, wag=1.0, wagf=6 + 14 * st, ph=1)
        pose(b, t, armL=1.2 + 0.7 * max(0, math.sin(7 * t + 2)) * k + 0.8 * st, armR=0.3 + 1.6 * st, side=0.9 * st, pitch=0.25 * k - 0.3 * st, pupil=1.3 + st, wag=1.0, wagf=6 + 14 * st, ph=2)
        pose(S["hero"], t, armL=2.4 * st, armR=2.4 * st, side=0.6 * st, pitch=lerp(0.55, -0.2, st), yaw=lerp(0, 2.6, smooth(to + 0.1, to + 0.5, t)), blink=1 - st, pupil=1 + st, wag=0.2 + st, wagf=2 + 12 * st)
        sq = 1 + 0.12 * tap; bag.scale = (0.5 * sq * (1 - 0.75 * st), 0.5 * sq * (1 - 0.75 * st), 0.5 / sq * (1 - 0.85 * st)); tie.location.z = lerp(0.95, 0.5, st); tie.rotation_euler.y = 1.3 * st
        for i in range(14):   # the storm leaves the bag: puffs spiral up and aft
            k_ = ((t - to) * 0.9 - i * 0.07) % 1.0 if t > to + i * 0.07 else 0; ang = i * 2.4 + 5 * k_
            poof(i, (1.25 - (9 * k_ if not wide else 16 * k_), 0.0, 1.0), k_, r=0.35 + 0.75 * k_, drift=(0, 1.8 * k_ * math.sin(ang), 0.5 + 2.6 * k_ * abs(math.cos(ang))))
        if not wide:
            isl.location = (0, 0, -600); cam((-0.7, -4.6, 3.0), (1.3, 0, 0.75), 27, shake=0.05 * st, t=t, shift=-0.2)
        else:
            u = t - t3; isl.location = (26 + 34 * smooth(0, 1.6, u), 4, 0); cam((-9.5 - 1.2 * u, -3.4, 3.2), (9, 1.5, 2.2), 31, shake=0.05, t=t)
    return up

def shot_E():   # circe: witch cat zaps the crew; poof; dogs
    light(); sky(); sea(); island((0, 0, 0), 9, palms=3, seed=7); make_poofs(9)
    wt = cat("witch", "black", 1.0, None, (-1.0, 0.1, 0.6), rz=facing(1, -0.25), hat="witch", eye=(0.75, 0.4, 0.95))
    wand = box("wand", mat("wood_dark", (0.3, 0.17, 0.08)), (0.035, 0.035, 0.5), (0, 0, -0.5), wt["arms"][1]); star = ico("star", mat("spark", (0.9, 0.5, 1.0), lit=False), 0.09, (0, 0, -0.78), wt["arms"][1], sub=1)
    pos = [(0.45, 0.25), (1.05, -0.45), (1.45, 0.8)]
    cats = [cat("v%d" % i, f, 0.9, None, (p[0], p[1], 0.6), rz=facing(-1, -0.25)) for i, (f, p) in enumerate(zip(("orange", "grey", "calico"), pos))]
    dogs = [cat("d%d" % i, "dog", 0.9, None, (p[0], p[1], 0.6), rz=facing(-0.6, -1), species="dog") for i, p in enumerate(pos)]
    bolt = box("bolt", mat("spark", (0.9, 0.5, 1.0), lit=False), (1.6, 0.08, 0.08), (0, 0, -500))
    tp, td = W("pigs", 1.6), W("dogs", 3.0)
    def up(t):
        sea_update(t, speed=0.6, calm_r=11); z = smooth(tp - 0.35, tp - 0.05, t); after = t > tp + 0.22; kd = smooth(td, td + 0.3, t)
        pose(wt, t, armR=2.3 * z - 0.6 * kd, armL=0.3 + 1.2 * kd, side=0.3 + 0.5 * kd, pitch=-0.1 - 0.25 * kd, lean=-0.3 * kd, wag=0.8 + kd, wagf=3 + 12 * kd, pupil=1 + 0.3 * z - 0.6 * kd, blink=0.0, ph=3)
        star.scale = (0.09 * (1 + 2 * z + 0.6 * math.sin(30 * t)),) * 3
        bolt.location = (0.1, 0.1, 1.75) if tp - 0.05 < t < tp + 0.14 and int(t * 30) % 2 == 0 else (0, 0, -500); bolt.rotation_euler = (0, 0.12, 0.05)
        for i, p in enumerate(pos):
            place(cats[i], (p[0], p[1], 0.6), on=not after); place(dogs[i], (p[0], p[1], 0.6 + 0.22 * abs(math.sin(7 * t + i * 2)) * (0.4 + 0.6 * kd)), on=after)
            pose(cats[i], t, armL=0.4 + 1.4 * z, armR=0.4 + 1.4 * z, side=0.6 * z, pitch=-0.2 * z, pupil=1 + z, lean=-0.2 * z, ph=i, wag=0.6)
            pose(dogs[i], t, armL=0.9, armR=0.9, roll=0.3 * math.sin(4 * t + i), wag=1.3, wagf=22, pitch=-0.1, ph=i)
            for j in range(3): poof(i * 3 + j, (p[0] + 0.3 * math.cos(j * 2.1), p[1] - 0.35, 1.2 + 0.3 * math.sin(j * 2.1)), (t - tp) / 0.7 - j * 0.06, r=0.6, drift=(0.4 * math.cos(j * 2.1), -0.2, 0.9))
        cam((0.25 + 0.15 * math.sin(0.5 * t), -6.6 + 0.2 * t, 1.6), (0.2, 0, 1.15), 43, shift=-0.15, shake=0.04 * (1 if tp < t < tp + 0.3 else 0), t=t)
    return up

def shot_F():   # sirens: winged cats on a rock shaking a tin of fish; the hero strains against the mast
    light(); sky(); sea(); ship(plugs=True, hero_at_prow=False); R = S["ship"]; h = S["hero"]; h["root"].rotation_euler.z = 0
    for z in (0.3, 0.45, 0.6): cone("rope", mat("rope", (0.9, 0.8, 0.55)), 0.36, 0.36, 0.07, (0.42, 0, z), R, seg=8, smooth_=True)
    rock = mat("rock", (0.42, 0.4, 0.42), "noise", (0.3, 0.3, 0.34), scale=1.5, texel=4); rk = empty("rk", None, (0, -8, 0))
    ico("srock", rock, (3.2, 2.6, 2.6), (0, 0, 0.2), rk, sub=2, jitter=0.16, seed=8); ico("srock2", rock, (1.6, 1.4, 1.2), (3.2, 0.6, 0), rk, sub=1, jitter=0.2, seed=9)
    s1 = cat("siren1", "white", 1.0, rk, (-0.75, 0.5, 2.55), rz=pi, wings=True, eye=(0.3, 0.75, 0.95), shadow=False); s2 = cat("siren2", "cream", 0.95, rk, (0.85, 0.3, 2.45), rz=pi + 0.2, wings=True, eye=(0.3, 0.75, 0.95), shadow=False)
    can = empty("can", s1["body"], (0, -0.2, 1.62)); cone("tin", mat("tin", (0.8, 0.82, 0.86)), 0.27, 0.27, 0.36, (0, 0, 0), can, seg=8, smooth_=True); cone("label", mat("label", (0.15, 0.45, 0.85)), 0.275, 0.275, 0.2, (0, 0, 0), can, seg=8, smooth_=True)
    sph("fish", mat("gold", (0.98, 0.8, 0.2)), (0.13, 0.03, 0.06), (0, -0.27, 0), can); notes = [sph("note", mat("note", (1, 0.9, 0.3), lit=False), 0.09, (0, 0, -500), seg=6, rings=4) for i in range(5)]
    t2 = W("so", 3.0)
    def up(t):
        sea_update(t, speed=1.5); ship_update(t, billow=0.7); crew_row(t)
        rk.location = (lerp(4.5, -1.5, t / DUR), -8, 0); shk = math.sin(22 * t)
        pose(s1, t, armL=2.9, armR=2.9, side=0.2, yaw=0.15 * math.sin(3 * t), wag=1.0, pupil=0.7, ph=1); can.rotation_euler = (0, 0.35 * shk, 0); can.location = (0.05 * shk, -0.2, 1.62)
        pose(s2, t, armL=0.4, armR=1.6 + 0.4 * math.sin(4 * t), side=0.7, roll=0.25 * math.sin(4 * t), wag=1.0, pupil=0.7, ph=2)
        for s in (s1, s2):
            for i, w in enumerate(s["wings"]): w.rotation_euler = (0, (1 if i else -1) * 0.5 * math.sin(9 * t), 0)
        strain = 0.5 + 0.5 * math.sin(9 * t)
        pose(h, t, armL=1.5 + 0.3 * strain, armR=1.5 + 0.3 * math.sin(9 * t + 2), side=-0.1, pitch=-0.15, roll=0.18 * math.sin(7 * t), yaw=0.2 * math.sin(4.5 * t), lean=0.3 + 0.12 * strain, pupil=2.5, wag=1.4, wagf=14, blink=0.0)
        for i, n in enumerate(notes):
            k = (t * 0.6 + i / 5) % 1.0; n.location = (rk.location.x - 0.3 + 0.6 * math.sin(i * 2.3 + 4 * k), -8 + 0.6 + 5.5 * k, 3.6 + 0.9 * k + 0.25 * math.sin(8 * k + i)); n.scale = (0.11 * math.sin(pi * k),) * 3
        if t < t2: cam((rk.location.x + 1.4, -2.6, 2.0), (rk.location.x, -7.6, 3.75), 40)
        else: cam((1.5, -4.7, 1.9 + 0.1 * math.sin(1.3 * t)), (0.55, 0, 1.45 + 0.1 * math.sin(1.3 * t)), 44, shift=-0.2)
    return up

def shot_G():   # calypso: hero flat on his back on a cushion while the sun and moon go round seven times
    light(); sky(sun=False); sea(); island((0, 0, 0), 9, palms=3, seed=11)
    box("cushion", mat("cushion", (0.8, 0.15, 0.3), "stripes", (0.95, 0.8, 0.3), scale=2, texel=8, axis=0, thr=0.8), (1.9, 1.1, 0.22), (0.2, 0, 0.72))
    h = cat("hero", "orange", 0.95, None, (0.95, 0, 1.08), helmet=False, shadow=False); h["root"].rotation_euler = (-pi / 2, 0, pi / 2)
    hel = cat("helm_only", "orange", 0.01, None, (0, 0, -500))   # (unused spare so the material set matches other shots)
    g = cat("calypso", "white", 1.0, None, (-1.35, 0.5, 0.6), rz=facing(1, -0.5), hat="flowers", eye=(0.35, 0.7, 0.95))
    fan = cone("fan", mat("leaf", (0.2, 0.62, 0.22)), 0.42, 0.0, 1.3, (0, 0, -0.85), g["arms"][1], seg=4, scale=(1, 0.2, 1), rot=(pi, 0, 0))
    sun = sph("sun", mat("sun", (1.0, 0.95, 0.6), lit=False), 9.0, seg=12, rings=8); moon = sph("moon", mat("moon", (0.9, 0.93, 1.0), lit=False), 6.0, seg=12, rings=8)
    ts = W("seven", 2.2); T = (DUR - 0.2) / 7.0
    def up(t):
        ph = 2 * pi * t / T; day = 0.5 + 0.5 * math.sin(ph); dusk = max(0, 1 - abs(math.sin(ph)) * 3)
        hz = vlerp(vlerp((0.1, 0.12, 0.3), (0.75, 0.86, 0.98), day), (1.0, 0.6, 0.35), dusk * 0.8); zn = vlerp((0.02, 0.03, 0.14), (0.2, 0.45, 0.9), day)
        set_sky(hz, zn); a = 0.42 + 0.58 * day
        light(d=(0.7 * math.cos(ph), -0.6, 0.35 + 0.5 * abs(math.sin(ph))), amb=(0.5 * a, 0.52 * a, 0.62 * a + 0.08 * (1 - day)), dif=(0.75 * a, 0.7 * a, 0.6 * a), fog=hz)
        sun.location = (130 * math.cos(ph), 240, 130 * math.sin(ph) - 10); moon.location = (-130 * math.cos(ph), 240, -130 * math.sin(ph) - 10)
        sea_update(t, speed=0.6, calm_r=11)
        pose(h, t, armL=0.5, armR=0.5, side=1.2, blink=1.0, wag=0.5, wagf=2.5, pitch=-0.15)
        h["body"].scale = (1, 1 + 0.06 * math.sin(2.4 * t), 1)
        pose(g, t, armR=1.5 + 0.5 * math.sin(5 * t), armL=0.3, side=0.3, yaw=-0.3, roll=0.1 * math.sin(2 * t), pupil=1.2, wag=0.6, ph=2)
        for i, p in enumerate(S["palms"]): p.rotation_euler = (0.06 * math.sin(2 * t + i), 0.06 * math.sin(1.7 * t + i * 2), 0)
        cam((0.2, -7.0 + 0.3 * t, 1.9), (-0.1, 0, 1.2), lerp(38, 44, t / DUR), shift=-0.19)
    return up

def shot_H():   # suitors: cats face-down in bowls along a banquet table; the doors open on the hero and they scatter
    light(d=(0.3, -0.7, 0.6), amb=(0.5, 0.42, 0.38), dif=(0.75, 0.62, 0.45), fog=(0.16, 0.1, 0.08), f0=14, f1=60)
    hall(); big_door(-5.5, facing_y=1); box("bench", mat("wood_dark", (0.3, 0.17, 0.08)), (9.4, 0.6, 0.4), (0, 1.95, 0.2)); make_poofs(10)
    sph("daylight", mat("daylight", (0.95, 0.97, 1.0), lit=False), (6, 0.2, 6), (0, -6.7, 2.5))
    box("table", mat("tablewood", (0.55, 0.34, 0.16), "stripes", (0.42, 0.25, 0.1), scale=3, texel=16, axis=1, thr=0.85), (9.4, 1.3, 0.14), (0, 1.0, 0.78))
    for x in (-4.3, 4.3): box("tleg", mat("wood_dark", (0.3, 0.17, 0.08)), (0.2, 1.0, 0.75), (x, 1.0, 0.37))
    furs = ("grey", "black", "calico", "white", "brown", "cream", "grey", "calico"); su = []; rng = random.Random(6)
    for i, f in enumerate(furs):
        back = i < 6; x = -3.75 + i * 1.5 if back else (-2.2, 2.4)[i - 6]; y = 1.95 if back else 0.05
        c = cat("s%d" % i, f, 0.92, None, (x, y, 0), rz=0 if back else pi); c["home"] = (x, y); c["dir"] = (-1 if x < 0 else 1) * rng.uniform(0.8, 1.3); su.append(c)
        bx, by = x, (1.38 if back else 0.62); cone("bowl", mat("bowl%d" % (i % 3), ((0.85, 0.2, 0.15), (0.2, 0.45, 0.8), (0.95, 0.8, 0.25))[i % 3]), 0.17, 0.27, 0.14, (bx, by, 0.92), seg=8); cone("food", mat("food", (0.55, 0.3, 0.2)), 0.22, 0.22, 0.03, (bx, by, 0.985), seg=8)
    h = cat("hero", "orange", 1.0, None, (0, -4.9, 0), rz=pi, helmet=True)
    bw = empty("bow", h["arms"][0], (0, -0.05, -0.3)); bm_ = mat("wood_dark", (0.3, 0.17, 0.08))
    for i in range(7): a = (i - 3) * 0.3; box("bowseg", bm_, (0.05, 0.05, 0.26), (0, -0.55 * math.cos(a) + 0.45, 0.75 * math.sin(a)), bw, rot=(-a, 0, 0))
    box("string", mat("cat_white", (1, 1, 1)), (0.015, 0.015, 1.25), (0, 0.06, 0), bw)
    t2 = W("he", 3.6, nth=1)
    def up(t):
        u = t - t2; op = smooth(0.0, 0.35, u)
        for hg, sx in S["doors"]: hg.rotation_euler.z = sx * 1.75 * op
        place(h, (0, -4.9 + 1.5 * smooth(0.1, 1.2, u), 0), pi); pose(h, t, armL=1.5, armR=0.2, side=0.25, pitch=-0.05, pupil=0.45, blink=0.0, wag=0.9, wagf=5)
        run = smooth(0.45, 0.6, u)
        for i, c in enumerate(su):
            x, y = c["home"]; back = i < 6; d = max(0.0, u - 0.5 - i * 0.03)
            if u < 0:
                nom = 0.5 + 0.5 * math.sin(10 * t + i * 1.9); place(c, (x, y, 0.4 if back else 0), 0 if back else pi); pose(c, t, armL=1.2, armR=1.2, pitch=0.5 + 0.25 * nom, lean=0.3 if back else 0.5, wag=0.7, wagf=4, ph=i, blink=0.6)
            else:
                rz = (pi if back else 0) * smooth(0.0, 0.25, u) + (0 if back else pi); rz = lerp(rz, facing(c["dir"], 0), run)
                place(c, (x + c["dir"] * 11 * d * d * 3 + c["dir"] * 6 * d, y + 0.3 * d, 0.9 * abs(math.sin(9 * d)) * run + 0.5 * math.exp(-((u - 0.4) / 0.12) ** 2)), rz)
                pose(c, t, armL=2.4, armR=2.4, side=0.7, pitch=-0.2, pupil=2.2, wag=1.5, wagf=25, blink=0.0, ph=i)
            poof(i, (x, y - 0.2, 0.5), (u - 0.5 - i * 0.03) / 0.6, r=0.55)
        if u < 0: cam((-3.2 + 1.0 * t, -3.6, 2.7), (-2.2 + 1.0 * t, 1.5, 1.2), 30, shift=-0.21)
        else: cam((0.4, 4.3, 2.5 - 0.15 * u), (0, -4.0, 1.2), 44, shift=-0.19, shake=0.05 * (1 - smooth(0.5, 1.2, u)), t=t)
    return up

def shot_I():   # door: he sits at the closed doors, then looks back at us and paws at them
    light(d=(0.5, -0.6, 0.6), amb=(0.52, 0.44, 0.4), dif=(0.75, 0.62, 0.45), fog=(0.16, 0.1, 0.08), f0=14, f1=60)
    box("floor", mat("tiles", (0.86, 0.8, 0.68), "checker", (0.6, 0.3, 0.22), scale=0.5, texel=16), (40, 40, 0.1), (0, 0, -0.05)); big_door(3.0, facing_y=-1)
    box("rug", mat("rug", (0.7, 0.15, 0.2), "stripes", (0.95, 0.8, 0.3), scale=1.5, texel=8, axis=1, thr=0.85), (2.6, 3.4, 0.03), (0, 0.6, 0.015))
    for sx in (-1, 1): cone("torch", mat("fire", (1.0, 0.7, 0.2), lit=False), 0.16, 0.0, 0.5, (sx * 2.7, 2.7, 3.0), seg=5); box("sconce", mat("bronze2", (0.85, 0.62, 0.2)), (0.12, 0.12, 0.5), (sx * 2.7, 2.72, 2.55))
    h = cat("hero", "orange", 1.0, None, (0.1, 1.75, 0), rz=pi, helmet=True)
    tw, to = W("wants", 2.6), W("out", 3.0)
    def up(t):
        k = smooth(tw - 0.35, tw + 0.05, t); scr = smooth(to - 0.1, to + 0.1, t) * (0.5 + 0.5 * math.sin(16 * t))
        pose(h, t, armR=2.0 * smooth(to - 0.2, to, t) + 0.6 * scr, armL=0.2, side=0.1, yaw=lerp(0, 2.55, k), pitch=lerp(-0.45, -0.05, k), roll=0.12 * k, wag=1.0, wagf=lerp(2.5, 7, k), pupil=lerp(1.0, 2.0, k), blink=1.0 if tw + 0.5 < t < tw + 0.6 else 0.0)
        cam(vlerp((1.5, -4.2, 0.8), (1.25, -2.2, 1.0), smooth(0, DUR, t)), vlerp((0, 3, 2.3), (0.1, 1.75, 1.3), smooth(0.3, tw + 0.3, t)), lerp(26, 38, k), shift=-0.19)
    return up

# ------------------------------------------------------------------ render
def setup_render(res, samples):
    sc = bpy.context.scene; sc.render.engine = "CYCLES"; c = sc.cycles; c.device = "CPU"; c.samples = samples; c.use_adaptive_sampling = False; c.use_denoising = False
    c.max_bounces = 0; c.diffuse_bounces = 0; c.glossy_bounces = 0; c.transmission_bounces = 0; c.transparent_max_bounces = 12; c.filter_width = 1.0
    sc.render.use_persistent_data = True; sc.render.resolution_x = res; sc.render.resolution_y = res * 16 // 9; sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGB"; sc.render.image_settings.compression = 20; sc.render.fps = FPS
    sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"; sc.display_settings.display_device = "sRGB"

def main():
    for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
    sc = bpy.context.scene
    if sc.world is None: sc.world = bpy.data.worlds.new("w")
    sc.world.use_nodes = True
    make_psx(); make_cam(); setup_render(ARGS.res, ARGS.samples)
    update = {"A": shot_A, "B": shot_B, "C": shot_C, "D": shot_D, "E": shot_E, "F": shot_F, "G": shot_G, "H": shot_H, "I": shot_I}[SHOT]()
    os.makedirs(ARGS.out, exist_ok=True)
    for f in ([ARGS.start] if ARGS.preview else range(ARGS.start, ARGS.end)):
        path = os.path.join(ARGS.out, f"{SHOT}_{f:04d}.png")
        if os.path.exists(path) and not ARGS.preview: continue
        sc.frame_set(f); update(f / FPS); sc.render.filepath = path; t0 = time.time(); bpy.ops.render.render(write_still=True)
        print(f"FRAME {SHOT} {f} {time.time() - t0:.1f}s", flush=True)
main()

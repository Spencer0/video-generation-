"""Procedural Blender scene: the Kaye effect (leaping shampoo), bright kitchen set.

Run headless:
  blender -b -noaudio -P pipeline/blender/scene_kaye.py -- --shot A --start 0 --end 240 \
      --out videos/005-kaye-effect/build/frames/A [--res 720] [--samples 16] [--fps 30] [--preview]

Scale: 1 Blender unit = 1 cm. Everything is kinematic (no fluid sim), as in video 002:
  stream = bevelled POLY curve (slow sine wobble, necking by free-fall speed)
  heap   = polar-grid dome whose vertex heights are recomputed per frame (breathing + dimple)
  jet    = bevelled POLY curve whose points are fluid parcels on a parabola from the dimple;
           grows (tip), is fed ~0.2 s real, then the root detaches and the tail flies out
  honey  = rope coiling (helix wound down from the landing point onto a slumped mound)
  water  = thin stream, spreading puddle, Poisson-ish splash droplets on parabolas
Scene time runs at SLOWMO x real time; the on-screen label says "SLOW MOTION 4x".
Shots (nominal lengths in SHOT_DUR, period = length so the assembler can wrap seamlessly):
  A  hero wide: bottle, stream, heap, plate, two leaps; frame 0 has a jet mid-leap (loop lands here)
  X  close-up on the impact point for the cutaway diagram; one leap late in the shot
  B  3/4 high angle for the try-it beat; two leaps
  H/W/S  comparison panels (1080x640 aspect): honey coils, water splashes, shampoo leaps
"""
import bpy, bmesh, math, random, sys, os, time
from mathutils import Vector
from mathutils import noise as mnoise

def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    a = {"shot": "A", "start": 0, "end": 1, "out": "/tmp/frames", "res": 720, "samples": 16, "preview": False, "fps": 30}
    i = 0
    while i < len(argv):
        k = argv[i].lstrip("-")
        if k == "preview": a["preview"] = True; i += 1; continue
        v = argv[i + 1]; i += 2
        a[k] = type(a[k])(v) if k in a and not isinstance(a[k], bool) else v
    return a

ARGS = parse_args(); FPS = ARGS["fps"]; SHOT = ARGS["shot"].upper()
SHOT_DUR = {"A": 8.0, "X": 7.0, "B": 5.0, "H": 5.0, "W": 5.0, "S": 5.0}
T_SHOT = SHOT_DUR[SHOT]
PANEL = SHOT in ("H", "W", "S")           # comparison panels render at 1080x640 aspect
FLUID = {"H": "honey", "W": "water"}.get(SHOT, "shampoo")
SLOWMO = 4.0; G = 981.0                     # cm/s^2, real time
Z_NOZZLE = 17.5 if SHOT in ("H", "W", "S") else 24.0   # pour height (a hand-span and a bit); panels pour lower so the spout stays in frame
IMPACT = Vector((0.0, 0.0, 0.0))            # where the stream lands (xy); the heap centre sits behind it
HEAP_C = Vector((0.0, 2.2, 0.0))
# jet events per shot: (start time in scene seconds, exit direction sign along x)
EVENTS = {"A": [(3.3, +1), (6.6, -1)], "X": [(4.6, +1)], "B": [(0.5, -1), (3.0, +1)], "S": [(4.3, -1), (2.4, +1)], "H": [], "W": []}[SHOT]
V_JET = Vector((50.0, 70.0, 112.0))         # cm/s real: leaves at ~50 deg, angled away from the camera so the arc stays in the portrait frame; ~6.5 cm high
T_FEED = 0.5                                # s real: how long the jet is fed before the heap shifts (a full arc stands ~0.2 s)

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
def principled(name, color, rough=0.5, metallic=0.0, coat=0.0, spec=0.5):
    m, nt, out = new_mat(name); p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = (*color, 1); p.inputs["Roughness"].default_value = rough; p.inputs["Metallic"].default_value = metallic
    set_in(p, "Coat Weight", coat); set_in(p, "Coat Roughness", 0.05); set_in(p, "Specular IOR Level", spec)
    nt.links.new(p.outputs[0], out.inputs[0]); return m
def link_obj(name, data):
    ob = bpy.data.objects.new(name, data); bpy.context.collection.objects.link(ob); return ob

# ----------------------------------------------------------------------------- materials
def fluid_material(kind):
    if kind == "shampoo":   # opaque pearl, glossy, a hint of pink; no transmission (cheap)
        return principled("shampoo", (0.02, 0.40, 0.45), rough=0.06, coat=1.0, spec=0.7)   # deep teal, glossy; no subsurface, no transmission
    if kind == "honey":
        return principled("honey", (0.80, 0.40, 0.06), rough=0.04, coat=0.8, spec=0.8)
    # water: no refraction (a flat glass puddle goes black once transmission bounces run out); pale blue, glossy, a little see-through
    return principled("water", (0.16, 0.45, 0.85), rough=0.02, coat=1.0, spec=0.9)   # opaque, clearly blue so motion-blurred droplets still read at panel size

def plate_material():
    m = principled("plate", (0.93, 0.93, 0.90), rough=0.12, coat=1.0, spec=0.5); return m

def counter_material():
    """Pale oak: stretched noise stripes, matte."""
    m, nt, out = new_mat("counter"); n = nt.nodes; L = nt.links
    p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Roughness"].default_value = 0.55
    tc = n.new("ShaderNodeTexCoord"); mp = n.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (0.05, 1.2, 1.0); L.new(tc.outputs["Object"], mp.inputs["Vector"])
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 2.0; nz.inputs["Detail"].default_value = 5; nz.inputs["Roughness"].default_value = 0.6; L.new(mp.outputs[0], nz.inputs["Vector"])
    ramp = n.new("ShaderNodeValToRGB"); ramp.color_ramp.elements[0].color = (0.42, 0.29, 0.17, 1); ramp.color_ramp.elements[1].color = (0.60, 0.44, 0.28, 1)
    L.new(nz.outputs["Fac"], ramp.inputs[0]); L.new(ramp.outputs[0], p.inputs["Base Color"]); L.new(p.outputs[0], out.inputs[0]); return m

def bottle_material(color): return principled("bottle", color, rough=0.28, coat=0.3, spec=0.5)

# ----------------------------------------------------------------------------- geometry helpers
def mesh_obj(name, bm, mat, smooth=True):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if smooth:
        for p in me.polygons: p.use_smooth = True
    ob = link_obj(name, me)
    if mat: me.materials.append(mat)
    return ob

def lathe(name, profile, mat, segs=96, scale_y=1.0):
    """Revolve an (r, z) profile around Z. profile: list of (r, z) from bottom-centre outward/upward."""
    bm = bmesh.new(); verts = [bm.verts.new((r, 0, z)) for r, z in profile]
    edges = [bm.edges.new((verts[i], verts[i + 1])) for i in range(len(verts) - 1)]
    bmesh.ops.spin(bm, geom=verts + edges, cent=(0, 0, 0), axis=(0, 0, 1), angle=2 * math.pi, steps=segs, use_merge=True)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    if scale_y != 1.0:
        for v in bm.verts: v.co.y *= scale_y
    return mesh_obj(name, bm, mat)

def add_box(name, dims, loc, mat, bevel=0.0):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * dims[0], v.co.y * dims[1], v.co.z * dims[2]))
    ob = mesh_obj(name, bm, mat, smooth=False); ob.location = loc
    if bevel: md = ob.modifiers.new("bevel", "BEVEL"); md.width = bevel; md.segments = 3
    return ob

def add_plane(name, size, loc, mat, rot=(0, 0, 0)):
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=size)   # size = half extent
    ob = mesh_obj(name, bm, mat, smooth=False); ob.location = loc; ob.rotation_euler = rot; return ob

def poly_curve(name, n, mat, radius=0.2, res=8):
    cu = bpy.data.curves.new(name, "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = 1.0; cu.bevel_resolution = res; cu.fill_mode = "FULL"; cu.use_fill_caps = True
    sp = cu.splines.new("POLY"); sp.points.add(n - 1); sp.use_smooth = True
    for p in sp.points: p.co = (0, 0, 0, 1); p.radius = radius
    cu.materials.append(mat); ob = link_obj(name, cu); return ob
def set_curve(ob, pts, radii):
    sp = ob.data.splines[0]
    for p, q, r in zip(sp.points, pts, radii): p.co = (q.x, q.y, q.z, 1.0); p.radius = max(r, 1e-4)

def polar_grid(name, mat, na=64, nr=22):
    bm = bmesh.new(); rings = []
    centre = bm.verts.new((0, 0, 0))
    for j in range(1, nr + 1):
        rings.append([bm.verts.new((0, 0, 0)) for _ in range(na)])
    for i in range(na):
        bm.faces.new((centre, rings[0][i], rings[0][(i + 1) % na]))
    for j in range(nr - 1):
        for i in range(na):
            bm.faces.new((rings[j][i], rings[j + 1][i], rings[j + 1][(i + 1) % na], rings[j][(i + 1) % na]))
    ob = mesh_obj(name, bm, mat); ob["na"] = na; ob["nr"] = nr; return ob

def sphere(name, r, mat, segs=48):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=segs // 2, radius=r); return mesh_obj(name, bm, mat)

def build_bottle(mat, cap_mat):
    """Generic squeeze bottle: oval body, rounded shoulder, neck, open flip cap with a spout. Origin = spout tip, +Z = toward the base."""
    prof = [(0.0, 0.0), (0.55, 0.0), (0.55, 1.2), (0.9, 1.3), (1.35, 1.7), (1.5, 2.6), (1.5, 3.0),          # spout + cap
            (2.4, 3.6), (3.1, 4.6), (3.3, 6.0), (3.3, 16.5), (3.1, 17.6), (2.5, 18.2), (0.0, 18.3)]        # shoulder, body, base
    cap = lathe("cap", prof[:7], cap_mat, scale_y=1.0)
    body = lathe("bottle", prof[6:], mat, scale_y=0.62)
    body.parent = cap
    return cap

# ----------------------------------------------------------------------------- set
def build_world():
    w = bpy.data.worlds["World"] if "World" in bpy.data.worlds else bpy.data.worlds.new("World")
    bpy.context.scene.world = w; w.use_nodes = True
    bg = w.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.80, 0.80, 0.80, 1); bg.inputs[1].default_value = 0.40

def light(name, typ, loc, energy, color, size=1.0, target=(0, 0, 5)):
    ld = bpy.data.lights.new(name, typ); ld.energy = energy; ld.color = color
    if typ == "AREA": ld.size = size
    ob = link_obj(name, ld); ob.location = loc; ob.visible_camera = False
    d = Vector(target) - Vector(loc); ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler(); return ob

def build_set():
    S = {}; build_world()
    counter = counter_material()
    S["counter"] = add_box("counter", (160, 90, 6), (0, 25, -3.5), counter, bevel=0.3)       # front edge at y=-20, top at z=-0.5
    add_plane("backdrop", 120, (0, 70, 40), principled("backdrop", (0.80, 0.80, 0.80), rough=0.9), rot=(math.radians(90), 0, 0))
    plate_prof = [(0.0, -0.5), (8.0, -0.5), (8.4, -0.45), (9.0, -0.1), (12.4, 1.5), (13.0, 1.55), (12.6, 1.1), (9.2, -0.5 + 0.1), (8.6, -0.5)]
    # simpler closed-ish plate: bottom disc + rim; keep top surface of the well at z = 0
    plate_prof = [(0.0, -0.5), (8.2, -0.5), (12.8, 1.4), (13.1, 1.55), (12.7, 1.55), (12.3, 1.25), (8.0, 0.0), (0.0, 0.0)]
    S["plate"] = lathe("plate", plate_prof, plate_material(), segs=128)
    # kitchen context in the background, soft-focus: a second bottle and a folded towel
    bot2 = add_box("bottle2", (6, 3.5, 17), (-26, 24, 8.0), principled("bottle2", (0.55, 0.75, 0.70), rough=0.3), bevel=1.2)
    # the pouring bottle (hand is out of frame above)
    col = {"shampoo": (0.70, 0.82, 0.82), "honey": (0.78, 0.52, 0.18), "water": (0.62, 0.78, 0.88)}[FLUID]
    S["bottle"] = build_bottle(bottle_material(col), principled("cap", (0.96, 0.96, 0.96), rough=0.3))
    S["bottle"].location = (IMPACT.x, IMPACT.y - 0.3, Z_NOZZLE); S["bottle"].rotation_euler = (math.radians(-22), 0, 0)   # spout down, body leaning back (+y)
    S["bottle"].scale = (1, 1, 1)
    fm = fluid_material(FLUID); S["fluid_mat"] = fm
    S["stream"] = poly_curve("stream", 28, fm, 0.25)
    S["heap"] = polar_grid("heap", fm)
    S["jets"] = [poly_curve(f"jet{i}", 40, fm, 0.2) for i in range(2)]
    S["blobs"] = [sphere(f"blob{i}", 1.0, fm) for i in range(2)]
    S["jet_drops"] = [[sphere(f"jd{i}{k}", 1.0, fm, 16) for k in range(3)] for i in range(2)]
    for dl in S["jet_drops"]:
        for d in dl: d.hide_render = True
    for b in S["blobs"]: b.hide_render = True
    if FLUID == "water":
        S["drops"] = [sphere(f"drop{i}", 0.16, fm, 24) for i in range(44)]
        S["puddle"] = sphere("puddle", 1.0, fm, 64)
    if FLUID == "honey":
        S["coil"] = poly_curve("coil", 160, fm, 0.3)
    # lights: big soft warm key front-left-high, cool-ish fill right, overhead softbox; bright and clean
    S["key"] = light("key", "AREA", (-42, 12, 58), 15000.0, (1.0, 0.96, 0.90), size=60.0, target=(0, 0, 8))   # window-shaped 60x90, above-left, slightly behind
    S["key"].data.shape = "RECTANGLE"; S["key"].data.size_y = 90.0
    S["fill"] = light("fill", "AREA", (55, -40, 22), 1600.0, (0.92, 0.95, 1.0), size=60.0, target=(0, 0, 6))   # dim fill from camera right
    S["rim"] = light("rim", "AREA", (28, 45, 34), 2200.0, (1.0, 0.98, 0.95), size=8.0, target=(0, 0, 10))   # small rim behind, opposite the key
    cam_d = bpy.data.cameras.new("cam"); cam = link_obj("cam", cam_d); cam_d.sensor_fit = "VERTICAL"; cam_d.sensor_height = 36.0
    tgt = link_obj("cam_target", None); cam.constraints.new("TRACK_TO").target = tgt
    cam.constraints[0].track_axis = "TRACK_NEGATIVE_Z"; cam.constraints[0].up_axis = "UP_Y"
    cam_d.dof.use_dof = True; cam_d.dof.aperture_fstop = 4.0
    focus = link_obj("focus", None); focus.location = (0, 0, 1.2); cam_d.dof.focus_object = focus
    S["cam"], S["cam_target"], S["focus"] = cam, tgt, focus
    bpy.context.scene.camera = cam
    return S

# ----------------------------------------------------------------------------- kinematics
def heap_height(x, y, t, dimple=1.0, h0=1.5, R=7.0, centre=HEAP_C):
    """Dome + skirt around the heap centre, breathing slowly, dimple at the impact point, soft ripples."""
    dx, dy = x - centre.x, y - centre.y; r = math.hypot(dx, dy)
    breath = 1 + 0.03 * math.sin(2 * math.pi * t / T_SHOT) + 0.012 * math.sin(2 * math.pi * 2 * t / T_SHOT + 1.0)
    dome = h0 * breath * max(0.0, 1 - (r / R) ** 2) ** 1.5
    skirt = 0.25 * max(0.0, 1 - (r / (R * 1.45)) ** 2) ** 1.2
    rip = 0.02 * math.sin(r * 6.0 - 2 * math.pi * 3 * t / T_SHOT) * max(0.0, 1 - r / (R * 1.5))
    lump = 0.22 * mnoise.noise(Vector((x * 0.45, y * 0.45, 0.3 * math.sin(2 * math.pi * t / T_SHOT)))) * max(0.0, 1 - r / (R * 1.4))   # soft lumps, periodic
    rd = math.hypot(x - IMPACT.x, y - IMPACT.y)
    dim = 0.75 * dimple * math.exp(-(rd / 0.9) ** 2)
    return max(0.0, dome + skirt + rip + lump - dim)

def update_heap(ob, t, dimple=1.0, h0=1.5, R=7.0, centre=HEAP_C, outer=10.5):
    me = ob.data; na, nr = ob["na"], ob["nr"]
    me.vertices[0].co = (centre.x, centre.y, heap_height(centre.x, centre.y, t, dimple, h0, R, centre))
    k = 1
    for j in range(1, nr + 1):
        rr = outer * (j / nr) ** 1.3
        for i in range(na):
            a = 2 * math.pi * i / na; x = centre.x + rr * math.cos(a); y = centre.y + rr * math.sin(a)
            me.vertices[k].co = (x, y, heap_height(x, y, t, dimple, h0, R, centre)); k += 1
    me.update()

def stream_points(t, z_top, z_bot, bot_xy, r_top, n=28, wob=0.16, lean=None):
    """Falling stream from the spout to (bot_xy, z_bot): free-fall necking, slow travelling wobble."""
    pts, radii = [], []; v0 = 35.0
    for i in range(n):
        u = i / (n - 1); z = lerp(z_top, z_bot, u)
        v = math.sqrt(v0 * v0 + 2 * G * (z_top - z)); r = r_top * math.sqrt(v0 / v) * (1 + 0.06 * math.sin(z * 2.2 - t * 9.0))
        w = wob * u * u; ph = z * 0.9 - t * 5.5
        x = IMPACT.x + w * math.sin(ph) + 0.6 * n1(t * 0.25, 3.0) * u * 0.25
        y = IMPACT.y - 0.3 * (1 - u) + w * 0.5 * math.cos(ph * 0.8)
        if lean is not None:   # pull the bottom of the stream to a landing point (honey coiling)
            s = smoothstep(0.55, 1.0, u); x = lerp(x, lean.x, s); y = lerp(y, lean.y, s)
        else:
            x = lerp(x, bot_xy.x, smoothstep(0.85, 1.0, u)); y = lerp(y, bot_xy.y, smoothstep(0.85, 1.0, u))
        pts.append(Vector((x, y, z))); radii.append(r)
    radii[-1] *= 0.7
    return pts, radii

def jet_state(t, t0, sign):
    """Return (ages_lo, ages_hi, phase) in real seconds for a jet event that started at scene time t0; None if inactive."""
    tau = (t - t0) / SLOWMO
    if tau < 0: tau += T_SHOT / SLOWMO   # events wrap around the shot period (hero loop)
    v = Vector((V_JET.x * sign, V_JET.y, V_JET.z)); z0 = 1.2
    t_land = (v.z + math.sqrt(v.z * v.z + 2 * G * z0)) / G
    if tau > T_FEED + t_land + 0.12: return None
    lo = max(0.0, tau - T_FEED); hi = min(tau, t_land)
    return lo, hi, tau, v, t_land, z0

def place_jet(ob, blob, t, t0, sign):
    st = jet_state(t, t0, sign)
    if st is None or st[1] <= st[0] + 1e-4:
        ob.hide_render = True
        for d in STATE["S"]["jet_drops"][EVENTS.index((t0, sign))]: d.hide_render = True
        return 0.0
    lo, hi, tau, v, t_land, z0 = st
    ob.hide_render = False
    origin = Vector((IMPACT.x + 0.3 * sign, IMPACT.y - 0.15, z0))
    n = len(ob.data.splines[0].points); pts, radii = [], []
    for i in range(n):
        u = i / (n - 1); a = lerp(lo, hi, u)
        p = origin + v * a + Vector((0, 0, -0.5 * G * a * a))
        pts.append(p)
        taper = smoothstep(0.0, 0.06, u) * (smoothstep(1.0, 0.94, u) if hi < t_land else 1.0)
        radii.append(0.26 * (1 - 0.5 * a / t_land) * (0.3 + 0.7 * taper))   # stream diameter at the dimple -> half at the tip
    set_curve(ob, pts, radii)
    for k, dr in enumerate(STATE["S"]["jet_drops"][EVENTS.index((t0, sign))]):   # a couple of detached droplets just past the tip
        a = hi + 0.012 * (k + 1); dr.hide_render = not (hi < t_land and tau > 0.03)
        q = origin + v * a + Vector((0, 0, -0.5 * G * a * a)); dr.location = (q.x + 0.15 * (k % 2), q.y, q.z + 0.08 * k); r = 0.11 - 0.025 * k; dr.scale = (r, r, r * 1.3)
    land = origin + v * t_land + Vector((0, 0, -0.5 * G * t_land * t_land)); land.z = 0.0
    blob.location = (land.x, land.y, 0.0)
    swell = 1.0 + 0.25 * smoothstep(t_land, t_land + 0.06, tau) * (1 - smoothstep(t_land + 0.2, t_land + 0.45, tau))
    blob.scale = (1.15 * swell, 1.0 * swell, 0.42)
    return 1.0 - smoothstep(T_FEED, T_FEED + 0.1, tau) * (1 - smoothstep(T_FEED + 0.25, T_FEED + 0.4, tau))   # dimple deepens while fed

def update_shampoo(S, t):
    dimple = 1.0
    for (t0, sign), jet, blob in zip(EVENTS, S["jets"], S["blobs"]):
        d = place_jet(jet, blob, t, t0, sign); dimple = max(dimple, 1.0 + 0.6 * (1 - d) if jet.hide_render is False else 1.0)
    for jet in S["jets"][len(EVENTS):]: jet.hide_render = True
    for blob in S["blobs"]:   # landing puddles stay visible (they were there from earlier leaps); same spots every cycle
        blob.hide_render = False
    if len(EVENTS) == 2:  # both blobs placed by their events; make sure each exists even if its jet is inactive
        for (t0, sign), blob in zip(EVENTS, S["blobs"]):
            v = Vector((V_JET.x * sign, V_JET.y, V_JET.z)); z0 = 1.2; tl = (v.z + math.sqrt(v.z * v.z + 2 * G * z0)) / G
            land = Vector((IMPACT.x + 0.25 * sign, IMPACT.y - 0.15, z0)) + v * tl + Vector((0, 0, -0.5 * G * tl * tl))
            if blob.scale.z == 1.0 or True:
                cur = blob.location; blob.location = (land.x, land.y, 0.0)
                if abs(blob.scale.z - 0.42) > 1e-6: blob.scale = (1.15, 1.0, 0.42)
    update_heap(S["heap"], t, dimple)
    z_bot = heap_height(IMPACT.x, IMPACT.y, t, dimple) + 0.05
    pts, radii = stream_points(t, Z_NOZZLE - 0.2, z_bot, IMPACT, 0.30)
    set_curve(S["stream"], pts, radii)
    S["focus"].location = (IMPACT.x, IMPACT.y, 1.3)

def update_honey(S, t):
    # slumped mound grows slowly; helix wound down from the landing point on top of it
    h0 = lerp(0.9, 1.5, t / T_SHOT); R = lerp(1.9, 2.4, t / T_SHOT)
    update_heap(S["heap"], t, dimple=0.0, h0=h0, R=R, centre=IMPACT, outer=3.6)
    for j in S["jets"]: j.hide_render = True
    for b in S["blobs"]: b.hide_render = True
    omega = 2 * math.pi * 1.9; turns = 2.5 + 1.9 * t; vis = min(turns, 7.0)
    rc = 0.85; thread = 0.30; pitch = 0.44
    top = h0 * 0.86 + vis * pitch
    th = omega * t; n = len(S["coil"].data.splines[0].points); pts, radii = [], []
    for i in range(n):
        u = i / (n - 1); s = u * vis * 2 * math.pi
        a = th - s; z = top - s / (2 * math.pi) * pitch
        rr = rc * (1 + 0.25 * smoothstep(0.6, 1.0, u))   # lowest turns spread a little as they slump
        pts.append(Vector((IMPACT.x + rr * math.cos(a), IMPACT.y + rr * math.sin(a), z))); radii.append(thread * (1 + 0.15 * smoothstep(0.6, 1.0, u)))
    set_curve(S["coil"], pts, radii)
    land = Vector((IMPACT.x + rc * math.cos(th), IMPACT.y + rc * math.sin(th), top))
    pts, radii = stream_points(t, Z_NOZZLE - 0.2, top + thread * 0.2, land, 0.36, wob=0.05, lean=land)
    set_curve(S["stream"], pts, radii)
    S["focus"].location = (IMPACT.x, IMPACT.y, top)

def update_water(S, t):
    S["heap"].hide_render = True
    for j in S["jets"]: j.hide_render = True
    for b in S["blobs"]: b.hide_render = True
    # puddle spreads then holds, with a shiver
    k = smoothstep(0.0, 3.5, t); rp = lerp(3.5, 7.5, k) * (1 + 0.015 * math.sin(t * 7)); S["puddle"].scale = (rp, rp * 0.92, 0.12); S["puddle"].location = (IMPACT.x, IMPACT.y + 0.4, 0.0)
    pts, radii = stream_points(t, Z_NOZZLE - 0.2, 0.08, IMPACT, 0.17, wob=0.08)
    set_curve(S["stream"], pts, radii)
    rng = random.Random(7)
    for i, d in enumerate(S["drops"]):
        per = rng.uniform(0.7, 1.3); ph0 = rng.uniform(0, per); ang = rng.uniform(0, 2 * math.pi); sp = rng.uniform(40, 85); el = math.radians(rng.uniform(55, 80)); r = rng.uniform(0.38, 0.62)   # exaggerated so they read at panel size
        tau = ((t + ph0) % per) / SLOWMO   # real seconds since launch
        vx, vy, vz = sp * math.cos(el) * math.cos(ang), sp * math.cos(el) * math.sin(ang), sp * math.sin(el)
        z = 0.1 + vz * tau - 0.5 * G * tau * tau
        if z < 0: d.hide_render = True; continue
        d.hide_render = False; d.location = (IMPACT.x + vx * tau, IMPACT.y + vy * tau, z); d.scale = (r, r, r * 1.15)
    S["focus"].location = (IMPACT.x, IMPACT.y, 0.6)

def update(t):
    S = STATE["S"]; cam, tgt = S["cam"], S["cam_target"]
    t = t % T_SHOT
    {"shampoo": update_shampoo, "honey": update_honey, "water": update_water}[FLUID](S, t)
    sway = math.sin(2 * math.pi * t / T_SHOT)   # periodic drift so the loop is seamless
    if SHOT == "A":
        cam.location = (1.0 + 0.5 * sway, -48.0, 9.0 + 0.25 * sway); tgt.location = (0.0, 0.0, 12.5); cam.data.lens = 45; cam.data.dof.aperture_fstop = 3.2
    elif SHOT == "B":
        cam.location = (34.0, -30.0, 16.0 + 0.4 * sway); tgt.location = (-1.0, 0.0, 9.0); cam.data.lens = 55; cam.data.dof.aperture_fstop = 3.5
    elif SHOT == "X":
        cam.location = (-6.0 + 0.3 * sway, -26.0, 4.5); tgt.location = (-1.2, 0.0, 3.0); cam.data.lens = 85; cam.data.dof.aperture_fstop = 3.5
    else:  # panels: side view, spout at the top edge, plate across the bottom
        cam.location = (1.5, -31.0, 6.5); tgt.location = (0.0, 0.0, 9.6); cam.data.lens = 50; cam.data.dof.aperture_fstop = 3.5

STATE = {}
def on_frame(scene):
    f = scene.frame_current_final if hasattr(scene, "frame_current_final") else scene.frame_current
    update(f / FPS)

def setup_render(res, samples):
    sc = bpy.context.scene; sc.render.engine = "CYCLES"; c = sc.cycles
    c.device = "CPU"; c.samples = samples; c.use_adaptive_sampling = True; c.adaptive_threshold = 0.1; c.adaptive_min_samples = 4
    c.use_denoising = True; c.denoiser = "OPENIMAGEDENOISE"; c.denoising_input_passes = "RGB_ALBEDO_NORMAL"; c.denoising_use_gpu = False
    c.max_bounces = 5; c.diffuse_bounces = 2; c.glossy_bounces = 3; c.transmission_bounces = 4; c.volume_bounces = 0; c.transparent_max_bounces = 4
    c.caustics_reflective = False; c.caustics_refractive = False; c.blur_glossy = 1.0; c.sample_clamp_indirect = 6.0
    sc.render.use_persistent_data = True; sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5
    sc.render.resolution_x = res; sc.render.resolution_y = (round(res * 640 / 1080 / 2) * 2) if PANEL else res * 16 // 9; sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGB"; sc.render.image_settings.compression = 20
    sc.render.fps = FPS; sc.view_settings.view_transform = "AgX"
    try: sc.view_settings.look = "AgX - Medium Contrast"
    except Exception: pass
    sc.view_settings.exposure = 0.25
    sc.use_nodes = False

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

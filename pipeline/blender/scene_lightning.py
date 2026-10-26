"""Procedural Blender scene: a lightning strike on a radio mast under a storm cloud.

Run headless:
  blender -b -noaudio -P pipeline/blender/scene_lightning.py -- --shot S --start 0 --end 192 \
      --out videos/003-lightning/build/frames/S [--res 576] [--samples 24] [--preview]

The bolt is a seeded midpoint-displacement polyline (main channel + branches) rendered as bevelled
curves with an emissive shader. Phases, all functions of scene time:
  calm          cloud base flickers (intra-cloud glow)
  stepped leader the main channel grows top->bottom via bevel_factor_end in ~50 m steps (100x slow-mo),
                 branches sprout as the leader passes their root
  streamers     (shot T) short upward channels from the mast tip just before attachment
  return stroke a brightness wave sweeps UP the channel (shader mask on the curve's U coordinate),
                 a huge strike light + cloud glow, camera shake, exponential decay
  re-strikes    three dimmer pulses down the same channel (the flicker)
Shots: S wide (mast, ground, cloud base; whole event), T close on the mast tip (same event, clock offset).
"""
import bpy, bmesh, math, random, sys, os, time
from mathutils import Vector
from mathutils import noise as mnoise

def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    a = {"shot": "S", "start": 0, "end": 1, "out": "/tmp/frames", "res": 576, "samples": 14, "preview": False, "fps": 24}
    i = 0
    while i < len(argv):
        k = argv[i].lstrip("-")
        if k == "preview": a["preview"] = True; i += 1; continue
        v = argv[i + 1]; i += 2
        a[k] = type(a[k])(v) if k in a and not isinstance(a[k], bool) else v
    return a

ARGS = parse_args(); FPS = ARGS["fps"]; SHOT = ARGS["shot"].upper()
SHOT_DUR = {"S": 192 / 24, "T": 132 / 24}
T_SHOT = SHOT_DUR[SHOT]
CLOCK_OFFSET = {"S": 0.0, "T": 0.45}[SHOT]  # shot T: strike lands at T 4.0 s (frame 96)

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
def add_cylinder(name, r0, r1, h, loc, mat, segs=24, rot=(0, 0, 0)):
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=r0, radius2=r1, depth=h)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(mat)
    for p in me.polygons: p.use_smooth = True
    ob = link_obj(name, me); ob.location = loc; ob.rotation_euler = rot; return ob
def add_box(name, dims, loc, mat, rot=(0, 0, 0)):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0); me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(mat)
    ob = link_obj(name, me); ob.scale = dims; ob.location = loc; ob.rotation_euler = rot; return ob

# ----------------------------------------------------------------------------- event timing (scene seconds, shot S clock)
CLOUD_Z = 700.0; MAST_H = 60.0
T_LEADER0, T_LEADER1 = 2.4, 4.4       # stepped leader descends (100x slow motion)
T_STRIKE = 4.45                       # return stroke
RESTRIKES = [(5.05, 0.75), (5.45, 0.6), (5.75, 0.5)]
CLOUD_FLICKERS = [(0.7, 0.5), (1.6, 0.35), (3.3, 0.25)]

def pulse(t, t0, attack=0.04, hold=0.06, decay=0.32):
    if t < t0: return 0.0
    k = t - t0
    if k < attack: return k / attack
    if k < attack + hold: return 1.0
    return math.exp(-(k - attack - hold) / decay)

def strike_intensity(t):
    """0..1 brightness of the channel over the event (return stroke + re-strikes + faint afterglow)."""
    v = pulse(t, T_STRIKE)
    for ts, a in RESTRIKES: v = max(v, a * pulse(t, ts, 0.03, 0.04, 0.25))
    if t > T_STRIKE: v = max(v, 0.03 * math.exp(-(t - T_STRIKE) / 1.5))
    return v

def wave_pos(t):
    """Return-stroke front position along the channel U (1 = mast, 0 = cloud); sweeps up in ~0.12 s."""
    best = 1.0
    for ts in [T_STRIKE] + [r[0] for r in RESTRIKES]:
        if t >= ts: best = min(best, 1.0 - min(1.0, (t - ts) / 0.12) * 1.15)
    return best

def leader_progress(t):
    """Fraction of the main channel revealed, in ~50 m steps with pauses."""
    u = smoothstep(T_LEADER0, T_LEADER1, t) ** 0.85
    steps = 14
    return min(1.0, math.floor(u * steps) / steps + (u * steps - math.floor(u * steps)) * 0.15)

# ----------------------------------------------------------------------------- bolt geometry
def midpoint_path(p0, p1, levels, rough, rng, drift=0.0):
    pts = [Vector(p0), Vector(p1)]
    for lv in range(levels):
        out = [pts[0]]
        for a, b in zip(pts[:-1], pts[1:]):
            m = (a + b) / 2; seg = (b - a).length
            d = Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 0.4))) * seg * rough * (0.6 ** lv * 1.6)
            out += [m + d + Vector((0, 0, 0)), b]
        pts = out
    return pts

def build_bolt(seed=3):
    rng = random.Random(seed)
    top = Vector((70, 40, CLOUD_Z + 20)); tip = Vector((0, 0, MAST_H + 1))
    main = midpoint_path(top, tip, 7, 0.10, rng)
    # keep the last stretch converging on the mast
    for i in range(len(main) - 12, len(main)):
        k = (i - (len(main) - 12)) / 12; main[i] = main[i].lerp(Vector((0, 0, main[i].z)), k * 0.6)
    branches = []
    cum = [0.0]
    for a, b in zip(main[:-1], main[1:]): cum.append(cum[-1] + (b - a).length)
    total = cum[-1]
    for _ in range(9):
        u = rng.uniform(0.12, 0.88); i = min(range(len(cum)), key=lambda k: abs(cum[k] / total - u))
        root = main[i]; direction = (main[min(i + 2, len(main) - 1)] - main[max(i - 2, 0)]).normalized()
        side = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), -rng.uniform(0.4, 1.2))).normalized()
        d = (direction * 0.5 + side).normalized(); length = (1 - u) * rng.uniform(90, 260)
        pts = midpoint_path(root, root + d * length, 4, 0.18, rng)
        branches.append({"pts": pts, "u": u, "len": length})
        if rng.random() < 0.25:   # a sub-branch
            j = len(pts) // 2; root2 = pts[j]; d2 = (d + Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), -0.5)).normalized() * 0.8).normalized()
            branches.append({"pts": midpoint_path(root2, root2 + d2 * length * 0.45, 3, 0.3, rng), "u": u + 0.5 * (1 - u) * 0.5, "len": length * 0.45})
    streamers = []
    for k in range(3):
        d = Vector((rng.uniform(-0.6, 0.6), rng.uniform(-0.6, 0.6), 1.0)).normalized(); L = rng.uniform(22, 38)
        streamers.append(midpoint_path(tip, tip + d * L, 3, 0.25, rng))
    return main, branches, streamers

def curve_obj(name, pts, mat, radius):
    cu = bpy.data.curves.new(name, "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = radius; cu.bevel_resolution = 2
    cu.use_fill_caps = True
    sp = cu.splines.new("POLY"); sp.points.add(len(pts) - 1)
    for p, q in zip(sp.points, pts): p.co = (q.x, q.y, q.z, 1.0)
    cu.materials.append(mat); cu.bevel_factor_end = 0.0
    ob = link_obj(name, cu); ob.visible_shadow = False
    return ob

def bolt_material(name):
    """Emission: leader glow (violet) + return stroke (white-blue) masked by the U-coordinate wave."""
    m, nt, out = new_mat(name); n = nt.nodes; L = nt.links
    tc = n.new("ShaderNodeTexCoord"); sep = n.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["UV"], sep.inputs[0])   # bevelled curve UV: X runs along the spline
    lead = n.new("ShaderNodeValue"); lead.name = "leader"; lead.outputs[0].default_value = 0.0
    ret = n.new("ShaderNodeValue"); ret.name = "return"; ret.outputs[0].default_value = 0.0
    wave = n.new("ShaderNodeValue"); wave.name = "wave"; wave.outputs[0].default_value = 1.0
    sub = n.new("ShaderNodeMath"); sub.operation = "SUBTRACT"; L.new(sep.outputs["X"], sub.inputs[0]); L.new(wave.outputs[0], sub.inputs[1])
    mul = n.new("ShaderNodeMath"); mul.operation = "MULTIPLY_ADD"; mul.inputs[1].default_value = 14.0; mul.inputs[2].default_value = 0.5; mul.use_clamp = True
    L.new(sub.outputs[0], mul.inputs[0])
    lit = n.new("ShaderNodeMath"); lit.operation = "MULTIPLY"; L.new(mul.outputs[0], lit.inputs[0]); L.new(ret.outputs[0], lit.inputs[1])
    # flicker along the channel so it is not a uniform tube
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 40.0; L.new(tc.outputs["Object"], nz.inputs["Vector"])
    nzm = n.new("ShaderNodeMapRange"); nzm.inputs["From Min"].default_value = 0.3; nzm.inputs["From Max"].default_value = 0.7; nzm.inputs["To Min"].default_value = 0.6; nzm.inputs["To Max"].default_value = 1.3
    L.new(nz.outputs["Fac"], nzm.inputs["Value"])
    col_lead = (0.55, 0.45, 1.0, 1); col_ret = (0.85, 0.92, 1.0, 1)
    mixc = n.new("ShaderNodeMix"); mixc.data_type = "RGBA"; mixc.inputs[6].default_value = col_lead; mixc.inputs[7].default_value = col_ret
    fac = n.new("ShaderNodeMath"); fac.operation = "MINIMUM"; fac.inputs[1].default_value = 1.0; L.new(lit.outputs[0], fac.inputs[0]); L.new(fac.outputs[0], mixc.inputs[0])
    strength = n.new("ShaderNodeMath"); strength.operation = "MULTIPLY_ADD"; L.new(lit.outputs[0], strength.inputs[0]); strength.inputs[1].default_value = 60.0; L.new(lead.outputs[0], strength.inputs[2])
    st2 = n.new("ShaderNodeMath"); st2.operation = "MULTIPLY"; L.new(strength.outputs[0], st2.inputs[0]); L.new(nzm.outputs[0], st2.inputs[1])
    em = n.new("ShaderNodeEmission"); L.new(mixc.outputs[2], em.inputs["Color"]); L.new(st2.outputs[0], em.inputs["Strength"])
    tr = n.new("ShaderNodeBsdfTransparent"); mixs = n.new("ShaderNodeMixShader")
    vis = n.new("ShaderNodeMath"); vis.operation = "GREATER_THAN"; vis.inputs[1].default_value = 0.02; L.new(st2.outputs[0], vis.inputs[0])
    L.new(vis.outputs[0], mixs.inputs[0]); L.new(tr.outputs[0], mixs.inputs[1]); L.new(em.outputs[0], mixs.inputs[2]); L.new(mixs.outputs[0], out.inputs[0])
    return m

# ----------------------------------------------------------------------------- set
def build_world():
    w = bpy.data.worlds["World"] if "World" in bpy.data.worlds else bpy.data.worlds.new("World")
    bpy.context.scene.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.004, 0.005, 0.010, 1)

def build_set():
    S = {}; build_world(); rng = random.Random(9)
    # ground: wide, gently hilly, wet
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=90, y_segments=90, size=3000)
    for v in bm.verts:
        d = math.hypot(v.co.x, v.co.y)
        amp = 18.0 * smoothstep(80, 500, d)
        v.co.z = amp * (mnoise.noise(Vector((v.co.x / 900, v.co.y / 900, 0.3))) * 0.7 + 0.3 * mnoise.noise(Vector((v.co.x / 300, v.co.y / 300, 1.3))))
    me = bpy.data.meshes.new("ground"); bm.to_mesh(me); bm.free()
    gm = principled("ground", (0.030, 0.034, 0.028), 0.25); me.materials.append(gm)
    for p in me.polygons: p.use_smooth = True
    S["ground"] = link_obj("ground", me)
    # mast: tapered lattice stand-in + guy wires + beacon
    steel = principled("steel", (0.25, 0.26, 0.28), 0.4, 1.0)
    add_cylinder("mast", 1.6, 0.5, MAST_H, (0, 0, MAST_H / 2), steel, segs=12)
    for k in range(3):
        a = k * 2 * math.pi / 3; foot = Vector((70 * math.cos(a), 70 * math.sin(a), 0)); top = Vector((0, 0, MAST_H - 4))
        mid = (foot + top) / 2; d = top - foot; L = d.length
        rot = d.to_track_quat("Z", "Y").to_euler()
        add_cylinder(f"guy{k}", 0.08, 0.08, L, mid, steel, segs=6, rot=rot)
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=0.9); me = bpy.data.meshes.new("beacon"); bm.to_mesh(me); bm.free()
    bmat, nt, out = new_mat("beacon"); e = nt.nodes.new("ShaderNodeEmission"); e.inputs["Color"].default_value = (1, 0.1, 0.05, 1); e.inputs["Strength"].default_value = 30
    nt.links.new(e.outputs[0], out.inputs[0]); me.materials.append(bmat); S["beacon"] = link_obj("beacon", me); S["beacon"].location = (0, 0, MAST_H + 0.5)
    S["beacon_mat"] = bmat
    # a farm and some trees for scale
    wood = principled("barn", (0.06, 0.04, 0.03), 0.7); tree = principled("tree", (0.02, 0.035, 0.02), 0.8)
    add_box("barn", (26, 14, 9), (210, 120, 4.5), wood, rot=(0, 0, 0.4)); add_box("barn_roof", (28, 16, 5), (210, 120, 11), wood, rot=(0, 0, 0.4))
    add_box("house", (12, 10, 7), (260, 170, 3.5), wood, rot=(0, 0, 0.4))
    for i in range(40):
        x, y = rng.uniform(-900, 900), rng.uniform(-250, 900)
        if math.hypot(x, y) < 90: continue
        h = rng.uniform(8, 16); add_cylinder(f"tree{i}", 4.0, 0.3, h, (x, y, h / 2), tree, segs=7)
    # cloud base: displaced plane with a glow driven per frame
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=110, y_segments=110, size=4500)
    for v in bm.verts:
        v.co.z = CLOUD_Z - 70 * (0.5 + 0.5 * mnoise.noise(Vector((v.co.x / 420, v.co.y / 420, 0.7)))) - 30 * mnoise.noise(Vector((v.co.x / 120, v.co.y / 120, 2.1)))
    me = bpy.data.meshes.new("cloud"); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    cm, nt, out = new_mat("cloud"); n = nt.nodes; L = nt.links
    p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Base Color"].default_value = (0.10, 0.11, 0.14, 1); p.inputs["Roughness"].default_value = 1.0
    tc = n.new("ShaderNodeTexCoord"); nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.004; nz.inputs["Detail"].default_value = 6
    L.new(tc.outputs["Object"], nz.inputs["Vector"])
    glow = n.new("ShaderNodeValue"); glow.name = "cloudglow"; glow.outputs[0].default_value = 0.0
    gm2 = n.new("ShaderNodeMath"); gm2.operation = "MULTIPLY"; L.new(nz.outputs["Fac"], gm2.inputs[0]); L.new(glow.outputs[0], gm2.inputs[1])
    em = n.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (0.55, 0.65, 1.0, 1); L.new(gm2.outputs[0], em.inputs["Strength"])
    add = n.new("ShaderNodeAddShader"); L.new(p.outputs[0], add.inputs[0]); L.new(em.outputs[0], add.inputs[1]); L.new(add.outputs[0], out.inputs[0])
    me.materials.append(cm); S["cloud"] = link_obj("cloud", me); S["cloud_mat"] = cm
    # bolt
    main, branches, streamers = build_bolt()
    bm_mat = bolt_material("bolt"); br_mat = bolt_material("branch"); st_mat = bolt_material("streamer")
    S["main"] = curve_obj("bolt_main", main, bm_mat, 1.3)
    S["branches"] = [(curve_obj(f"branch{i}", b["pts"], br_mat, 0.55), b["u"]) for i, b in enumerate(branches)]
    S["streamers"] = [curve_obj(f"streamer{i}", p, st_mat, 0.25) for i, p in enumerate(streamers)]
    S["mats"] = {"main": bm_mat, "branch": br_mat, "streamer": st_mat}
    # lights: faint moonlight-through-cloud fill, strike light, ground bounce light
    def light(name, typ, loc, energy, color, size=1.0, rot=(0, 0, 0)):
        ld = bpy.data.lights.new(name, typ); ld.energy = energy; ld.color = color
        if typ == "AREA": ld.size = size
        if typ == "POINT": ld.shadow_soft_size = size
        if typ == "SUN": ld.angle = size
        ob = link_obj(name, ld); ob.location = loc; ob.rotation_euler = rot; return ob
    S["fill"] = light("fill", "SUN", (0, 0, 1000), 0.02, (0.5, 0.6, 1.0), size=0.5, rot=(math.radians(35), 0, math.radians(-40)))
    S["strike"] = light("strike", "POINT", (20, 10, 320), 0.0, (0.8, 0.88, 1.0), size=25)
    S["strike_low"] = light("strike_low", "POINT", (0, 0, 70), 0.0, (0.8, 0.88, 1.0), size=8)
    # camera
    cd = bpy.data.cameras.new("cam"); cam = link_obj("cam", cd); bpy.context.scene.camera = cam
    tgt = link_obj("cam_target", None)
    con = cam.constraints.new("TRACK_TO"); con.target = tgt; con.track_axis = "TRACK_NEGATIVE_Z"; con.up_axis = "UP_Y"
    cd.clip_end = 20000; S["cam"], S["cam_target"] = cam, tgt
    return S

STATE = {}

def update(t):
    S = STATE["S"]; cam, tgt = S["cam"], S["cam_target"]
    prog = leader_progress(t); inten = strike_intensity(t); wv = wave_pos(t)
    lead_on = 1.0 if (T_LEADER0 < t < T_STRIKE + 0.2) else 0.0
    S["main"].data.bevel_factor_end = max(prog, 1.0 if t >= T_STRIKE else 0.0)
    S["main"].data.bevel_depth = lerp(1.3, 2.6, inten)
    for ob, u in S["branches"]:
        k = (prog - u) / (0.25 * (1 - u) + 0.05)
        ob.data.bevel_factor_end = max(0.0, min(1.0, k)) if prog > u else (1.0 if t >= T_STRIKE else 0.0)
    for i, ob in enumerate(S["streamers"]):
        k = (t - (T_STRIKE - 0.3 - 0.05 * i)) / 0.25
        ob.data.bevel_factor_end = max(0.0, min(1.0, k)) if t < T_STRIKE + 0.4 else 0.0
    for name, m in S["mats"].items():
        n = m.node_tree.nodes
        n["leader"].outputs[0].default_value = lead_on * (1.0 if name != "branch" else 0.7) * (1 if name != "streamer" else 1.5)
        n["return"].outputs[0].default_value = inten * (1.0 if name == "main" else (0.45 if name == "branch" else 0.0))
        n["wave"].outputs[0].default_value = wv
    S["cloud_mat"].node_tree.nodes["cloudglow"].outputs[0].default_value = 0.18 * inten + 0.2 * sum(a * pulse(t, ts, 0.05, 0.1, 0.25) for ts, a in CLOUD_FLICKERS)
    S["strike"].data.energy = 8.0e7 * inten; S["strike_low"].data.energy = 2.5e6 * inten
    S["beacon_mat"].node_tree.nodes["Emission"].inputs["Strength"].default_value = 30.0 if (t % 1.2) < 0.15 else 1.0
    shake = Vector((n1(t * 30, 1), n1(t * 27, 2), n1(t * 33, 3))) * 3.0 * (math.exp(-(t - T_STRIKE) / 0.45) if t > T_STRIKE else 0.0)
    if SHOT == "S":
        k = ease_in_out(min(t / 8.0, 1.0))
        cam.location = vlerp((170, -680, 55), (120, -600, 70), k) + shake
        tgt.location = Vector((0, 0, lerp(330, 345, k))); cam.data.lens = 26
    else:
        k = ease_in_out(min(t / 5.5, 1.0))
        cam.location = vlerp((70, -190, 30), (55, -160, 45), k) + shake * 0.4
        tgt.location = Vector((0, 0, MAST_H + 70)); cam.data.lens = 32

def on_frame(scene):
    f = scene.frame_current_final if hasattr(scene, "frame_current_final") else scene.frame_current
    update(f / FPS + CLOCK_OFFSET)

def setup_render(res, samples):
    sc = bpy.context.scene; sc.render.engine = "CYCLES"; c = sc.cycles
    c.device = "CPU"; c.samples = samples; c.use_adaptive_sampling = True; c.adaptive_threshold = 0.1; c.adaptive_min_samples = 4
    c.use_denoising = True; c.denoiser = "OPENIMAGEDENOISE"; c.denoising_input_passes = "RGB_ALBEDO_NORMAL"; c.denoising_use_gpu = False
    c.max_bounces = 4; c.diffuse_bounces = 2; c.glossy_bounces = 2; c.transmission_bounces = 0; c.volume_bounces = 0; c.transparent_max_bounces = 8
    c.caustics_reflective = False; c.caustics_refractive = False; c.blur_glossy = 1.0; c.sample_clamp_indirect = 10.0
    sc.render.use_persistent_data = True; sc.render.use_motion_blur = False
    sc.render.resolution_x = res; sc.render.resolution_y = res * 16 // 9; sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGB"; sc.render.image_settings.compression = 20
    sc.render.fps = FPS; sc.view_settings.view_transform = "AgX"
    try: sc.view_settings.look = "AgX - Medium High Contrast"
    except Exception: pass
    sc.view_settings.exposure = 0.0
    sc.use_nodes = True; nt = sc.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    rl = nt.nodes.new("CompositorNodeRLayers"); gl = nt.nodes.new("CompositorNodeGlare"); comp = nt.nodes.new("CompositorNodeComposite")
    gl.glare_type = "BLOOM"
    for k, v in (("Threshold", 1.0), ("Strength", 0.3), ("Size", 0.7)):
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

"""VTuber host layer: a VRoid avatar (VRM) toon-rendered as an RGBA pass over the whole video.

Run headless (after tts.py; reads build/timeline.json and build/vo.wav):
  blender -b -noaudio -P pipeline/blender/scene_vtuber.py -- --video 006-lake-peigneur \
      --start 0 --end 1555 --out videos/006-lake-peigneur/build/frames/G [--every 1] [--preview --frame N] [--samples 8]

Why a VRM and not primitives: two procedural passes (spheres, decals, bezier hair) looked amateur. VRoid
avatars are what real 3D VTubers use: sculpted face, painted textures, and a face rig with visemes,
blink and expressions. script.json "avatar.vrm" names the file, looked up in $VRM_DIR (default
/home/user/tools/vrm; see README for the download). Host for 006: VRoid sample "AvatarSample_G" (Victoria
Rubin, VRoid Project), licence embedded in the file: anyone may use it, commercial use, modification and
redistribution allowed, no credit required.

Pipeline: the .vrm is glTF 2.0 binary, so Blender's own glTF importer loads mesh, skin, textures and the
morph targets (names *Fcl_MTH_A, *Fcl_EYE_Close, *Fcl_ALL_Joy, ...). Materials are rebuilt as toon
emission (texture x a soft N.L band, alpha cut-out), body and hair get solidify outlines, arms are posed
down from the T-pose. Everything is a pure function of the frame number:
  mouth   = VO loudness (50 ms RMS, dB-mapped, fast attack / slower release) -> A/O/E visemes
  blinks  = seeded schedule, 2.2-4.6 s apart, plus one on every beat change
  pose    = idle sway + breathing (spine/chest), talking nods (neck/head), gaze (eye bones)
  face    = expression per beat, keyed to beat starts and spoken words (expr_keys(); video-specific)
"""
import bpy, math, random, sys, os, json, time, wave, shutil, tempfile, struct
import numpy as np
from mathutils import Vector, Quaternion

def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    a = {"video": "006-lake-peigneur", "start": 0, "end": -1, "out": "", "samples": 8, "preview": False, "every": 1, "res": 640, "frame": -1}
    i = 0
    while i < len(argv):
        k = argv[i].lstrip("-")
        if k == "preview": a["preview"] = True; i += 1; continue
        v = argv[i + 1]; i += 2
        a[k] = type(a[k])(v) if k in a and not isinstance(a[k], bool) else v
    return a

ARGS = parse_args()
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
VD = os.path.join(ROOT, "videos", ARGS["video"]); BD = os.path.join(VD, "build")
TL = json.load(open(os.path.join(BD, "timeline.json"))); FPS = TL["fps"]
SCRIPT = json.load(open(os.path.join(VD, "script.json"))); AV = SCRIPT["avatar"]
RES_X = ARGS["res"]; RES_Y = int(round(RES_X * AV["height"] / AV["width"] / 2) * 2)
OUT = ARGS["out"] or os.path.join(BD, AV["dir"])
VRM = os.path.join(os.environ.get("VRM_DIR", "/home/user/tools/vrm"), AV.get("vrm", "AvatarSample_G.vrm"))
LIGHT = Vector((0.45, 0.75, 0.55)).normalized()   # VRMs face +y in Blender, so the key light sits on +y

# ------------------------------------------------------------------ build
def toonify(m):
    """Texture (or base colour) x a soft two-step N.L band, as Emission; alpha cut-out / blend kept."""
    nt = m.node_tree
    if not nt: return
    tex = next((n for n in nt.nodes if n.type == 'TEX_IMAGE'), None)
    bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    out = next((n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'), None)
    if not out: return
    em = nt.nodes.new('ShaderNodeEmission')
    geo = nt.nodes.new('ShaderNodeNewGeometry'); dot = nt.nodes.new('ShaderNodeVectorMath'); dot.operation = 'DOT_PRODUCT'; dot.inputs[1].default_value = tuple(LIGHT)
    nt.links.new(geo.outputs['Normal'], dot.inputs[0])
    ramp = nt.nodes.new('ShaderNodeValToRGB'); ramp.color_ramp.interpolation = 'CONSTANT'
    ramp.color_ramp.elements[0].color = (0.86, 0.82, 0.92, 1); ramp.color_ramp.elements[1].position = 0.38; ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
    mr = nt.nodes.new('ShaderNodeMath'); mr.operation = 'MULTIPLY_ADD'; mr.inputs[1].default_value = 0.5; mr.inputs[2].default_value = 0.5
    nt.links.new(dot.outputs['Value'], mr.inputs[0]); nt.links.new(mr.outputs[0], ramp.inputs['Fac'])
    mul = nt.nodes.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1.0
    if tex: nt.links.new(tex.outputs['Color'], mul.inputs['A'])
    elif bsdf: mul.inputs['A'].default_value = bsdf.inputs['Base Color'].default_value
    nt.links.new(ramp.outputs['Color'], mul.inputs['B']); nt.links.new(mul.outputs['Result'], em.inputs['Color'])
    a = tex.outputs['Alpha'] if (tex and m.blend_method != 'OPAQUE') else (bsdf.inputs['Alpha'].links[0].from_socket if bsdf and bsdf.inputs['Alpha'].is_linked else None)
    if a is not None:
        if m.blend_method == 'CLIP':
            gt = nt.nodes.new('ShaderNodeMath'); gt.operation = 'GREATER_THAN'; gt.inputs[1].default_value = 0.5; nt.links.new(a, gt.inputs[0]); a = gt.outputs[0]
        tr = nt.nodes.new('ShaderNodeBsdfTransparent'); mix = nt.nodes.new('ShaderNodeMixShader')
        nt.links.new(a, mix.inputs['Fac']); nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(em.outputs[0], mix.inputs[2]); nt.links.new(mix.outputs[0], out.inputs['Surface'])
    else:
        nt.links.new(em.outputs[0], out.inputs['Surface'])

def outline_mat():
    ol = bpy.data.materials.new('outline'); ol.use_nodes = True; nt = ol.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    o_ = nt.nodes.new('ShaderNodeOutputMaterial'); g = nt.nodes.new('ShaderNodeNewGeometry'); e = nt.nodes.new('ShaderNodeEmission'); e.inputs['Color'].default_value = (0.035, 0.02, 0.05, 1)
    t = nt.nodes.new('ShaderNodeBsdfTransparent'); mx = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(g.outputs['Backfacing'], mx.inputs['Fac']); nt.links.new(e.outputs[0], mx.inputs[1]); nt.links.new(t.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], o_.inputs['Surface'])
    return ol

def build():
    for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
    tmp = os.path.join(tempfile.mkdtemp(), "avatar.glb"); shutil.copy(VRM, tmp)   # .vrm is glTF binary
    bpy.ops.import_scene.gltf(filepath=tmp)
    S = {}; arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE'); S['arm'] = arm
    bpy.context.view_layer.update()
    S['rest'] = {pb.name: (arm.matrix_world @ pb.bone.matrix_local).to_quaternion() for pb in arm.pose.bones}
    for m in bpy.data.materials: toonify(m)
    ol = outline_mat()
    # Blender's importer names morph targets target_0..N; the VRoid names live in the glTF JSON (mesh/primitive extras)
    raw = open(VRM, 'rb').read(); n = struct.unpack('<I', raw[12:16])[0]; gj = json.loads(raw[20:20 + n])
    tnames = {}
    for me in gj['meshes']:
        tn = me.get('extras', {}).get('targetNames') or me['primitives'][0].get('extras', {}).get('targetNames')
        if tn: tnames[me['name']] = tn
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.data.shape_keys:
            tn = tnames.get(o.data.name) or next((v for v in tnames.values() if len(v) == len(o.data.shape_keys.key_blocks) - 1), None)
            if tn:
                for kb, name in zip(o.data.shape_keys.key_blocks[1:], tn): kb.name = name
    arm.rotation_mode = 'XYZ'   # glTF import leaves objects in quaternion mode, which ignores rotation_euler
    S['keys'] = {}
    for o in bpy.data.objects:
        if o.type != 'MESH': continue
        if any(k in o.name for k in ('Body', 'Hair')):
            # thin: a hull on VRoid's double-sided cards (ponytail, corset laces) draws thick black bars at 2+ mm
            n = len(o.data.materials); o.data.materials.append(ol)
            sm = o.modifiers.new('outline', 'SOLIDIFY'); sm.thickness = 0.0009; sm.offset = 1.0; sm.use_flip_normals = True; sm.material_offset = n; sm.use_rim = False
        if o.data.shape_keys:
            for kb in o.data.shape_keys.key_blocks:
                if 'Fcl_' in kb.name: S['keys'][kb.name.split('Fcl_')[-1]] = kb
    print("blendshapes:", sorted(S['keys']))
    # camera: orthographic bust shot from +y (VRMs face +y here), framed on the rest-pose head
    hp = arm.matrix_world @ arm.pose.bones['J_Bip_C_Head'].head
    cd = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cd); bpy.context.collection.objects.link(cam); bpy.context.scene.camera = cam
    cd.type = 'ORTHO'; cd.ortho_scale = AV.get("ortho_scale", 0.74); cd.sensor_fit = 'VERTICAL'
    cam.location = (hp.x, hp.y + 3.0, hp.z + AV.get("cam_dz", -0.11)); cam.rotation_euler = (math.pi / 2, 0, math.pi); S['cam'] = cam
    return S

def set_rot(S, bname, axis, ang, mul=None):
    """Rotate a pose bone by `ang` about a WORLD axis (applied on top of earlier calls in this frame via mul)."""
    arm = S['arm']; pb = arm.pose.bones.get(bname)
    if not pb: return
    pb.rotation_mode = 'QUATERNION'; ml = S['rest'][bname]
    q = Quaternion(axis, ang) if mul is None else mul
    pb.rotation_quaternion = ml.inverted() @ q @ ml

def qworld(*rots):
    q = Quaternion()
    for axis, ang in rots: q = Quaternion(axis, ang) @ q
    return q

# ------------------------------------------------------------------ drivers: VO envelope, blinks, expressions
def vo_envelope():
    w = wave.open(TL["vo"], 'rb'); sr = w.getframerate(); n = w.getnframes(); sw = w.getsampwidth()
    raw = w.readframes(n); w.close()
    x = np.frombuffer(raw, dtype={2: np.int16, 4: np.int32}[sw]).astype(np.float64) / (2 ** (8 * sw - 1))
    if w.getnchannels() > 1: x = x.reshape(-1, w.getnchannels()).mean(1)
    nfr = TL["total_frames"] + 2; env = np.zeros(nfr); half = int(0.025 * sr)
    for f in range(nfr):
        c = int(f / FPS * sr); seg = x[max(c - half, 0): c + half]
        rms = math.sqrt(float((seg ** 2).mean())) if len(seg) else 0.0
        db = 20 * math.log10(rms + 1e-9); env[f] = min(max((db + 40) / 20, 0), 1)
    out = np.zeros(nfr); y = 0.0
    for f in range(nfr):   # fast attack, slower release
        y = env[f] if env[f] > y else y + (env[f] - y) * 0.45; out[f] = y
    return out

def word_time(beat, word, nth=0):
    b = next(b for b in TL["beats"] if b["id"] == beat); n = 0
    for l in b["lines"]:
        for w in l["words"]:
            if "".join(ch for ch in w["word"].lower() if ch.isalnum() or ch == "'") == word:
                if n == nth: return w["start"]
                n += 1
    return b["start"]
def beat_start(bid): return next(b["start"] for b in TL["beats"] if b["id"] == bid)

# expression presets -> VRoid blendshapes (fun/joy/surprised/sorrow are whole-face; brows separately)
# keys: fun, joy, surp, brw_surp, brw_sorrow, eye_surp, gx/gz (gaze, radians), lean (body roll), nod (head pitch), turn (head yaw)
EXPR = {
    'talk':  dict(fun=0.35, joy=0.0, surp=0.0, brw_surp=0.0, brw_sorrow=0.0, eye_surp=0.0, gx=0.0, gz=0.0, lean=0.0, nod=0.0, turn=0.0),
    'shock': dict(fun=0.0, joy=0.0, surp=0.5, brw_surp=0.35, brw_sorrow=0.0, eye_surp=0.3, gx=0.12, gz=0.06, lean=-0.04, nod=-0.06, turn=0.16),
    'happy': dict(fun=0.0, joy=0.85, surp=0.0, brw_surp=0.0, brw_sorrow=0.0, eye_surp=0.0, gx=0.0, gz=0.0, lean=0.05, nod=0.05, turn=0.0),
    'think': dict(fun=0.1, joy=0.0, surp=0.0, brw_surp=0.0, brw_sorrow=0.45, eye_surp=0.0, gx=-0.1, gz=0.1, lean=0.07, nod=0.04, turn=-0.12),
    'look':  dict(fun=0.15, joy=0.0, surp=0.25, brw_surp=0.25, brw_sorrow=0.0, eye_surp=0.1, gx=0.16, gz=0.05, lean=-0.03, nod=-0.05, turn=0.22),
}
def expr_keys():
    """Video-specific: (time, preset). Story beats react to the scene, physics beats explain."""
    K = [(0.0, 'shock'), (beat_start('setup'), 'talk'), (beat_start('setup') + 1.6, 'look'), (beat_start('setup') + 3.4, 'talk'),
         (beat_start('mine'), 'talk'), (word_time('mine', 'punched') - 0.1, 'shock'),
         (beat_start('whirlpool'), 'shock'), (word_time('whirlpool', 'swallowed'), 'look'),
         (beat_start('waterfall'), 'shock'), (word_time('waterfall', 'every') - 0.1, 'happy'),
         (beat_start('why'), 'think'), (beat_start('spin'), 'talk'), (beat_start('salt'), 'talk'),
         (beat_start('payoff'), 'happy'), (beat_start('cta'), 'happy')]
    return sorted(K)
KEYS = None
def expr_at(t, blend=0.2):
    cur = dict(EXPR[KEYS[0][1]])
    for i, (tk, name) in enumerate(KEYS):
        if t < tk: break
        k = min(max((t - tk) / blend, 0), 1); k = k * k * (3 - 2 * k); tgt = EXPR[name]
        cur = {p: cur[p] + (tgt[p] - cur[p]) * k for p in cur}
    return cur

def blink_at(t):
    rng = random.Random(11); bt = []; x = 1.2
    while x < TL["duration"] + 5: bt.append(x); x += rng.uniform(2.2, 4.6)
    bt += [b["start"] + 0.08 for b in TL["beats"][1:]]
    b = 0.0
    for t0 in bt:
        d = t - t0
        if 0 <= d < 0.05: b = max(b, d / 0.05)
        elif 0.05 <= d < 0.14: b = max(b, 1 - (d - 0.05) / 0.09)
    return b

# ------------------------------------------------------------------ per-frame update
Z, X, Y = Vector((0, 0, 1)), Vector((1, 0, 0)), Vector((0, 1, 0))
def update(S, f, ENV):
    t = f / FPS; E = expr_at(t); amp = float(ENV[min(f, len(ENV) - 1)]); K = S['keys']
    def sk(name, v):
        if name in K: K[name].value = max(0.0, min(1.0, v))
    # face: whole-face expression, brows, then visemes on top (scaled down under joy/surprise, which open the mouth themselves)
    sk('ALL_Fun', E['fun']); sk('ALL_Joy', E['joy']); sk('ALL_Surprised', E['surp'])
    sk('BRW_Surprised', E['brw_surp']); sk('BRW_Sorrow', E['brw_sorrow']); sk('EYE_Surprised', E['eye_surp'])
    open_k = 1 - 0.6 * max(E['joy'], E['surp'])
    w = 0.5 + 0.5 * math.sin(2 * math.pi * 2.7 * t) * math.sin(2 * math.pi * 0.9 * t + 1)   # cheap vowel variety
    sk('MTH_A', amp * 0.85 * (1 - 0.6 * w) * open_k); sk('MTH_O', amp * 0.55 * w * open_k); sk('MTH_E', amp * 0.25 * (1 - w) * open_k)
    bl = blink_at(t) * (1 - E['joy'])   # joy already closes the eyes
    sk('EYE_Close', bl)
    # pose: arms down from the T-pose, body turned ~12 deg towards frame right (the 3D scene), breathing + sway
    for side, s in (("L", 1), ("R", -1)):
        set_rot(S, f"J_Bip_{side}_UpperArm", Y, -s * math.radians(70 - 2 * math.sin(2 * math.pi * t / 3.6)))
        set_rot(S, f"J_Bip_{side}_LowerArm", Z, s * math.radians(12))
    S['arm'].rotation_euler = (0, 0, 0.2)   # +z turns a +y-facing model towards -x = frame right
    breath = math.sin(2 * math.pi * t / 3.6)
    set_rot(S, 'J_Bip_C_Spine', None, None, qworld((Y, E['lean'] * 0.5 + 0.02 * math.sin(2 * math.pi * t / 5.1)), (X, 0.012 * breath)))
    set_rot(S, 'J_Bip_C_UpperChest', X, -0.01 * breath)
    nod = E['nod'] + 0.05 * amp * math.sin(2 * math.pi * t * 2.1) + 0.02 * math.sin(2 * math.pi * t / 2.9)
    set_rot(S, 'J_Bip_C_Neck', None, None, qworld((Z, 0.5 * (E['turn'] + 0.03 * math.sin(2 * math.pi * t / 6.1))), (X, -0.5 * nod)))
    set_rot(S, 'J_Bip_C_Head', None, None, qworld((Y, E['lean'] + 0.035 * math.sin(2 * math.pi * t / 4.3 + 1.0)), (Z, 0.5 * E['turn']), (X, -0.5 * nod)))
    for side in ("L", "R"):
        set_rot(S, f"J_Adj_{side}_FaceEye", None, None, qworld((Z, E['gx']), (X, E['gz'])))

def setup_render():
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; c = sc.cycles
    c.device = 'CPU'; c.samples = ARGS["samples"]; c.use_adaptive_sampling = False; c.use_denoising = False
    c.max_bounces = 0; c.transparent_max_bounces = 24; c.use_light_tree = False
    c.pixel_filter_type = 'BLACKMAN_HARRIS'; c.filter_width = 1.3
    sc.render.film_transparent = True; sc.render.use_persistent_data = False   # skinned + shape-keyed meshes change every frame
    sc.render.resolution_x = RES_X; sc.render.resolution_y = RES_Y; sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'; sc.render.image_settings.compression = 15
    sc.render.fps = FPS; sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'; sc.use_nodes = False

def main():
    global KEYS
    S = build(); KEYS = expr_keys(); ENV = vo_envelope(); setup_render()
    os.makedirs(OUT, exist_ok=True); sc = bpy.context.scene
    end = ARGS["end"] if ARGS["end"] >= 0 else TL["total_frames"]
    frames = [ARGS["frame"] if ARGS["frame"] >= 0 else ARGS["start"]] if ARGS["preview"] else range(ARGS["start"], end, ARGS["every"])
    for f in frames:
        path = os.path.join(OUT, f"G_{f:04d}.png")
        if os.path.exists(path) and not ARGS["preview"]: continue
        update(S, f, ENV); sc.frame_set(f); sc.render.filepath = path
        t0 = time.time(); bpy.ops.render.render(write_still=True)
        print(f"FRAME G {f} {time.time() - t0:.2f}s", flush=True)

main()

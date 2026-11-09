"""Procedural low-poly anime host ("VTuber") rendered as an RGBA layer for the whole video.

Run headless (after tts.py, it reads the timeline and the VO):
  blender -b -noaudio -P pipeline/blender/scene_vtuber.py -- --video 006-lake-peigneur \
      --start 0 --end 1555 --out videos/006-lake-peigneur/build/frames/G [--every 1] [--preview] [--samples 6]

Everything is a pure function of the frame number:
  mouth   = VO loudness (50 ms RMS of build/vo.wav, dB-mapped, fast attack / slower release)
  blinks  = seeded schedule, 2.2-4.6 s apart, plus one on every beat change
  pose    = idle sway + breathing + small talking nods, per-expression lean/tilt
  face    = expression per beat, keyed to beat starts and spoken words (EXPR_KEYS below; video-specific table)
Look: toon.py (cel bands, inverted-hull outlines, emission only), orthographic camera, transparent film.
Character: pink hair (bangs, side locks, back blades, ahoge), aqua eyes, sailor collar + red bow,
cat-ear headset with a mic boom. Faces the camera turned ~10 deg towards frame right (the 3D scene).
"""
import bpy, bmesh, math, random, sys, os, json, time, wave
import numpy as np
from mathutils import Vector, Matrix, Euler
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from toon import *

def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    a = {"video": "006-lake-peigneur", "start": 0, "end": -1, "out": "", "samples": 6, "preview": False, "every": 1, "res": 640, "frame": -1}
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

# ------------------------------------------------------------------ palette
SKIN, SKIN_SH = '#FFE7DA', (0.97, 0.80, 0.80)
HAIR, HAIR_DK, HAIR_SH = '#FF93C4', '#E2679F', (0.80, 0.62, 0.86)
IRIS_DK, IRIS, IRIS_LT, PUPIL = '#1D4E96', '#2C93D6', '#7FEAF5', '#0D1F45'
LASH, BROW = '#3A1E33', '#C9578C'
SHIRT, COLLAR, BOW = '#F8F8FC', '#283272', '#EE3B57'
HEADSET, GLOW, EAR_IN = '#2E2C3C', '#7CF3FF', '#FFB8D4'

# ------------------------------------------------------------------ helpers
def attach(o, parent):
    bpy.context.view_layer.update()   # matrix_world of freshly placed objects is stale until the depsgraph updates
    mw = o.matrix_world.copy(); o.parent = parent; o.matrix_parent_inverse = parent.matrix_world.inverted(); o.matrix_world = mw; return o
def empty(name, loc=(0, 0, 0), parent=None):
    e = bpy.data.objects.new(name, None); bpy.context.collection.objects.link(e); e.location = loc
    if parent: attach(e, parent)
    return e

FACE_R = 1.0   # curvature radius for face decals
def decal(name, pts2, mat, parent, layer=0, curve=FACE_R):
    """Flat shape in the parent's local xz plane, bent onto a sphere of radius `curve` so it hugs the face; layer = stacking order."""
    verts = [(x, -0.012 - 0.0035 * layer + (x * x + z * z) / (2 * curve), z) for x, z in pts2]
    f = list(range(len(verts)))[::-1]
    o = mesh_from(name, verts, [f], mat); o.parent = parent; return o
def decal_strip(name, pts2, width, mat, parent, layer=0, taper=(1, 1), curve=FACE_R):
    o = strip(name, pts2, width, mat, taper=taper); o.parent = parent
    for v in o.data.vertices: v.co.y = -0.012 - 0.0035 * layer + (v.co.x ** 2 + v.co.z ** 2) / (2 * curve)
    return o

# ------------------------------------------------------------------ build
def build():
    clear_scene(); S = {}
    M = {k: v for k, v in dict(
        skin=toon_mat('skin', SKIN, shade=SKIN_SH, hi=1.03, steps=(0.40, 0.92)),
        hair=toon_mat('hair', HAIR, shade=HAIR_SH, hi=1.10, rim=0.45, rim_col='#FFE3F2', steps=(0.48, 0.84)),
        hair_dk=toon_mat('hair_dk', HAIR_DK, shade=HAIR_SH, hi=None),
        white=flat_mat('white', '#FFFFFF'), sclera=flat_mat('sclera', '#FFFFFF'),
        iris_dk=flat_mat('iris_dk', IRIS_DK), iris=flat_mat('iris', IRIS), iris_lt=flat_mat('iris_lt', IRIS_LT), pupil=flat_mat('pupil', PUPIL),
        lash=flat_mat('lash', LASH), brow=flat_mat('brow', BROW), mouth=flat_mat('mouth', '#9C2E45'), tongue=flat_mat('tongue', '#F07D93'),
        lip=flat_mat('lip', '#7A2C3C'), blush=flat_mat('blush', '#FF7FA0', alpha=0.42), blushline=flat_mat('blushline', '#F0607F', alpha=0.75),
        nose=flat_mat('nose', '#F2B3A6'), sweat=flat_mat('sweat', '#9FE6FF', alpha=0.9),
        shirt=toon_mat('shirt', SHIRT, shade=(0.80, 0.82, 0.95), hi=None, steps=(0.45, 0.9)), collar=toon_mat('collar', COLLAR, shade=0.7, hi=1.15, rim=0.3, rim_col='#8FA0FF'),
        bow=toon_mat('bow', BOW, shade=0.72, hi=1.1), headset=toon_mat('headset', HEADSET, shade=0.75, hi=1.35, rim=0.5, rim_col='#7CF3FF'),
        glow=flat_mat('glow', GLOW, strength=1.0), ear_in=flat_mat('ear_in', EAR_IN),
    ).items()}
    body = empty('body', (0, 0, -1.3)); S['body'] = body
    headp = empty('head_pivot', (0, 0, -0.62)); attach(headp, body); S['head'] = headp

    # --- head: sphere, narrow jaw, longer lower face
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=18, v_segments=12, radius=1.0)
    for v in bm.verts:
        x, y, z = v.co
        if z < 0:
            k = -z; x *= 1 - 0.34 * k ** 1.5; y *= 1 - 0.16 * k; z *= 1.10
            if k > 0.6: y -= 0.05 * (k - 0.6)
        y *= 0.94; v.co = Vector((x, y, z))
    me = bpy.data.meshes.new('head'); bm.to_mesh(me); bm.free()
    head = bpy.data.objects.new('head', me); bpy.context.collection.objects.link(head); me.materials.append(M['skin'])
    for p in me.polygons: p.use_smooth = True
    attach(head, headp); outline(head, 0.022)
    bpy.context.view_layer.update()
    def face_pt(x, z):
        hit, loc, nrm, _ = head.ray_cast(Vector((x, -3, z)), Vector((0, 1, 0)))
        return (loc, nrm) if hit else (Vector((x, -0.9, z)), Vector((0, -1, 0)))
    def face_frame(name, x, z, yaw_k=1.0):
        loc, nrm = face_pt(x, z)
        e = bpy.data.objects.new(name, None); bpy.context.collection.objects.link(e)
        e.parent = head; e.location = loc; e.rotation_euler = (0, 0, math.atan2(nrm.x, -nrm.y) * yaw_k); return e

    # --- eyes
    S['eyes'] = []
    for side in (-1, 1):
        ex, ez = 0.39 * side, -0.17
        E = face_frame(f'eye{side}', ex, ez, 0.8); E.scale = (1.2, 1.0, 1.2)   # big anime eyes
        open_g = empty(f'eye_open{side}'); open_g.parent = E
        # sclera: rounded, flatter on top, outer corner slightly lifted
        sc = [(0.17 * math.cos(a) * (1 + 0.08 * side * math.cos(a)), (0.19 if math.sin(a) > 0 else 0.16) * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 22, endpoint=False)]
        decal(f'sclera{side}', sc, M['sclera'], open_g, 0)
        iris_g = empty(f'iris{side}'); iris_g.parent = open_g
        decal(f'irisdk{side}', ellipse(0.122, 0.158, 18, 0, -0.005), M['iris_dk'], iris_g, 1)
        decal(f'iris{side}', ellipse(0.105, 0.12, 18, 0, -0.035), M['iris'], iris_g, 2)
        decal(f'irislt{side}', ellipse(0.085, 0.06, 16, 0, -0.085), M['iris_lt'], iris_g, 3)
        pup = decal(f'pupil{side}', ellipse(0.048, 0.072, 14, 0, 0.0), M['pupil'], iris_g, 4)
        decal(f'hl1{side}', ellipse(0.042, 0.05, 12, -0.045, 0.065), M['white'], iris_g, 5)
        decal(f'hl2{side}', ellipse(0.02, 0.02, 10, 0.05, -0.07), M['white'], iris_g, 5)
        # lashes: thick upper line with an outer flick, thin lower line
        up = [(0.185 * math.cos(a), 0.195 * math.sin(a) + 0.005) for a in np.linspace(math.pi * 0.98, math.pi * 0.02, 14)]
        if side < 0: up = up[::-1]
        # up runs inner -> outer; add the flick past the outer corner
        o = up[-1]; up.append((o[0] + 0.06 * side, o[1] + 0.035))
        decal_strip(f'lash{side}', up, 0.05, M['lash'], open_g, 6, taper=(0.5, 0.9))
        lo = [(0.12 * math.cos(a), -0.17 * math.sin(a) - 0.0) for a in np.linspace(math.pi * 0.25, math.pi * 0.75, 6)]
        decal_strip(f'lashlo{side}', [(x * side + 0.05 * side, z) for x, z in lo], 0.018, M['lash'], open_g, 6)
        # closed eye (blink): a downward arc; happy eye: an upward arc
        cl = [(0.17 * math.cos(a), -0.06 * math.sin(a) - 0.02) for a in np.linspace(math.pi, 0, 10)]
        closed = decal_strip(f'closed{side}', cl, 0.045, M['lash'], E, 6)
        hp = [(0.15 * math.cos(a), 0.09 * math.sin(a) - 0.06) for a in np.linspace(math.pi, 0, 10)]
        happy = decal_strip(f'happy{side}', hp, 0.05, M['lash'], E, 6)
        # brow (on the face, above the eye; hidden partly by bangs, which is fine and very anime)
        B = face_frame(f'brow{side}', 0.36 * side, 0.15, 0.8)
        br = [(x, 0.018 * math.sin(math.pi * (x + 0.12) / 0.24)) for x in np.linspace(-0.12, 0.12, 6)]
        decal_strip(f'browm{side}', br, 0.032, M['brow'], B, 7, taper=(1.0, 0.5) if side > 0 else (0.5, 1.0))
        S['eyes'].append(dict(side=side, E=E, open=open_g, iris=iris_g, pupil=pup, closed=closed, happy=happy, brow=B, brow0=B.location.copy()))

    # --- nose, mouth, blush, sweat drop
    N = face_frame('nose', 0.0, -0.36, 1.0); decal('nosem', [(-0.025, 0.0), (0.02, 0.012), (0.0, -0.03)], M['nose'], N, 1)
    Mo = face_frame('mouth', 0.0, -0.56, 1.0); S['mouth_frame'] = Mo
    mo_open = empty('mouth_open'); mo_open.parent = Mo; S['mouth_open'] = mo_open
    D = [(-0.11, 0.0)] + [(0.11 * math.cos(a), 0.11 * math.sin(a)) for a in np.linspace(math.pi, 2 * math.pi, 12)][1:-1] + [(0.11, 0.0), (0.0, 0.012)]
    decal('mouthm', D, M['mouth'], mo_open, 2, curve=0.9)
    decal('tongue', [(0.06 * math.cos(a), 0.035 * math.sin(a) - 0.075) for a in np.linspace(0, 2 * math.pi, 12, endpoint=False)], M['tongue'], mo_open, 3, curve=0.9)
    sm = [(x, 0.035 * (x / 0.07) ** 2 - 0.03) for x in np.linspace(-0.07, 0.07, 7)]
    S['mouth_closed'] = decal_strip('smile', sm, 0.022, M['lip'], Mo, 2, curve=0.9)
    for side in (-1, 1):
        Bl = face_frame(f'blush{side}', 0.47 * side, -0.38, 0.9)
        decal(f'blushm{side}', ellipse(0.13, 0.055, 14), M['blush'], Bl, 0)
        for k in range(3):
            x0 = -0.05 + 0.045 * k
            decal_strip(f'bl{side}{k}', [(x0 + 0.02, 0.025), (x0 - 0.01, -0.025)], 0.012, M['blushline'], Bl, 1)
        S.setdefault('blush', []).append(Bl)
    Sw = empty('sweat', (0.8, -1.05, 0.42), headp); Sw.scale = (1.5, 1, 1.5)   # in front of the bangs at the temple, anime-style
    decal('sweatm', [(0.0, 0.08)] + [(0.04 * math.cos(a), 0.045 * math.sin(a) - 0.02) for a in np.linspace(math.pi * 0.15, -math.pi * 1.15, 12)], M['sweat'], Sw, 9)
    S['sweat'] = Sw

    # --- hair
    hc = Vector((0, 0.04, 0.06)); R = 1.08
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=R)
    kill = [f for f in bm.faces if (f.calc_center_median().y < -0.18 and f.calc_center_median().z < 0.42 and abs(f.calc_center_median().x) < 0.80) or f.calc_center_median().z < -0.62]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    for v in bm.verts: v.co.x *= 1.04; v.co += hc
    me = bpy.data.meshes.new('hair_cap'); bm.to_mesh(me); bm.free()
    cap = bpy.data.objects.new('hair_cap', me); bpy.context.collection.objects.link(cap); me.materials.append(M['hair'])
    attach(cap, headp); outline(cap, 0.018)
    def sph(az, el, r=R):
        az, el = math.radians(az), math.radians(el)
        return hc + Vector((math.sin(az) * math.cos(el) * r * 1.04, -math.cos(az) * math.cos(el) * r, math.sin(el) * r))
    strands = []
    # bangs: alternating long/short spikes across the forehead, tips just above the eyes
    nb = 9
    for i in range(nb):
        u = i / (nb - 1); az = -62 + 124 * u; L = 0.0 if i % 2 else 0.1
        root = sph(az * 0.8, 52); tip = sph(az * 1.02 + (6 if az > 0 else -6) * (u - 0.5), 4 + 10 * (i % 2) - (8 if abs(az) > 50 else 0), R + 0.07)
        tip.z -= L; ctrl = (root + tip) / 2; ctrl += (ctrl - hc).normalized() * 0.32
        strands.append(blade(f'bang{i}', root, ctrl, tip, 0.36, 0.12, M['hair'], segs=4, side=Vector((math.cos(math.radians(az)), math.sin(math.radians(az)), 0))))
    # side locks down to the chest, in front of the shoulders
    for side in (-1, 1):
        root = sph(76 * side, 25); tip = Vector((0.98 * side, -0.42, -1.95)); ctrl = Vector((1.22 * side, -0.38, -0.5))
        strands.append(blade(f'side{side}', root, ctrl, tip, 0.34, 0.14, M['hair'], segs=6, side=Vector((0, 1, 0))))
        root = sph(98 * side, 15); tip = Vector((1.22 * side, -0.05, -2.2)); ctrl = Vector((1.4 * side, -0.1, -0.6))
        strands.append(blade(f'side2{side}', root, ctrl, tip, 0.4, 0.16, M['hair_dk'], segs=6, side=Vector((0, 1, 0))))
    # back hair: wide blades behind the body
    for i, az in enumerate(np.linspace(110, 250, 7)):
        root = sph(az, 18); dirn = Vector((math.sin(math.radians(az)), -math.cos(math.radians(az)), 0))
        tip = hc + dirn * 1.25 + Vector((0, 0.25, -2.7 - 0.25 * (i % 2))); ctrl = hc + dirn * 1.55 + Vector((0, 0.2, -0.8))
        strands.append(blade(f'back{i}', root, ctrl, tip, 0.75, 0.2, M['hair_dk'], segs=6, side=Vector((math.cos(math.radians(az)), math.sin(math.radians(az)), 0))))
    # ahoge
    strands.append(blade('ahoge', sph(-8, 80), hc + Vector((0.15, -0.55, 1.75)), hc + Vector((0.42, -0.62, 1.38)), 0.13, 0.05, M['hair'], segs=5, side=Vector((0, 1, 0)), tip=0.1))
    for s in strands:
        for p in s.data.polygons: p.use_smooth = False
        attach(s, headp); outline(s, 0.016)

    # --- headset with cat ears
    band = blade('band', Vector((-1.12, 0.05, -0.02)), Vector((0, 0.05, 2.32)), Vector((1.12, 0.05, -0.02)), 0.16, 0.1, M['headset'], segs=10, side=Vector((0, 1, 0)), tip=1.0)
    attach(band, headp); outline(band, 0.016)
    for side in (-1, 1):
        cup = cyl(f'cup{side}', 0.32, 0.28, 0.0, 0.2, M['headset'], n=10, loc=(1.04 * side, 0.02, -0.08), rot=(0, math.pi / 2 * side, 0))
        attach(cup, headp); outline(cup, 0.016)
        g = cyl(f'cupglow{side}', 0.2, 0.2, 0.0, 0.02, M['glow'], n=10, loc=(1.245 * side, 0.02, -0.08), rot=(0, math.pi / 2 * side, 0)); attach(g, headp)
        # cat ear on the band: a low pyramid, pink inner face
        bx, bz = 0.62 * side, 0.92
        v = [Vector((bx - 0.24, -0.1, bz)), Vector((bx + 0.24, -0.1, bz)), Vector((bx + 0.0, 0.18, bz - 0.02)), Vector((bx + 0.12 * side, -0.02, bz + 0.5))]
        ear = mesh_from(f'ear{side}', v, [(0, 1, 3), (1, 2, 3), (2, 0, 3), (0, 2, 1)], M['headset'])
        bmx = bmesh.new(); bmx.from_mesh(ear.data); bmesh.ops.recalc_face_normals(bmx, faces=bmx.faces[:]); bmx.to_mesh(ear.data); bmx.free()
        attach(ear, headp); outline(ear, 0.016)
        c = (v[0] + v[1] + v[3]) / 3; vi = [c + (p - c) * 0.6 + Vector((0, -0.02, 0)) for p in (v[0], v[1], v[3])]
        inn = mesh_from(f'earin{side}', vi, [(0, 1, 2)], M['ear_in']); attach(inn, headp)
    mic = blade('mic', Vector((-1.1, -0.15, -0.25)), Vector((-1.0, -0.75, -0.75)), Vector((-0.42, -0.95, -0.72)), 0.05, 0.05, M['headset'], segs=6, side=Vector((0, 0, 1)), tip=1.0)
    attach(mic, headp); outline(mic, 0.012)
    tipb = ico('mic_tip', 0.07, M['glow'], loc=(-0.4, -0.96, -0.72)); attach(tipb, headp)

    # --- neck, torso, sailor collar, bow, arms
    neck = cyl('neck', 0.2, 0.23, 0.0, 0.75, M['skin'], n=10, loc=(0, 0.06, -1.4)); attach(neck, body); outline(neck, 0.016)
    rings = [ring(0, 0.05, z, rx * 0.86, ry, 14, 2.6) for z, rx, ry in [(-1.2, 0.32, 0.26), (-1.38, 0.82, 0.42), (-1.58, 1.08, 0.52), (-1.95, 1.04, 0.55), (-2.7, 0.92, 0.55), (-3.5, 0.9, 0.55), (-4.4, 0.92, 0.56)]]
    torso = loft('torso', rings, M['shirt']); attach(torso, body); outline(torso, 0.022)
    crings = [ring(0, 0.05, z, rx * 0.86 if z < -1.2 else rx, ry, 14, 2.6) for z, rx, ry in [(-1.17, 0.37, 0.31), (-1.36, 0.88, 0.48), (-1.57, 1.13, 0.57), (-1.78, 1.11, 0.6)]]
    col = loft('collar', crings, M['collar']); attach(col, body); outline(col, 0.018)
    # white V-front over the collar and a stripe
    vf = mesh_from('vfront', [(-0.36, -0.55, -1.22), (0.36, -0.55, -1.22), (0.0, -0.64, -1.86)], [(0, 2, 1)], M['shirt'])
    vfb = mesh_from('vneck', [(-0.2, -0.56, -1.2), (0.2, -0.56, -1.2), (0.0, -0.6, -1.45)], [(0, 2, 1)], M['skin'])
    for o in (vf, vfb): attach(o, body)
    st = loft('stripe', [ring(0, 0.05, z, rx * 0.86, ry, 14, 2.6) for z, rx, ry in [(-1.72, 1.125, 0.6), (-1.66, 1.13, 0.6)]], flat_mat('stripe', '#FFFFFF'), cap_top=False, cap_bottom=False); attach(st, body)
    bow_c = Vector((0, -0.7, -1.86))
    for side in (-1, 1):
        lp = mesh_from(f'bowl{side}', [bow_c, bow_c + Vector((0.42 * side, -0.02, 0.17)), bow_c + Vector((0.4 * side, -0.02, -0.16))], [(0, 1, 2)], M['bow'])
        tl_ = mesh_from(f'bowt{side}', [bow_c + Vector((0.03 * side, 0, -0.04)), bow_c + Vector((0.22 * side, -0.02, -0.5)), bow_c + Vector((0.08 * side, -0.02, -0.52))], [(0, 1, 2)], M['bow'])
        for o in (lp, tl_):
            sol = o.modifiers.new('s', 'SOLIDIFY'); sol.thickness = 0.04
            attach(o, body)
    knot = ico('knot', 0.09, M['bow'], loc=tuple(bow_c + Vector((0, -0.03, 0))), scale=(1.1, 0.7, 1.0)); attach(knot, body); outline(knot, 0.012)
    for side in (-1, 1):
        arm = loft(f'arm{side}', [ring(0, 0, z, r, r, 10) for z, r in [(0, 0.34), (-0.6, 0.33), (-1.6, 0.3), (-2.4, 0.3)]], M['shirt'])
        arm.location = (0.86 * side, 0.12, -1.55); arm.rotation_euler = (0, -0.16 * side, 0); attach(arm, body); outline(arm, 0.02)

    # --- camera (orthographic, framed so the top of the ahoge and the elbows fit)
    cd = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cd); bpy.context.collection.objects.link(cam)
    cd.type = 'ORTHO'; cd.ortho_scale = 5.2; cd.sensor_fit = 'VERTICAL'; cam.location = (0.05, -20, -0.85); cam.rotation_euler = (math.pi / 2, 0, 0)
    cd.clip_start = 1; cd.clip_end = 60; bpy.context.scene.camera = cam
    S['cam'] = cam
    return S

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

# expression presets: brow (raise), tilt (brow inner up +), eye (scale), pupil (scale), gx/gz (gaze), mouth (base open), wide (mouth width),
# happy (closed-arc eyes), blush, sweat, lean (body roll), nod (head pitch), turn (head yaw extra)
EXPR = {
    'talk':  dict(brow=0.0, tilt=0.0, eye=1.0, pupil=1.0, gx=0.0, gz=0.0, mouth=0.0, wide=1.0, happy=0.0, blush=0.75, sweat=0.0, lean=0.0, nod=0.0, turn=0.0),
    'shock': dict(brow=0.07, tilt=0.12, eye=1.12, pupil=0.62, gx=0.035, gz=0.02, mouth=0.38, wide=0.72, happy=0.0, blush=0.35, sweat=1.0, lean=-0.05, nod=-0.06, turn=0.12),
    'happy': dict(brow=0.03, tilt=0.0, eye=1.0, pupil=1.0, gx=0.0, gz=0.0, mouth=0.25, wide=1.15, happy=1.0, blush=1.0, sweat=0.0, lean=0.06, nod=0.04, turn=0.0),
    'think': dict(brow=0.04, tilt=-0.1, eye=0.96, pupil=1.0, gx=-0.03, gz=0.04, mouth=0.0, wide=0.7, happy=0.0, blush=0.6, sweat=0.0, lean=0.08, nod=0.03, turn=-0.1),
    'look':  dict(brow=0.03, tilt=0.05, eye=1.05, pupil=0.85, gx=0.045, gz=0.03, mouth=0.1, wide=0.8, happy=0.0, blush=0.6, sweat=0.0, lean=-0.03, nod=-0.04, turn=0.18),
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
def update(S, f, ENV):
    t = f / FPS; E = expr_at(t); amp = float(ENV[min(f, len(ENV) - 1)])
    talking = amp > 0.05
    # pose: body faces ~10 deg towards frame right, breathes, sways; head nods with speech
    S['body'].rotation_euler = (0.0, E['lean'] * 0.6 + 0.025 * math.sin(2 * math.pi * t / 5.1), 0.17 + 0.03 * math.sin(2 * math.pi * t / 7.3))
    S['body'].location = (0.0, 0.0, -1.3 + 0.025 * math.sin(2 * math.pi * t / 3.6))
    nod = E['nod'] + 0.05 * amp * math.sin(2 * math.pi * t * 2.1) + 0.02 * math.sin(2 * math.pi * t / 2.9)
    S['head'].rotation_euler = (nod, E['lean'] + 0.04 * math.sin(2 * math.pi * t / 4.3 + 1.0), 0.06 + E['turn'] + 0.035 * math.sin(2 * math.pi * t / 6.1))
    # eyes
    bl = blink_at(t); hp = E['happy']
    for e in S['eyes']:
        op = max(1 - bl, 0.0) * (1 - hp)
        e['open'].scale = (E['eye'], 1, E['eye'] * max(op, 0.08))
        e['open'].hide_render = op < 0.22
        e['closed'].hide_render = not (op < 0.22 and hp < 0.5)
        e['happy'].hide_render = hp < 0.5
        e['iris'].location = (E['gx'], 0, E['gz'])
        e['pupil'].scale = (E['pupil'], 1, E['pupil'])
        side = e['side']
        e['brow'].location = e['brow0'] + Vector((0, 0, E['brow']))
        e['brow'].rotation_euler = (0, -E['tilt'] * side, e['brow'].rotation_euler.z)
    # mouth: VO loudness on top of the expression's base opening
    open_ = min(E['mouth'] * (0.6 if talking else 1.0) + amp * 0.95, 1.1)
    wob = 0.85 + 0.15 * math.sin(2 * math.pi * t * 5.3)   # cheap vowel-width variation
    S['mouth_open'].scale = (E['wide'] * (0.75 + 0.35 * amp) * wob, 1, max(open_, 0.05))
    S['mouth_open'].hide_render = open_ < 0.12
    S['mouth_closed'].hide_render = open_ >= 0.12
    for b in S['blush']: b.scale = (1, 1, max(E['blush'], 0.01)); b.hide_render = E['blush'] < 0.05
    S['sweat'].hide_render = E['sweat'] < 0.5
    S['sweat'].scale = (1.5, 1, 1.5 * (1 + 0.05 * math.sin(t * 9)))

def main():
    global KEYS
    S = build(); KEYS = expr_keys(); ENV = vo_envelope()
    setup_toon_render(RES_X, RES_Y, ARGS["samples"], FPS, transparent=True)
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

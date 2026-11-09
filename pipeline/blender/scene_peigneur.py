"""Procedural low-poly anime scene: the Lake Peigneur disaster (Louisiana, 20 Nov 1980).

Run headless:
  blender -b -noaudio -P pipeline/blender/scene_peigneur.py -- --shot W --start 0 --end 300 \
      --out videos/006-lake-peigneur/build/frames/W [--res 720] [--samples 6] [--fps 30] [--preview]

Look: toon.py (flat cel bands, inverted-hull outlines, emission only, anime sky gradient). No sims:
  water   = polar grid (log-spaced rings) recomputed per frame: free-vortex funnel z = -D a^2/(r^2+a^2),
            small waves, per-face colours (depth tint + foam spiral arms wound by the real differential
            rotation omega(r) = GAMMA/(r^2+a^2), i.e. v ~ 1/r outside the core)
  floats  = rig / barges / tug / buoys advected by the same omega(r), drifting inward, tilted to the funnel
            surface, sinking at the core (numerically integrated from t=0 each frame, so frames are standalone)
Scale: 1 unit ~ 25 m horizontally; the rig and barges are drawn ~3x oversize so they read on a phone.
Shots (frames in script.json "shots"):
  C  calm establishing: lake, rig in the middle, moored barges, Jefferson Island house, canal; slow push-in
  W  the whirlpool at its peak, aerial 3/4: the rig tilts and goes down at ~5 s, barges spiral in afterwards
  M  cutaway diorama (not to scale): lake slab, strata, salt dome, mine rooms with miners; the camera follows
     the drill down; the bit breaks the roof on the spoken word "punched" (read from build/timeline.json),
     then the lake pours in, the hole widens, the surface dimples into a whirlpool and the room floods
  F  the reversed canal pours over a cliff into the drained lakebed (own set: strata cliff, streak-shaded
     free-fall curtain, toon foam, spray, plunge pool, stranded barges); not to scale
  V  top-down orthographic on the vortex for the physics beat: two buoys at r=9 and r=4.5 (inner one ~2x the
     speed: v = GAMMA r/(r^2+a^2)), debris rings. Vortex centre lands at pixel (540, 700) of the 1080x1920
     frame, 48 px per unit (beats.js draws the rings from these numbers).
"""
import bpy, bmesh, math, random, sys, os, json, time
import numpy as np
from mathutils import Vector, Matrix, Euler
from mathutils import noise as mnoise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from toon import *

def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    a = {"shot": "W", "start": 0, "end": 1, "out": "/tmp/frames", "res": 720, "samples": 6, "preview": False, "fps": 30}
    i = 0
    while i < len(argv):
        k = argv[i].lstrip("-")
        if k == "preview": a["preview"] = True; i += 1; continue
        v = argv[i + 1]; i += 2
        a[k] = type(a[k])(v) if k in a and not isinstance(a[k], bool) else v
    return a

ARGS = parse_args(); FPS = ARGS["fps"]; SHOT = ARGS["shot"].upper()
R_LAKE = 38.0          # mean shoreline radius
A_CORE = 2.5           # vortex core radius
GAMMA = 38.0           # v(r) = GAMMA r / (r^2 + a^2): ~3 units/s at r=12, ~5.7 at r=6
BED = 16.0             # lakebed depth (only seen drained, in F)

def smoothstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0) if e1 != e0 else 0.0)); return t * t * (3 - 2 * t)
def lerp(a, b, t): return a + (b - a) * t
def shore_r(th): return R_LAKE + 2.6 * math.sin(3 * th + 1.0) + 1.6 * math.sin(5 * th + 0.3) + 0.8 * math.sin(9 * th)
def omega(r): return GAMMA / (r * r + A_CORE * A_CORE)

# per-shot vortex strength: depth D of the funnel and whether it spins
VORTEX = {"C": 0.0, "W": 9.0, "V": 7.0, "F": 4.0, "M": 0.0}[SHOT]

def timeline_event():
    """M: seconds into the shot at which the bit breaks through (on the spoken word 'punched')."""
    try:
        tl = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(ARGS["out"]))), "timeline.json")))
        b = next(b for b in tl["beats"] if b["id"] == "mine")
        for l in b["lines"]:
            for w in l["words"]:
                if w["word"].lower().strip(".,") == "punched": return w["start"] - b["start"] + 0.15
    except Exception as e:
        print("timeline not found, default breach time", e)
    return 5.0

# ------------------------------------------------------------------ materials
def mats():
    M = {}
    M['grass'] = attr_mat('terrain', 'Col', shade=0.72, hi=1.05, steps=(0.5, 0.9))
    M['water'] = attr_mat('water', 'Col', shade=0.78, hi=1.10, steps=(0.46, 0.93))
    M['trunk'] = toon_mat('trunk', '#7A4E35', shade=0.65, hi=None)
    M['leaf1'] = toon_mat('leaf1', '#3FA34D', shade=(0.55, 0.7, 0.62), hi=1.12, rim=0.25, rim_col='#D8FF9A')
    M['leaf2'] = toon_mat('leaf2', '#2E8545', shade=(0.55, 0.7, 0.62), hi=1.12, rim=0.25, rim_col='#D8FF9A')
    M['leaf3'] = toon_mat('leaf3', '#6DBE45', shade=(0.55, 0.7, 0.62), hi=1.10)
    M['moss'] = toon_mat('moss', '#9DB89A', shade=0.7, hi=None)
    M['white'] = toon_mat('whitepaint', '#F4F1EA', shade=(0.74, 0.76, 0.9), hi=None)
    M['roof'] = toon_mat('roof', '#4B5568', shade=0.7, hi=1.12)
    M['red'] = toon_mat('rigred', '#E2402F', shade=0.68, hi=1.12)
    M['rigwhite'] = toon_mat('rigwhite', '#F2F2F2', shade=(0.7, 0.72, 0.86), hi=None)
    M['steel'] = toon_mat('steel', '#596273', shade=0.7, hi=1.2)
    M['deck'] = toon_mat('deck', '#3E4250', shade=0.75, hi=1.1)
    M['rust'] = toon_mat('rust', '#B4502F', shade=0.66, hi=1.1)
    M['rust2'] = toon_mat('rust2', '#8E3B2A', shade=0.66, hi=1.1)
    M['yellow'] = toon_mat('yellow', '#FFC62E', shade=0.7, hi=1.1)
    M['tugred'] = toon_mat('tugred', '#D23A3A', shade=0.68, hi=1.1)
    M['black'] = toon_mat('blackish', '#2A2A33', shade=0.8, hi=1.3)
    M['cloud'] = toon_mat('cloud', '#FFFFFF', shade=(0.80, 0.86, 0.98), hi=None, steps=(0.42, 0.9))
    M['abyss'] = flat_mat('abyss', '#0B1B3D')
    M['foam'] = toon_mat('foam', '#EAF8FF', shade=(0.78, 0.86, 0.96), hi=None)
    M['mist'] = flat_mat('mist', '#FFFFFF', alpha=0.45)
    M['buoyY'] = toon_mat('buoyY', '#FFD21F', shade=0.7, hi=1.15, rim=0.6)
    M['buoyO'] = toon_mat('buoyO', '#FF5A36', shade=0.7, hi=1.15, rim=0.6)
    M['debris'] = toon_mat('debris', '#9B7A55', shade=0.7, hi=None)
    M['wf'] = attr_mat('waterfall', 'Col', shade=0.85, hi=None, steps=(0.3, 0.9))
    return M

# ------------------------------------------------------------------ world pieces
def terrain(M):
    """Square grid, flat shaded, per-face colour mosaic. Lake basin inside the shoreline, canal to the east,
    Jefferson Island hill on the north-west shore."""
    n = 110; size = 220.0; step = size / n
    rng = np.random.default_rng(4)
    def h(x, y):
        r = math.hypot(x, y); th = math.atan2(y, x); R = shore_r(th); rr = r / R
        if rr < 1.0:
            z = -BED * smoothstep(1.0, 0.82, rr) - 0.4 * (1 - rr)   # bed: slope near the shore, flat floor
            z -= 3.0 * math.exp(-(r / 6.0) ** 2)                     # the crater
        else:
            z = 0.55 + 2.2 * smoothstep(1.0, 1.6, rr) * (0.6 + 0.4 * mnoise.noise(Vector((x * 0.03, y * 0.03, 0.5))))
            z += 0.5 * mnoise.noise(Vector((x * 0.08, y * 0.08, 2.0)))
        # Jefferson Island: a salt-dome hill on the NW shore
        jx, jy = -27.0, 25.0; d = math.hypot(x - jx, y - jy)
        z = max(z, 4.2 * math.exp(-(d / 10.0) ** 2) + (0.55 if rr >= 0.97 else -BED) * 0) if d < 16 else z
        # canal: east, along +x, a straight cut
        if x > R - 2 and abs(y) < 3.2 and abs(th) < 0.4:
            z = min(z, -1.6 * smoothstep(3.2, 2.0, abs(y)) + 0.6 * smoothstep(2.0, 3.2, abs(y)))
        return z
    verts = []; faces = []
    for j in range(n + 1):
        for i in range(n + 1):
            x = -size / 2 + i * step; y = -size / 2 + j * step + 10.0
            verts.append((x, y, h(x, y)))
    for j in range(n):
        for i in range(n):
            a = j * (n + 1) + i; faces.append((a, a + 1, a + n + 2, a + n + 1))
    o = mesh_from('terrain', verts, faces, M['grass'])
    me = o.data; ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'CORNER')
    cols = []
    greens = [srgb('#79C35A'), srgb('#6AB650'), srgb('#86CC62'), srgb('#5FA84A')]
    mud = [srgb('#8C6A4C'), srgb('#7D5E43'), srgb('#9A7656'), srgb('#6E5139')]
    sand = srgb('#E6D3A0'); wet = srgb('#5A4634')
    for p in me.polygons:
        c = p.center; r = math.hypot(c.x, c.y); th = math.atan2(c.y, c.x); rr = r / shore_r(th)
        k = rng.integers(0, 4)
        if c.z < -0.3: col = mud[k] if rng.random() > 0.12 else wet
        elif rr < 1.06 and c.z < 1.2: col = sand
        else: col = greens[k]
        for _ in p.loop_indices: cols.extend(col)
    ca.data.foreach_set('color', cols)
    # distant ground plane so the horizon never shows the grid edge
    # (an annulus outside the terrain, slightly below its rim: it must never cover the lake or the drained bed)
    n = 48; ri, ro = 98.0, 1500.0; fv = []
    for k in range(n):
        a = 2 * math.pi * k / n; fv += [(ri * math.cos(a), 10 + ri * math.sin(a), 0.2), (ro * math.cos(a), 10 + ro * math.sin(a), 0.2)]
    mesh_from('far', fv, [(2 * k, 2 * ((k + 1) % n), 2 * ((k + 1) % n) + 1, 2 * k + 1) for k in range(n)], toon_mat('far', '#86B874', shade=1.0, hi=None))
    return o

def tree(M, x, y, z, s=1.0, rng=None, outline_w=0.12, moss=False):
    rng = rng or random.Random(1)
    root = bpy.data.objects.new('tree', None); bpy.context.collection.objects.link(root); root.location = (x, y, z)
    tr = cyl('trunk', 0.35 * s, 0.25 * s, 0.0, 2.2 * s, M['trunk'], n=5); tr.parent = root
    leaves = [M['leaf1'], M['leaf2'], M['leaf3']]
    for k in range(rng.randint(2, 3)):
        r = (1.2 + rng.random() * 0.7) * s
        c = ico('canopy', r, leaves[rng.randint(0, 2)], loc=(rng.uniform(-0.6, 0.6) * s, rng.uniform(-0.6, 0.6) * s, (2.4 + k * 0.9 + rng.random() * 0.5) * s), sub=1, scale=(1.0, 1.0, 0.8))
        c.parent = root; c.rotation_euler = (rng.random(), rng.random(), rng.random()); outline(c, outline_w)
    if moss:   # live oak with Spanish moss: a few hanging grey-green spikes
        for k in range(4):
            a = rng.random() * 6.28; px, py = math.cos(a) * 1.3 * s, math.sin(a) * 1.3 * s
            b = blade('moss', Vector((px, py, 2.6 * s)), Vector((px * 1.05, py * 1.05, 1.9 * s)), Vector((px * 1.1, py * 1.1, 1.3 * s)), 0.35 * s, 0.1, M['moss'], segs=2)
            b.parent = root
    return root

def house(M, x, y, z, rot=0.0):
    root = bpy.data.objects.new('house', None); bpy.context.collection.objects.link(root); root.location = (x, y, z); root.rotation_euler = (0, 0, rot)
    b = box('house_body', (6.0, 3.6, 2.6), M['white'], loc=(0, 0, 1.3)); b.parent = root; outline(b, 0.1)
    rf = mesh_from('roof', [(-3.4, -2.2, 2.6), (3.4, -2.2, 2.6), (3.4, 2.2, 2.6), (-3.4, 2.2, 2.6), (-2.6, 0, 4.2), (2.6, 0, 4.2)],
                   [(0, 1, 5, 4), (2, 3, 4, 5), (1, 2, 5), (3, 0, 4), (0, 3, 2, 1)], M['roof']); rf.parent = root; outline(rf, 0.1)
    for k in range(6):   # porch columns
        c = cyl('col', 0.14, 0.14, 0.0, 2.4, M['white'], n=5, loc=(-2.6 + k * 1.04, -2.2, 0.0)); c.parent = root
    pr = box('porch_roof', (6.4, 1.2, 0.2), M['white'], loc=(0, -2.3, 2.45)); pr.parent = root; outline(pr, 0.06)
    for k in range(4):
        w = box('win', (0.6, 0.05, 0.9), M['deck'], loc=(-2.1 + k * 1.4, -1.82, 1.4)); w.parent = root
    return root

def rig(M):
    """Drilling rig on a barge-type platform: deck, red/white lattice derrick, crown, drawworks shed, crane."""
    root = bpy.data.objects.new('rig', None); bpy.context.collection.objects.link(root)
    hull = box('rig_hull', (6.0, 5.0, 1.1), M['rust2'], loc=(0, 0, -0.1)); hull.parent = root; outline(hull, 0.09)
    deck = box('rig_deck', (5.6, 4.6, 0.25), M['deck'], loc=(0, 0, 0.55)); deck.parent = root
    shed = box('rig_shed', (2.0, 1.6, 1.2), M['rigwhite'], loc=(-1.7, 1.2, 1.25)); shed.parent = root; outline(shed, 0.07)
    tank = cyl('rig_tank', 0.5, 0.5, 0.0, 1.5, M['yellow'], n=8, loc=(2.0, 1.4, 0.65)); tank.parent = root; outline(tank, 0.06)
    Hd = 9.0; b0, b1 = 1.7, 0.45
    def leg_xy(sx, sy, z): k = z / Hd; w = lerp(b0, b1, k); return Vector((sx * w, sy * w, z + 0.65))
    nseg = 6
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        for s in range(nseg):
            p0 = leg_xy(sx, sy, Hd * s / nseg); p1 = leg_xy(sx, sy, Hd * (s + 1) / nseg)
            o = blade('leg', p0, (p0 + p1) / 2, p1, 0.2, 0.2, M['red'] if s % 2 == 0 else M['rigwhite'], segs=1, tip=1.0); o.parent = root; outline(o, 0.05)
    for s in range(nseg):   # X braces on each face
        z0, z1 = Hd * s / nseg, Hd * (s + 1) / nseg
        for (ax, ay), (bx, by) in (((1, 1), (1, -1)), ((1, -1), (-1, -1)), ((-1, -1), (-1, 1)), ((-1, 1), (1, 1))):
            for p0, p1 in ((leg_xy(ax, ay, z0), leg_xy(bx, by, z1)), (leg_xy(bx, by, z0), leg_xy(ax, ay, z1))):
                o = blade('brace', p0, (p0 + p1) / 2, p1, 0.08, 0.08, M['steel'], segs=1, tip=1.0); o.parent = root
    crown = box('crown', (1.3, 1.3, 0.5), M['red'], loc=(0, 0, Hd + 0.9)); crown.parent = root; outline(crown, 0.06)
    flag = box('beacon', (0.25, 0.25, 0.25), flat_mat('beacon', '#FFEE88'), loc=(0, 0, Hd + 1.3)); flag.parent = root
    pipe = cyl('rig_pipe', 0.1, 0.1, -3.0, Hd, M['steel'], n=6); pipe.parent = root
    boom = blade('crane', Vector((2.2, -1.5, 0.8)), Vector((3.2, -2.6, 3.5)), Vector((4.0, -3.4, 5.2)), 0.22, 0.22, M['yellow'], segs=2, tip=1.0); boom.parent = root; outline(boom, 0.05)
    return root

def barge(M, name, kind=0, rng=None):
    rng = rng or random.Random(2)
    root = bpy.data.objects.new(name, None); bpy.context.collection.objects.link(root)
    L, Wd = 5.6, 1.9
    hull = mesh_from(name + '_hull', [(-L / 2, -Wd / 2, -0.3), (L / 2, -Wd / 2, -0.3), (L / 2, Wd / 2, -0.3), (-L / 2, Wd / 2, -0.3),
                                      (-L / 2 - 0.4, -Wd / 2, 0.45), (L / 2 + 0.4, -Wd / 2, 0.45), (L / 2 + 0.4, Wd / 2, 0.45), (-L / 2 - 0.4, Wd / 2, 0.45)],
                     [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)], M['rust'] if kind % 2 == 0 else M['rust2'])
    hull.parent = root; outline(hull, 0.09)
    for k in range(rng.randint(1, 3)):
        c = box(name + '_cargo', (rng.uniform(0.8, 1.6), rng.uniform(0.8, 1.4), rng.uniform(0.4, 0.9)), [M['steel'], M['yellow'], M['deck']][rng.randint(0, 2)],
                loc=(rng.uniform(-1.8, 1.8), rng.uniform(-0.3, 0.3), 0.8)); c.parent = root; outline(c, 0.05)
    return root

def tug(M):
    root = bpy.data.objects.new('tug', None); bpy.context.collection.objects.link(root)
    hull = mesh_from('tug_hull', [(-1.6, -0.9, -0.3), (1.2, -0.9, -0.3), (2.2, 0, -0.1), (1.2, 0.9, -0.3), (-1.6, 0.9, -0.3),
                                  (-1.7, -1.0, 0.6), (1.3, -1.0, 0.6), (2.5, 0, 0.7), (1.3, 1.0, 0.6), (-1.7, 1.0, 0.6)],
                     [(0, 4, 3, 2, 1), (5, 6, 7, 8, 9), (0, 1, 6, 5), (1, 2, 7, 6), (2, 3, 8, 7), (3, 4, 9, 8), (4, 0, 5, 9)], M['tugred'])
    hull.parent = root; outline(hull, 0.08)
    cab = box('tug_cab', (1.4, 1.3, 1.1), M['rigwhite'], loc=(-0.2, 0, 1.15)); cab.parent = root; outline(cab, 0.06)
    top = box('tug_top', (0.9, 1.0, 0.6), M['rigwhite'], loc=(-0.2, 0, 2.0)); top.parent = root; outline(top, 0.05)
    st = cyl('tug_stack', 0.22, 0.2, 0.0, 1.0, M['black'], n=6, loc=(-1.1, 0, 1.2)); st.parent = root; outline(st, 0.04)
    return root

def clouds(M, rng):
    for k in range(9):
        x = rng.uniform(-140, 140); y = rng.uniform(120, 260); z = rng.uniform(28, 55); s = rng.uniform(5, 10)
        for j in range(3):
            c = ico('cloud', s * rng.uniform(0.6, 1.0), M['cloud'], loc=(x + (j - 1) * s * 1.1, y + rng.uniform(-2, 2), z + rng.uniform(-1, 1.5)), sub=1, scale=(1.4, 1.0, 0.6))

# ------------------------------------------------------------------ water (vortex)
class Water:
    def __init__(self, M, R=48.0, n_ang=80, n_rad=40, r0=0.45, name='water'):
        rs = r0 * (R / r0) ** (np.arange(n_rad + 1) / n_rad)
        th = np.linspace(0, 2 * np.pi, n_ang, endpoint=False)
        self.r = np.repeat(rs, n_ang); self.th = np.tile(th, n_rad + 1)
        verts = np.stack([self.r * np.cos(self.th), self.r * np.sin(self.th), np.zeros_like(self.r)], 1)
        faces = []
        for j in range(n_rad):
            for i in range(n_ang):
                a = j * n_ang + i; b = j * n_ang + (i + 1) % n_ang; faces.append((a, b, b + n_ang, a + n_ang))
        self.obj = mesh_from(name, verts.tolist(), faces, M['water'])
        me = self.obj.data; self.col = me.color_attributes.new('Col', 'FLOAT_COLOR', 'CORNER')
        self.nf = len(faces); fa = np.array(faces)
        self.fr = (self.r[fa[:, 0]] + self.r[fa[:, 2]]) / 2
        self.fth = np.arctan2(np.sin(self.th[fa[:, 0]]) + np.sin(self.th[fa[:, 1]]), np.cos(self.th[fa[:, 0]]) + np.cos(self.th[fa[:, 1]]))
        self.loop_face = np.repeat(np.arange(self.nf), 4)
        jit = np.random.default_rng(9).random(self.nf); self.jit = jit
        self.abyss = cyl('abyss', 0.9, 0.9, -0.2, 0.0, M['abyss'], n=10)
        self.R = R
    def z(self, r, t, D, level=0.0, waves=1.0):
        return level - D * A_CORE ** 2 / (r * r + A_CORE ** 2) + waves * 0.12 * np.sin(0.55 * r - 1.7 * t) * np.cos(3 * self.th - 0.3 * t) if isinstance(r, np.ndarray) else level - D * A_CORE ** 2 / (r * r + A_CORE ** 2)
    def update(self, t, D, level=0.0, spin=True, calm_ripple=1.0):
        r, th = self.r, self.th
        zz = level - D * A_CORE ** 2 / (r * r + A_CORE ** 2)
        zz = zz + calm_ripple * 0.10 * np.sin(0.5 * r - 1.6 * t + 2 * np.sin(2 * th)) + 0.06 * np.sin(1.3 * r * np.cos(th - 0.7) + 2.1 * t)
        co = np.stack([r * np.cos(th), r * np.sin(th), zz], 1).astype(np.float32)
        self.obj.data.vertices.foreach_set('co', co.ravel()); self.obj.data.update()
        self.abyss.location = (0, 0, level - D - 0.15); self.abyss.hide_render = D < 0.5
        # face colours
        fr, fth = self.fr, self.fth
        depth = A_CORE ** 2 / (fr * fr + A_CORE ** 2) * (D / 9.0)
        base = np.array(srgb('#3AA3EC')[:3]); deep = np.array(srgb('#1B4FA6')[:3]); lite = np.array(srgb('#7FD0FF')[:3]); foam = np.array(srgb('#F2FBFF')[:3])
        c = base[None, :] * (1 - np.clip(depth * 1.6, 0, 1))[:, None] + deep[None, :] * np.clip(depth * 1.6, 0, 1)[:, None]
        c = c * (0.94 + 0.08 * self.jit[:, None])
        if spin and D > 0:
            ph = 5 * (fth - omega(fr) * t) + 2.4 * np.log(fr)
            s = np.sin(ph) + 0.25 * np.sin(3.1 * fr + 2 * fth + self.jit * 3)
            reach = np.clip(1.4 - fr / 26.0, 0, 1)
            m1 = (s > 0.55) & (self.jit < 0.85 + 0.15 * reach); m2 = (s > 0.95 - 0.3 * reach) & (fr < 30)
            c[m1] = c[m1] * 0.4 + lite * 0.6; c[m2] = foam
        else:   # calm: sparse sparkles
            s = np.sin(0.7 * fr - 0.9 * t + 4 * self.jit) + np.sin(3 * fth + 0.3 * t)
            m = s > 1.75; c[m] = c[m] * 0.4 + lite * 0.6
        cols = np.concatenate([c, np.ones((self.nf, 1))], 1)[self.loop_face].astype(np.float32)
        self.col.data.foreach_set('color', cols.ravel())
    def surface(self, r, D, level=0.0):
        z = level - D * A_CORE ** 2 / (r * r + A_CORE ** 2); dz = D * A_CORE ** 2 * 2 * r / (r * r + A_CORE ** 2) ** 2
        return z, dz

def hide(obj, h):
    """hide_render on a group root does not hide its children: apply to the whole hierarchy."""
    for o in [obj] + list(obj.children_recursive): o.hide_render = h

def place_float(obj, r, th, D, extra_tilt=0.0, sink=0.0, heading=0.0, level=0.0, bob=0.0):
    z, dz = Water.surface(None, r, D, level)
    er = Vector((math.cos(th), math.sin(th), 0)); et = Vector((-math.sin(th), math.cos(th), 0))
    n = (Vector((0, 0, 1)) - er * dz).normalized()
    n = (n * math.cos(extra_tilt) - er * math.sin(extra_tilt)).normalized()   # extra roll towards the centre
    x = (et * math.cos(heading) + er * math.sin(heading)); x = (x - n * x.dot(n)).normalized(); y = n.cross(x)
    m = Matrix((x, y, n)).transposed()
    obj.matrix_world = Matrix.Translation(Vector((r * math.cos(th), r * math.sin(th), z - sink + bob))) @ m.to_4x4()

def advect(r0, th0, t, r_of_t, dt=1 / 60):
    """theta(t) for a float whose radius follows r_of_t, advected by omega(r)."""
    th = th0; s = 0.0; n = int(t / dt)
    for i in range(n): th += omega(max(r_of_t(s), 0.3)) * dt; s += dt
    th += omega(max(r_of_t(s), 0.3)) * (t - n * dt)
    return th

# ------------------------------------------------------------------ shots C / W / V / F (shared world)
def build_lake():
    M = mats(); S = {"M": M}; rng = random.Random(6)
    sky_world('#2F6FE0', '#CDEBFF')
    terrain(M)
    S['water'] = Water(M)
    # trees around the shore + live oaks and the house on Jefferson Island
    for k in range(150):
        th = rng.uniform(-math.pi, math.pi); R = shore_r(th) + rng.uniform(4, 30)
        if abs(th) < 0.12 and R < 110: continue   # keep the canal clear
        x, y = R * math.cos(th), R * math.sin(th) + 0.0
        if math.hypot(x, y - 10) > 105: continue
        tree(M, x, y, 0.4, rng.uniform(0.9, 1.6), rng)
    for k in range(14):
        a = rng.uniform(0, 6.28); d = rng.uniform(4, 11); x, y = -27 + d * math.cos(a), 25 + d * math.sin(a)
        tree(M, x, y, 4.2 * math.exp(-(d / 10.0) ** 2) - 0.2, rng.uniform(1.1, 1.6), rng, moss=True)
    house(M, -27.5, 24.0, 4.1, rot=-0.75)
    clouds(M, rng)
    S['rig'] = rig(M)
    S['barges'] = [barge(M, f'barge{k}', k, rng) for k in range(11)]
    S['tug'] = tug(M)
    return S

def cam_new(lens=35):
    cd = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cd); bpy.context.collection.objects.link(cam)
    cd.lens = lens; cd.sensor_fit = 'HORIZONTAL'; cd.sensor_width = 36; cd.clip_start = 0.5; cd.clip_end = 2000
    bpy.context.scene.camera = cam; return cam
def look(cam, loc, tgt, roll=0.0):
    cam.location = loc; d = Vector(tgt) - Vector(loc); cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler(); cam.rotation_euler.rotate_axis('Z', roll)

# barge schedule for W: (r0, th0, t_start_drift, t_gone)
BARGE_W = [(13, 0.4, 2.0, 6.3), (16, 2.2, 2.5, 7.4), (19, 4.0, 3.0, 8.4), (14, 5.4, 3.2, 9.2), (22, 1.2, 3.5, 10.4), (17, 3.3, 4.0, 11.5),
           (25, 5.0, 4.0, 12.5), (20, 0.0, 5.0, 13.5), (27, 2.7, 5.0, 15.0), (24, 4.5, 6.0, 16.0), (29, 1.7, 6.0, 17.0)]
TUG_W = (11, 3.6, 1.0, 7.9)

def update_lake(S, t):
    W = S['water']; D = VORTEX
    if SHOT == "C":
        W.update(t, 0.0, spin=False)
        S['rig'].matrix_world = Matrix.Translation((0, 0, 0.15 + 0.05 * math.sin(t * 1.3)))
        moor = [(7, -6, 0.2), (8.5, -3.6, 0.15), (-7, -5, -0.3), (-6.5, 6, 0.4), (5, 7.5, 1.2)]
        for k, b in enumerate(S['barges']):
            if k < len(moor):
                x, y, a = moor[k]; b.matrix_world = Matrix.Translation((x, y, 0.1 + 0.04 * math.sin(t * 1.1 + k))) @ Matrix.Rotation(a, 4, 'Z'); b.hide_set(False)
            else:   # the rest moored along the canal mouth
                x = shore_r(0) - 6 - (k - 5) * 0.0; y = -8 + (k - 5) * 2.4
                b.matrix_world = Matrix.Translation((30 - (k - 5) * 0.4, -14 + (k - 5) * 2.5, 0.1)) @ Matrix.Rotation(1.57, 4, 'Z')
        S['tug'].matrix_world = Matrix.Translation((10.5, -1.0, 0.1)) @ Matrix.Rotation(2.8, 4, 'Z')
        return
    W.update(t, D, spin=True)
    if SHOT == "V":
        hide(S['rig'], True); hide(S['tug'], True)
        for b in S['barges']: hide(b, True)
        for k, (obj, r) in enumerate(S['buoys']):
            th = (0.6 if r > 6 else 2.0) + GAMMA / (r * r) * t   # ideal free vortex outside the core (v = GAMMA/r: half r, double v); beats.js mirrors this (BUOYS)
            place_float(obj, r, th, D, bob=0.08 * math.sin(t * 3 + k))
        for k, (obj, r, th0) in enumerate(S['debris']):
            place_float(obj, r, th0 + omega(r) * t, D, heading=th0 * 3)
        return
    # W: rig slides in and goes down; barges spiral in afterwards
    def r_rig(s): return 3.6 * (1 - smoothstep(0.3, 5.0, s)) + 0.6
    th = advect(3.6, -0.9, t, r_rig); rr = r_rig(t)
    sink = 8.0 * smoothstep(3.9, 6.2, t); tilt = 0.12 + 0.55 * smoothstep(0.0, 5.0, t)
    place_float(S['rig'], rr, th, D, extra_tilt=tilt, sink=sink, heading=0.3)
    hide(S['rig'], t > 6.3)
    for k, b in enumerate(S['barges']):
        r0, th0, ts, tg = BARGE_W[k]
        def r_of(s, r0=r0, ts=ts, tg=tg): return max(r0 * (1 - smoothstep(ts, tg, s)) ** 0.8, 0.0) + 0.9 * (1 - smoothstep(tg - 0.6, tg, s))
        rr = r_of(t); thb = advect(r0, th0, t, r_of)
        sink = 6.0 * smoothstep(tg - 1.3, tg + 0.2, t)
        place_float(b, rr, thb, D, extra_tilt=0.25 * smoothstep(tg - 2.5, tg, t), sink=sink, heading=0.25)
        hide(b, t > tg + 0.25)
    r0, th0, ts, tg = TUG_W
    def r_tug(s): return max(r0 * (1 - smoothstep(ts, tg, s)) ** 0.8, 0.0) + 0.9 * (1 - smoothstep(tg - 0.6, tg, s))
    place_float(S['tug'], r_tug(t), advect(r0, th0, t, r_tug), D, extra_tilt=0.3 * smoothstep(tg - 2.5, tg, t), sink=6.0 * smoothstep(tg - 1.3, tg + 0.2, t), heading=-0.2)
    hide(S['tug'], t > tg + 0.25)

def build_v_extras(S):
    M = S['M']; S['buoys'] = []
    for r, m in ((9.0, M['buoyY']), (4.5, M['buoyO'])):
        root = bpy.data.objects.new('buoy', None); bpy.context.collection.objects.link(root)
        b = ico('buoy_b', 0.9, m, loc=(0, 0, 0.3), sub=1, scale=(1, 1, 0.8)); b.parent = root; outline(b, 0.1)
        c = cyl('buoy_m', 0.12, 0.12, 0.6, 2.0, M['black'], n=5); c.parent = root
        S['buoys'].append((root, r))
    rng = random.Random(3); S['debris'] = []
    for k in range(26):
        r = [4.5, 8.5, 16, 20][k % 4] + rng.uniform(-0.6, 0.6); th0 = rng.uniform(0, 6.28)
        o = box('debris', (rng.uniform(0.8, 1.4), 0.35, 0.25), M['debris']); outline(o, 0.06)
        S['debris'].append((o, r, th0))

# ------------------------------------------------------------------ F: the reversed canal pours into the drained lake
# Its own set piece (the first version reused the lake terrain: the falls were small, half hidden by the shore slope,
# per-face checker stripes, grey "mist" blobs that read as rocks). Here: a curved low-poly cliff with strata, the canal
# cut through its rim, a free-fall water curtain with a scrolling streak shader, white toon foam churning at the foot,
# spray, a plunge pool, and barges stranded on the mud for scale. Not to scale (real drop ~164 ft / 50 m).
FALL_H = 17.0; CLIFF_R = 30.0; FALL_A = math.radians(72)   # cliff height, cliff radius, angle of the falls on the arc

def streak_mat(name, base, lite, foam, scale=(26.0, 2.2, 1.0), speed=1.0):
    """Water curtain: emission from a ColorRamp over noise stretched along the fall (UV v), scrolled by a per-frame
    'time' value -> long vertical streaks moving down. Returns (material, time node)."""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial'); uv = nt.nodes.new('ShaderNodeUVMap'); uv.uv_map = 'UVMap'
    tval = nt.nodes.new('ShaderNodeValue'); tval.outputs[0].default_value = 0.0
    comb = nt.nodes.new('ShaderNodeCombineXYZ'); nt.links.new(tval.outputs[0], comb.inputs['Y'])
    sub = nt.nodes.new('ShaderNodeVectorMath'); sub.operation = 'SUBTRACT'; nt.links.new(uv.outputs['UV'], sub.inputs[0]); nt.links.new(comb.outputs[0], sub.inputs[1])
    mul = nt.nodes.new('ShaderNodeVectorMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = scale
    nt.links.new(sub.outputs[0], mul.inputs[0])
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 1.0; nz.inputs['Detail'].default_value = 1.0
    nt.links.new(mul.outputs[0], nz.inputs['Vector'])
    ramp = nt.nodes.new('ShaderNodeValToRGB'); ramp.color_ramp.interpolation = 'CONSTANT'; el = ramp.color_ramp.elements
    el[0].position = 0.0; el[0].color = srgb(base); el[1].position = 0.5; el[1].color = srgb(lite); e = el.new(0.62); e.color = srgb(foam)
    nt.links.new(nz.outputs['Fac'], ramp.inputs['Fac'])
    # foam where the water leaves the lip and at the bottom (UV v near 1)
    sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(uv.outputs['UV'], sep.inputs[0])
    edge = nt.nodes.new('ShaderNodeMath'); edge.operation = 'GREATER_THAN'; edge.inputs[1].default_value = 0.955; nt.links.new(sep.outputs['Y'], edge.inputs[0])
    mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.inputs['B'].default_value = srgb(foam)
    nt.links.new(edge.outputs[0], mix.inputs['Factor']); nt.links.new(ramp.outputs['Color'], mix.inputs['A'])
    em = nt.nodes.new('ShaderNodeEmission'); nt.links.new(mix.outputs['Result'], em.inputs['Color']); nt.links.new(em.outputs[0], out.inputs['Surface'])
    return m, tval

def curtain(name, mat, width, push, nu=18, nv=26, back=0.0):
    """Free-fall sheet from the lip: horizontal speed constant, z = H - g tau^2 / 2 (shape only; time is in the shader).
    UV: u across, v = 0 at the lip .. 1 at the foot."""
    er = Vector((math.cos(FALL_A), math.sin(FALL_A), 0)); inward = -er; tang = Vector((-math.sin(FALL_A), math.cos(FALL_A), 0))
    lip = er * (CLIFF_R - 0.6 - back) + Vector((0, 0, FALL_H - 0.6))
    verts, uvs = [], []
    for j in range(nv + 1):
        v = j / nv; tau = v                       # normalised fall time; z drops as tau^2
        for i in range(nu + 1):
            u = i / nu; w = width * (1 + 0.35 * v) * (u - 0.5)
            bulge = 0.25 * math.sin(math.pi * u) * v
            p = lip + inward * (push * tau + bulge) + tang * w + Vector((0, 0, -(FALL_H - 0.3) * tau * tau))
            verts.append(p); uvs.append((u, v))
    faces = [(j * (nu + 1) + i, j * (nu + 1) + i + 1, (j + 1) * (nu + 1) + i + 1, (j + 1) * (nu + 1) + i) for j in range(nv) for i in range(nu)]
    o = mesh_from(name, verts, faces, mat, smooth=True); uvl = o.data.uv_layers.new(name='UVMap')
    for poly in o.data.polygons:
        for li, vi in zip(poly.loop_indices, poly.vertices): uvl.data[li].uv = uvs[vi]
    return o, lip + inward * push + Vector((0, 0, -(FALL_H - 0.3)))

def build_falls():
    M = mats(); S = {"M": M}; rng = random.Random(12)
    sky_world('#2F6FE0', '#CDEBFF')
    # mud basin (the drained lakebed): low-poly grid, mud mosaic with wet patches and puddles
    n = 60; size = 140.0; st = size / n; verts = []; faces = []
    for j in range(n + 1):
        for i in range(n + 1):
            x = -size / 2 + i * st; y = -size / 2 + j * st + 10
            z = 0.35 * mnoise.noise(Vector((x * 0.07, y * 0.07, 1.0))) + 0.6 * smoothstep(CLIFF_R - 8, CLIFF_R, math.hypot(x, y))
            verts.append((x, y, z))
    faces = [(j * (n + 1) + i, j * (n + 1) + i + 1, (j + 1) * (n + 1) + i + 1, (j + 1) * (n + 1) + i) for j in range(n) for i in range(n)]
    mud = mesh_from('mud', verts, faces, M['grass']); ca = mud.data.color_attributes.new('Col', 'FLOAT_COLOR', 'CORNER'); cols = []
    muds = [srgb('#8C6A4C'), srgb('#7D5E43'), srgb('#9A7656'), srgb('#6E5139')]; wet = srgb('#5A4634'); pud = srgb('#5FA9DA')
    for p in mud.data.polygons:
        c = p.center; k = mnoise.noise(Vector((c.x * 0.05, c.y * 0.05, 7.0)))
        col = pud if k > 0.42 else (wet if k > 0.25 else muds[rng.randint(0, 3)])
        for _ in p.loop_indices: cols.extend(col)
    ca.data.foreach_set('color', cols)
    # cliff: an arc of rock with strata bands, displaced low-poly faces; a notch where the canal comes through
    na, nh = 56, 9; a0, a1 = math.radians(5), math.radians(175); verts = []
    strata = [srgb('#9C7455'), srgb('#8A6248'), srgb('#B08860'), srgb('#7A543D'), srgb('#A47B58')]
    def notch(a): return 1.8 * math.exp(-((a - FALL_A) / math.radians(8.5)) ** 2)
    for j in range(nh + 1):
        for i in range(na + 1):
            a = a0 + (a1 - a0) * i / na; h = FALL_H * j / nh
            if j == nh: h -= notch(a)
            r = CLIFF_R + 1.1 * mnoise.noise(Vector((a * 6, h * 0.25, 3.0))) - 0.9 * (1 - h / FALL_H)
            verts.append((r * math.cos(a), r * math.sin(a), h))
    faces = [(j * (na + 1) + i + 1, j * (na + 1) + i, (j + 1) * (na + 1) + i, (j + 1) * (na + 1) + i + 1) for j in range(nh) for i in range(na)]
    cliff = mesh_from('cliff', verts, faces, M['grass']); ca = cliff.data.color_attributes.new('Col', 'FLOAT_COLOR', 'CORNER'); cols = []
    for p in cliff.data.polygons:
        band = int(p.center.z / FALL_H * 7.0) % len(strata); col = tuple(c * rng.uniform(0.92, 1.06) for c in strata[band][:3]) + (1.0,)
        for _ in p.loop_indices: cols.extend(col)
    ca.data.foreach_set('color', cols); outline(cliff, 0.12)
    # plateau on top (grass) with the canal channel running out to the rim
    pv = []; npa = 40
    for i in range(npa + 1):
        a = a0 + (a1 - a0) * i / npa; pv += [((CLIFF_R + 0.6) * math.cos(a), (CLIFF_R + 0.6) * math.sin(a), FALL_H - 0.15), (140 * math.cos(a), 140 * math.sin(a), FALL_H - 0.15)]
    plat = mesh_from('plateau', pv, [(2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1) for i in range(npa)], toon_mat('plateau', '#79C35A', shade=0.8, hi=None))
    er = Vector((math.cos(FALL_A), math.sin(FALL_A), 0)); tang = Vector((-er.y, er.x, 0))
    S['canal_mat'], S['canal_t'] = streak_mat('canalw', '#3E9FE6', '#7FD0FF', '#E8F8FF', scale=(5.0, 1.2, 1.0))
    cw = 4.8; L0, L1 = CLIFF_R - 0.6, CLIFF_R + 80; nc = 12; cv = []; cuv = []
    for j in range(nc + 1):
        r = L0 + (L1 - L0) * j / nc
        for s_ in (-1, 1): cv.append(er * r + tang * cw * s_ + Vector((0, 0, FALL_H - 0.6))); cuv.append(((s_ + 1) / 2, -(r - L0) / 20.0))
    canal = mesh_from('canal', cv, [(2 * j, 2 * j + 1, 2 * j + 3, 2 * j + 2) for j in range(nc)], S['canal_mat'])
    uvl = canal.data.uv_layers.new(name='UVMap')
    for poly in canal.data.polygons:
        for li, vi in zip(poly.loop_indices, poly.vertices): uvl.data[li].uv = cuv[vi]
    for s_ in (-1, 1):   # grassy banks along the canal
        bank = box('bank', (L1 - L0, 1.6, 1.2), toon_mat('bankg', '#6AB650', shade=0.75, hi=None), loc=tuple(er * ((L0 + L1) / 2) + tang * (cw + 0.8) * s_ + Vector((0, 0, FALL_H - 0.2))), rot=(0, 0, FALL_A))
        outline(bank, 0.08)
    for k in range(34):
        a = rng.uniform(a0 + 0.05, a1 - 0.05)
        if abs(a - FALL_A) < math.radians(12): continue
        r = rng.uniform(CLIFF_R + 2.5, CLIFF_R + 26); tree(M, r * math.cos(a), r * math.sin(a), FALL_H - 0.2, rng.uniform(1.0, 1.6), rng)
    # the falls: one free-fall sheet
    S['wf_mat'], S['wf_t'] = streak_mat('fallfront', '#4FB3F0', '#9EE0FF', '#FFFFFF', scale=(26.0, 2.2, 1.0))
    _, foot = curtain('fall', S['wf_mat'], 10.0, 4.4)
    S['foot'] = foot
    # plunge pool + foam puffs + spray + soft mist
    pool = Water(M, R=9.0, n_ang=36, n_rad=8, r0=0.6, name='pool'); pool.obj.location = (foot.x, foot.y, 0.45); pool.abyss.hide_render = True; S['pool'] = pool
    S['puffs'] = []
    for k in range(14):
        a = math.pi * (k / 13.0) + FALL_A + math.pi / 2; r = rng.uniform(2.0, 5.5)
        base = foot + Vector((math.cos(a) * r, math.sin(a) * r * 0.7, 0.5)); size = rng.uniform(0.7, 1.3)
        o = ico('puff', size, M['cloud'], loc=tuple(base), sub=1); outline(o, 0.03, col='#7FA6C8')
        S['puffs'].append((o, base, size, rng.uniform(0, 6.28)))
    S['spray'] = []
    for k in range(26):
        o = ico('spray', 0.22, M['foam'], sub=1); S['spray'].append((o, rng.uniform(0, 6.28), rng.uniform(4, 9), rng.uniform(0.5, 1.2), rng.random()))
    # stranded barges and a few boulders on the mud, for scale
    for k, (x, y, a, tilt) in enumerate([(14, 8, 0.6, 0.12), (-4, 14, 2.2, -0.08), (19, -2, 1.3, 0.18)]):
        b = barge(M, f'stranded{k}', k, rng); b.matrix_world = Matrix.Translation((x, y, 0.55)) @ Matrix.Rotation(a, 4, 'Z') @ Matrix.Rotation(tilt, 4, 'X')
    for k in range(9):
        x = rng.uniform(-14, 26); y = rng.uniform(-4, 22)
        o = ico('rock', rng.uniform(0.6, 1.6), toon_mat('rock', '#8D8577', shade=0.68, hi=1.1), loc=(x, y, 0.3), sub=1, scale=(1.3, 1.0, 0.7)); outline(o, 0.07)
    clouds(M, rng)
    S['cam'] = cam_new(30)
    S['cam'].data.shift_y = -0.3; S['cam'].data.shift_x = -0.07   # lift the falls into the upper right: captions + host live lower left
    return S

def update_falls(S, t):
    for node, speed in ((S['wf_t'], 1.15), (S['canal_t'], -0.35)): node.outputs[0].default_value = speed * t
    S['pool'].update(t, 0.6, level=0.0, spin=True)
    foot = S['foot']
    for o, base, size, ph in S['puffs']:
        k = math.sin(t * 2.6 + ph); o.scale = (size * (1 + 0.18 * k), size * (1 + 0.18 * k), size * (1 + 0.25 * math.sin(t * 3.1 + ph)))
        o.location = base + Vector((0, 0, 0.3 * k)); o.rotation_euler = (t * 0.7 + ph, ph, t * 0.4)
    for o, a, sp, per, ph in S['spray']:
        tau = ((t / per + ph) % 1.0) * per; vx, vz = math.cos(a) * sp * 0.5, sp
        z = 0.6 + vz * tau - 9.8 * tau * tau
        o.location = foot + Vector((vx * tau, math.sin(a) * sp * 0.25 * tau, z)); o.hide_render = z < 0.2
    k = smoothstep(0, 7, t)   # slow push-in, low on the mud looking up at the falls (kept upper-right, clear of the host)
    look(S['cam'], (foot.x + lerp(-8.0, -7.0, k), foot.y + lerp(-17.0, -15.0, k), 1.2), (foot.x - 2.0, foot.y, FALL_H * 0.72))

# ------------------------------------------------------------------ M: cutaway diorama
STRATA = [('#C9A57A', 0.0, -3.0), ('#B08A62', -3.0, -8.0), ('#9C7553', -8.0, -14.0), ('#86634A', -14.0, -21.0), ('#735540', -21.0, -90.0)]
def build_mine():
    M = mats(); S = {"M": M}; rng = random.Random(8)
    sky_world('#3A78E6', '#D8F0FF')
    WD, DP = 60.0, 22.0    # block width (x) and depth (y); the cut face is at y = -DP/2
    S['t_breach'] = timeline_event()
    yF = -DP / 2
    # strata slabs
    for col, z0, z1 in STRATA:
        o = box('stratum', (WD, DP, z0 - z1), toon_mat('st' + col, col, shade=0.72, hi=None), loc=(0, 0, (z0 + z1) / 2)); outline(o, 0.12)
    # salt dome: a tall rounded low-poly blob poking up into the strata, cut flat at the front face
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
    for v in bm.verts:
        x, y, z = v.co; v.co = Vector((x * 14 * (1 - 0.25 * max(z, 0)), y * 10, z * 22 - 30))
        if v.co.y < yF + 0.02: v.co.y = yF + 0.02
        if v.co.z > -6.5: v.co.z = -6.5 - 0.6 * (abs(x))
    me = bpy.data.meshes.new('dome'); bm.to_mesh(me); bm.free()
    dome = bpy.data.objects.new('dome', me); bpy.context.collection.objects.link(dome); me.materials.append(toon_mat('salt', '#F1E6EC', shade=(0.8, 0.78, 0.9), hi=1.04))
    for p in me.polygons: p.use_smooth = False
    outline(dome, 0.12)
    # front face of the dome: lighter flat salt with crystal flecks so the cut reads as a cut
    face = mesh_from('salt_face', [(-12.5, yF - 0.03, -38), (12.5, yF - 0.03, -38), (12.5, yF - 0.03, -9), (6, yF - 0.03, -6.8), (-6, yF - 0.03, -6.8), (-12.5, yF - 0.03, -9)],
                     [(0, 1, 2, 3, 4, 5)], flat_mat('saltface', '#FBF3F6'))
    for k in range(40):
        x = rng.uniform(-11, 11); z = rng.uniform(-36, -9)
        box('fleck', (0.35, 0.02, 0.35), flat_mat('fleck', '#E3D2DD'), loc=(x, yF - 0.05, z), rot=(0, rng.uniform(0, 1.5), 0))
    # mine level at z = -24: a room-and-pillar slice (dark rooms, salt pillars), lamps, miners
    MZ = -24.0; S['MZ'] = MZ
    rooms = [(-10, -5.5), (-4, 0.5), (2, 6.5), (8, 11.0)]
    for x0, x1 in rooms:
        box('room', (x1 - x0, 0.05, 3.2), flat_mat('room', '#3B2F4A'), loc=((x0 + x1) / 2, yF - 0.07, MZ + 1.6))
        box('floor', (x1 - x0, 0.06, 0.35), flat_mat('floor', '#7C6A86'), loc=((x0 + x1) / 2, yF - 0.09, MZ + 0.17))
        for k in range(2):
            lx = x0 + (x1 - x0) * (0.3 + 0.4 * k)
            ico('lamp', 0.18, flat_mat('lamp', '#FFE27A'), loc=(lx, yF - 0.12, MZ + 3.0))
            box('glow', (1.4, 0.03, 1.0), flat_mat('lampglow', '#FFE27A', alpha=0.18), loc=(lx, yF - 0.1, MZ + 2.6))
    # tunnels drawn as wide dark bands connecting rooms behind pillars
    box('tunnel', (22.0, 0.04, 1.5), flat_mat('tunnel', '#2E2440'), loc=(0.5, yF - 0.06, MZ + 0.8))
    # lower level (the mine went to 1,500 ft)
    for x0, x1 in [(-8, -2), (1, 9)]:
        box('room2', (x1 - x0, 0.05, 2.6), flat_mat('room', '#3B2F4A'), loc=((x0 + x1) / 2, yF - 0.07, -31.5))
    S['miners'] = []
    for k, x in enumerate([-8.6, -6.6, -2.6, -0.9, 3.3, 5.4, 9.3]):
        root = bpy.data.objects.new('miner', None); bpy.context.collection.objects.link(root); root.location = (x, yF - 0.4, MZ + 0.35)
        bd = cyl('mbody', 0.28, 0.22, 0.0, 1.0, toon_mat('overall' + str(k % 2), ['#2F6FD6', '#F08A24'][k % 2], shade=0.7, hi=None), n=6); bd.parent = root
        hd = ico('mhead', 0.25, toon_mat('mskin', '#F2C9A8', shade=0.75, hi=None), loc=(0, 0, 1.25), sub=1); hd.parent = root
        ht = cyl('mhat', 0.3, 0.2, 1.35, 1.6, M['yellow'], n=6); ht.parent = root
        lamp = ico('mlamp', 0.08, flat_mat('mlampc', '#FFFFFF'), loc=(0, -0.28, 1.45), sub=1); lamp.parent = root
        for o in (bd, hd, ht): outline(o, 0.05)
        S['miners'].append((root, x, k))
    # lake slab on top (front face cut) + surface that dimples later
    S['lake'] = box('lake_slab', (WD, DP, 1.2), toon_mat('lakecut', '#2E8FE0', shade=0.85, hi=None), loc=(0, 0, 0.6))
    S['water'] = Water(M, R=10.8, n_ang=48, n_rad=16, r0=0.4, name='surf')   # inside the slab: never overhangs the cut; S['water'].obj.location = (0, 0, 1.25)
    S['water'].abyss.hide_render = True
    # ground ring around the lake slab (shore at the block edges)
    for sx in (-1, 1):
        o = box('shore', (8, DP, 1.6), toon_mat('shoreg', '#79C35A', shade=0.75, hi=None), loc=(sx * (WD / 2 - 4), 0, 0.8)); outline(o, 0.12)
    for k in range(10):
        sx = -1 if k < 5 else 1; tree(M, sx * rng.uniform(WD / 2 - 7, WD / 2 - 1.5), rng.uniform(-DP / 2 + 1.5, DP / 2 - 1.5), 1.6, rng.uniform(0.7, 1.0), rng, outline_w=0.08)
    rg = rig(M); rg.location = (0, 1.0, 1.25); rg.scale = (0.9, 0.9, 0.9); S['rig'] = rg
    # drill string: from the rig down to the bit; pipe drawn in front of the cut so it reads
    S['pipe'] = cyl('drillpipe', 0.22, 0.22, 0.0, 1.0, M['steel'], n=6, loc=(0, yF - 0.3, 1.2)); outline(S['pipe'], 0.06)
    S['bit'] = mesh_from('bit', [(-0.45, 0, 0), (0.45, 0, 0), (0, 0.45, 0), (0, -0.45, 0), (0, 0, -0.9)], [(0, 4, 3), (3, 4, 1), (1, 4, 2), (2, 4, 0), (0, 3, 1, 2)], M['yellow']); outline(S['bit'], 0.05)
    # water: column pouring through the hole, flood box filling the rooms, spray bits
    S['col'] = cyl('pour', 1.0, 1.0, 0.0, 1.0, toon_mat('pourw', '#4FB3F0', shade=0.8, hi=1.2), n=8, loc=(0, yF - 0.35, 0)); outline(S['col'], 0.06)
    S['flood'] = box('flood', (1.0, 0.1, 1.0), flat_mat('floodw', '#3EA0EE'), loc=(0, yF - 0.2, MZ))
    S['spray'] = [ico('spray', 0.3, M['foam'], sub=1) for _ in range(16)]
    S['hole'] = cyl('holeedge', 1.0, 1.0, -0.05, 0.05, flat_mat('holedark', '#123A80'), n=10, loc=(0, yF - 0.32, MZ + 3.25))
    S['cam'] = cam_new(30)
    S['cam'].data.shift_y = -0.3; S['cam'].data.shift_x = -0.07   # lift the falls into the upper right: captions + host live lower left
    return S

def update_mine(S, t):
    tb = S['t_breach']; MZ = S['MZ']; yF = -11.0
    roof = MZ + 3.2
    # bit descends: fast through the strata, slows near the roof, punches through at tb
    k = smoothstep(0.0, tb, t) ** 0.85
    zbit = lerp(-0.5, roof, k) if t < tb else roof - 1.6 * smoothstep(tb, tb + 0.4, t)
    S['bit'].location = (0, yF - 0.3, zbit); S['pipe'].scale = (1, 1, 1.25 - zbit); S['pipe'].location = (0, yF - 0.3, zbit)
    after = max(t - tb, 0.0)
    hole_r = 0.25 + 0.55 * min(after, 1.0) + 0.18 * max(after - 1.0, 0.0)   # the hole keeps widening: fresh water dissolves the salt
    on = t > tb + 0.05
    # pouring column from the lake to the room
    S['col'].hide_render = not on; S['col'].location = (0, yF - 0.35, roof - 0.1); S['col'].scale = (hole_r, hole_r, (1.2 - roof) * smoothstep(tb, tb + 0.5, t) + 0.1)
    S['hole'].hide_render = not on; S['hole'].scale = (hole_r * 1.15, hole_r * 1.15, 1)
    # the room floods outward from the breach
    fl = smoothstep(tb + 0.3, tb + 9.0, t); width = 2.0 + 20.0 * fl; height = 0.3 + 2.9 * smoothstep(tb + 2.0, tb + 14.0, t)
    S['flood'].hide_render = not on; S['flood'].scale = (width, 1.0, height); S['flood'].location = (0.5, yF - 0.2, MZ + height / 2 + 0.05)
    rng = random.Random(4)
    for i, s in enumerate(S['spray']):
        a = rng.uniform(-2.6, -0.5); sp = rng.uniform(3, 7); ph = rng.random(); per = 0.8
        tau = ((after + ph * per) % per)
        x = math.cos(a) * sp * tau * (1 if i % 2 else -1); z = roof - 0.2 + math.sin(a) * sp * tau - 4.9 * tau * tau
        s.location = (x, yF - 0.6, max(z, MZ + 0.2)); s.hide_render = not on or z < MZ; sc = 0.6 + 0.5 * (1 - tau / per); s.scale = (sc, sc, sc)
    # lake surface: dimples into a whirlpool and drops a little
    D = 3.5 * smoothstep(tb + 0.5, tb + 6.0, t); S['water'].update(t, D, level=-0.25 * smoothstep(tb, tb + 10, t), spin=D > 0.05)
    # rig tilts after the breach
    S['rig'].rotation_euler = (0.0, -0.22 * smoothstep(tb + 1.0, tb + 6.0, t), 0.0); S['rig'].location.z = 1.25 - 0.6 * smoothstep(tb + 2.0, tb + 8.0, t)
    # miners: idle sway, then run left (away from the breach) towards the shaft
    for root, x0, k in S['miners']:
        run = smoothstep(tb + 0.6 + 0.12 * k, tb + 6.0, t)
        root.location.x = x0 - 22 * run * (0.8 + 0.1 * (k % 3)); root.location.z = MZ + 0.35 + (0.12 * abs(math.sin(t * 10 + k)) if run > 0 else 0.0)
        root.hide_render = root.location.x < -11.5
    # camera: starts on the rig + lake, tilts down following the bit, holds on the mine level, eases back a bit
    cam = S['cam']; zc = lerp(2.0, MZ + 1.5, smoothstep(0.4, tb - 0.4, t)); back = 24 + 8 * smoothstep(tb + 1.5, tb + 7.0, t)
    zc += 1.5 * smoothstep(tb + 1.5, tb + 6.0, t)
    look(cam, (8.0, -11 - back, zc + 3.0), (1.5, 0.0, zc - 7.5))   # aim low: the mine level sits at y~650-750 of the frame, clear of the host + captions

# ------------------------------------------------------------------ cameras for the lake shots
def update_cam(S, t):
    cam = S['cam']
    if SHOT == "C":
        k = smoothstep(0, 5.0, t); look(cam, (lerp(40, 30, k), lerp(-62, -44, k), lerp(36, 25, k)), (1, 4, -3))
    elif SHOT == "W":
        a = -0.95 + 0.02 * t
        look(cam, (40 * math.cos(a), 40 * math.sin(a), 30 - 0.3 * t), (5.5, -4.5, -6.5))   # vortex centre at y~720: above the caption line (975) and the host
    elif SHOT == "V":
        pass

def setup_v_cam(S):
    cd = bpy.data.cameras.new('camv'); cam = bpy.data.objects.new('camv', cd); bpy.context.collection.objects.link(cam)
    cd.type = 'ORTHO'; cd.ortho_scale = 40.0; cd.sensor_fit = 'VERTICAL'; cd.clip_start = 1; cd.clip_end = 200
    # vortex centre at pixel (540, 700) of 1920: 260 px above centre at 48 px/unit -> camera 5.4167 units towards -y
    cam.location = (0.0, -260.0 / 48.0, 60.0); cam.rotation_euler = (0, 0, 0); bpy.context.scene.camera = cam; S['cam'] = cam

def main():
    clear_scene()
    if SHOT == "M":
        S = build_mine(); upd = update_mine
    elif SHOT == "F":
        S = build_falls(); upd = update_falls
    else:
        S = build_lake()
        if SHOT == "V": build_v_extras(S); setup_v_cam(S)
        else: S['cam'] = cam_new(30)
        def upd(S, t): update_lake(S, t); update_cam(S, t)
    res = ARGS["res"]; setup_toon_render(res, res * 16 // 9, ARGS["samples"], FPS, transparent=False)
    os.makedirs(ARGS["out"], exist_ok=True); sc = bpy.context.scene
    frames = [ARGS["start"]] if ARGS["preview"] else range(ARGS["start"], ARGS["end"])
    for f in frames:
        path = os.path.join(ARGS["out"], f"{SHOT}_{f:04d}.png")
        if os.path.exists(path) and not ARGS["preview"]: continue
        upd(S, f / FPS); sc.frame_set(f); sc.render.filepath = path
        t0 = time.time(); bpy.ops.render.render(write_still=True)
        print(f"FRAME {SHOT} {f} {time.time() - t0:.1f}s", flush=True)

main()

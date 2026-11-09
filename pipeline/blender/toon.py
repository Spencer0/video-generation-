"""Low-poly anime ("toon") toolkit for Cycles, shared by scene_peigneur.py and scene_vtuber.py.

Look: flat cel shading with hard bands, black inverted-hull outlines, pure colours, no noise.
Everything is Emission, so a camera ray stops at the first opaque surface: no bounces, no
denoiser, 4-8 samples are only anti-aliasing. Typical cost is well under 1 s/frame at 576x1024.

  toon_mat(name, '#RRGGBB', shade=..)   cel material: base * band(N.L) (+ optional rim), Emission
  flat_mat(name, '#RRGGBB', alpha=1)     unlit colour (eyes, decals, sky cards); alpha < 1 mixes with Transparent
  attr_mat(name, attr='Col')             cel material whose base colour is a per-vertex colour attribute
  outline(obj, w)                        inverted hull: copy, push along vertex normals, flip, black, backfaces transparent
  mesh_from(name, verts, faces)          new object from raw lists
  blade(...)                             tapered curved hair strand / spike (also: grass, spray, debris)
  loft(rings)                            closed tube through a list of rings (torso, hulls, trunks)
  setup_toon_render(...)                 Cycles settings for this look (Standard view transform, emission-only)
Colours are given as sRGB hex and converted to linear for the node values, so what you type is what you see.
"""
import bpy, bmesh, math
from mathutils import Vector

LIGHT = Vector((-0.45, -0.75, 0.55)).normalized()   # key light direction (towards the light), world space

def srgb(h, a=1.0):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return (*lin, a)

def _base(name):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial'); return m, nt, out

def _band(nt, shade, hi, light, steps):
    """Return a node socket with the cel band factor (colour) from N.L."""
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    dot = nt.nodes.new('ShaderNodeVectorMath'); dot.operation = 'DOT_PRODUCT'
    dot.inputs[1].default_value = tuple(light)
    nt.links.new(geo.outputs['Normal'], dot.inputs[0])
    ramp = nt.nodes.new('ShaderNodeValToRGB'); ramp.color_ramp.interpolation = 'CONSTANT'
    el = ramp.color_ramp.elements
    sh = shade if isinstance(shade, tuple) else (shade, shade, shade * 1.06 if shade < 0.94 else shade)
    el[0].position = 0.0; el[0].color = (*sh, 1)
    el[1].position = steps[0]; el[1].color = (1, 1, 1, 1)
    if hi:
        e = el.new(steps[1]); e.color = (hi, hi, hi, 1)
    # map dot from [-1,1] to [0,1]
    mr = nt.nodes.new('ShaderNodeMath'); mr.operation = 'MULTIPLY_ADD'; mr.inputs[1].default_value = 0.5; mr.inputs[2].default_value = 0.5
    nt.links.new(dot.outputs['Value'], mr.inputs[0]); nt.links.new(mr.outputs[0], ramp.inputs['Fac'])
    return ramp.outputs['Color'], geo

def toon_mat(name, col, shade=0.62, hi=1.07, rim=0.0, rim_col='#FFFFFF', light=None, steps=(0.52, 0.86), strength=1.0):
    """Cel material. shade: brightness multiplier in the shadow band (or an RGB tuple to tint shadows);
    hi: multiplier in the highlight band (None/0 = two bands); rim: add a thin rim light on silhouettes."""
    m, nt, out = _base(name)
    band, geo = _band(nt, shade, hi, light or LIGHT, steps)
    rgb = nt.nodes.new('ShaderNodeRGB'); rgb.outputs[0].default_value = srgb(col)
    mul = nt.nodes.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1.0
    nt.links.new(rgb.outputs[0], mul.inputs['A']); nt.links.new(band, mul.inputs['B'])
    colsock = mul.outputs['Result']
    if rim > 0:
        lw = nt.nodes.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.5
        thr = nt.nodes.new('ShaderNodeMath'); thr.operation = 'GREATER_THAN'; thr.inputs[1].default_value = 0.82
        nt.links.new(lw.outputs['Facing'], thr.inputs[0])
        rm = nt.nodes.new('ShaderNodeMix'); rm.data_type = 'RGBA'; rm.blend_type = 'SCREEN'
        k = nt.nodes.new('ShaderNodeMath'); k.operation = 'MULTIPLY'; k.inputs[1].default_value = rim
        nt.links.new(thr.outputs[0], k.inputs[0]); nt.links.new(k.outputs[0], rm.inputs['Factor'])
        nt.links.new(colsock, rm.inputs['A']); rm.inputs['B'].default_value = srgb(rim_col); colsock = rm.outputs['Result']
    em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Strength'].default_value = strength
    nt.links.new(colsock, em.inputs['Color']); nt.links.new(em.outputs[0], out.inputs['Surface'])
    m.diffuse_color = srgb(col)
    return m

def attr_mat(name, attr='Col', shade=0.66, hi=1.06, light=None, steps=(0.5, 0.88), alpha_attr=None):
    """Cel material with base colour from a colour attribute (set per frame from Python: water foam, mud...)."""
    m, nt, out = _base(name)
    band, geo = _band(nt, shade, hi, light or LIGHT, steps)
    at = nt.nodes.new('ShaderNodeAttribute'); at.attribute_name = attr; at.attribute_type = 'GEOMETRY'
    mul = nt.nodes.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1.0
    nt.links.new(at.outputs['Color'], mul.inputs['A']); nt.links.new(band, mul.inputs['B'])
    em = nt.nodes.new('ShaderNodeEmission'); nt.links.new(mul.outputs['Result'], em.inputs['Color'])
    if alpha_attr:
        tr = nt.nodes.new('ShaderNodeBsdfTransparent'); mix = nt.nodes.new('ShaderNodeMixShader')
        nt.links.new(at.outputs['Alpha'], mix.inputs['Fac']); nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(em.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs['Surface'])
    else:
        nt.links.new(em.outputs[0], out.inputs['Surface'])
    return m

def flat_mat(name, col, alpha=1.0, strength=1.0):
    """Unlit colour. alpha < 1: mixed with Transparent (blush, soft shadows, glows)."""
    m, nt, out = _base(name)
    em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = srgb(col); em.inputs['Strength'].default_value = strength
    if alpha < 1.0:
        tr = nt.nodes.new('ShaderNodeBsdfTransparent'); mix = nt.nodes.new('ShaderNodeMixShader'); mix.inputs['Fac'].default_value = alpha
        nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(em.outputs[0], mix.inputs[2]); nt.links.new(mix.outputs[0], out.inputs['Surface'])
    else:
        nt.links.new(em.outputs[0], out.inputs['Surface'])
    m.diffuse_color = srgb(col)
    return m

_OUTLINE = {}
def outline_mat(col='#1A1420'):
    if col in _OUTLINE: return _OUTLINE[col]
    m, nt, out = _base('outline_' + col)
    geo = nt.nodes.new('ShaderNodeNewGeometry'); em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = srgb(col)
    tr = nt.nodes.new('ShaderNodeBsdfTransparent'); mix = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(geo.outputs['Backfacing'], mix.inputs['Fac']); nt.links.new(em.outputs[0], mix.inputs[1]); nt.links.new(tr.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs['Surface'])
    _OUTLINE[col] = m; return m

def outline(obj, w=0.02, col='#1A1420'):
    """Inverted-hull outline as a child object (follows the parent's transform; static mesh only)."""
    me = obj.data.copy(); me.name = obj.name + '_ol'
    bm = bmesh.new(); bm.from_mesh(me); bm.normal_update()
    # push along the averaged vertex normal so flat-shaded hulls stay closed; scale-compensated
    s = obj.scale; sc = (abs(s.x) + abs(s.y) + abs(s.z)) / 3 or 1.0
    for v in bm.verts: v.co += v.normal * (w / sc)
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:]); bm.to_mesh(me); bm.free()
    me.materials.clear(); me.materials.append(outline_mat(col))
    for p in me.polygons: p.material_index = 0
    o = bpy.data.objects.new(obj.name + '_ol', me); bpy.context.collection.objects.link(o)
    o.parent = obj; o.matrix_parent_inverse.identity()
    o.visible_shadow = False
    return o

def mesh_from(name, verts, faces, mat=None, smooth=False, parent=None, loc=(0, 0, 0)):
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts], [], faces); me.update()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    if mat: me.materials.append(mat)
    for p in me.polygons: p.use_smooth = smooth
    o.location = loc
    if parent: o.parent = parent
    return o

def poly_disc(name, pts2, mat, plane='xz', parent=None, loc=(0, 0, 0), y=0.0):
    """Flat n-gon from 2D points (decals: eyes, mouth, blush). plane 'xz' faces -y (towards a camera at -y)."""
    if plane == 'xz': verts = [(p[0], y, p[1]) for p in pts2]
    else: verts = [(p[0], p[1], y) for p in pts2]
    f = list(range(len(verts)))
    if plane == 'xz': f = f[::-1]
    return mesh_from(name, verts, [f], mat, parent=parent, loc=loc)

def ellipse(rx, rz, n=14, cx=0.0, cz=0.0, a0=0.0, a1=2 * math.pi, closed=True):
    k = n if closed else n + 1
    return [(cx + rx * math.cos(a0 + (a1 - a0) * i / n), cz + rz * math.sin(a0 + (a1 - a0) * i / n)) for i in range(k)]

def strip(name, pts2, width, mat, y=0.0, parent=None, taper=(1.0, 1.0), loc=(0, 0, 0)):
    """Flat ribbon along a 2D polyline in the xz plane (lash lines, brows, closed eyes, mouth lines)."""
    verts = []; n = len(pts2)
    for i, p in enumerate(pts2):
        a = pts2[max(i - 1, 0)]; b = pts2[min(i + 1, n - 1)]
        dx, dz = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dz) or 1
        nx, nz = -dz / L, dx / L; u = i / (n - 1); w = width * (taper[0] + (taper[1] - taper[0]) * u) / 2
        verts.append((p[0] + nx * w, y, p[1] + nz * w)); verts.append((p[0] - nx * w, y, p[1] - nz * w))
    faces = [(2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1) for i in range(n - 1)]
    return mesh_from(name, verts, faces, mat, parent=parent, loc=loc)

def bezier(p0, p1, p2, n):
    p0, p1, p2 = Vector(p0), Vector(p1), Vector(p2)
    return [(1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t * t * p2 for t in (i / (n - 1) for i in range(n))]

def blade(name, p0, p1, p2, width, thick, mat, segs=5, side=None, parent=None, tip=0.0, root_w=1.0):
    """Tapered strand along a quadratic bezier p0->p2 (control p1). Cross-section is a flat diamond:
    `width` across `side` (a world-ish vector), `thick` along the other normal. Tip width fraction `tip`."""
    pts = bezier(p0, p1, p2, segs + 1); verts = []; faces = []
    for i, p in enumerate(pts):
        a = pts[max(i - 1, 0)]; b = pts[min(i + 1, len(pts) - 1)]; t = (b - a).normalized()
        sd = Vector(side) if side is not None else Vector((1, 0, 0))
        sd = (sd - t * sd.dot(t)); sd = sd.normalized() if sd.length > 1e-6 else Vector((1, 0, 0))
        nm = t.cross(sd).normalized()
        u = i / segs; w = width * (root_w + (tip - root_w) * u ** 1.3) / 2; th = thick * (1 - 0.7 * u) / 2
        verts += [p + sd * w, p + nm * th, p - sd * w, p - nm * th]
    for i in range(segs):
        for k in range(4):
            a, b = 4 * i + k, 4 * i + (k + 1) % 4
            faces.append((a, b, b + 4, a + 4))
    faces.append((3, 2, 1, 0)); L = 4 * segs; faces.append((L, L + 1, L + 2, L + 3))
    return mesh_from(name, verts, faces, mat, parent=parent)

def loft(name, rings, mat, cap_top=True, cap_bottom=True, parent=None, smooth=False):
    """Closed tube through rings (each a list of 3D points, same count)."""
    n = len(rings[0]); verts = [v for r in rings for v in r]; faces = []
    for j in range(len(rings) - 1):
        for i in range(n):
            a = j * n + i; b = j * n + (i + 1) % n
            faces.append((a, b, b + n, a + n))
    if cap_bottom: faces.append(tuple(range(n))[::-1])
    if cap_top: faces.append(tuple(range((len(rings) - 1) * n, len(rings) * n)))
    o = mesh_from(name, verts, faces, mat, smooth=smooth, parent=parent)
    # make normals point outward regardless of ring winding
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:]); bm.to_mesh(o.data); bm.free()
    return o

def ring(cx, cy, cz, rx, ry, n=10, p=2.0, rot=0.0):
    out = []
    for i in range(n):
        a = 2 * math.pi * i / n + rot; c, s = math.cos(a), math.sin(a)
        out.append(Vector((cx + rx * math.copysign(abs(c) ** (2 / p), c), cy + ry * math.copysign(abs(s) ** (2 / p), s), cz)))
    return out

def box(name, size, mat, loc=(0, 0, 0), parent=None, rot=(0, 0, 0)):
    sx, sy, sz = (s / 2 for s in size)
    v = [(-sx, -sy, -sz), (sx, -sy, -sz), (sx, sy, -sz), (-sx, sy, -sz), (-sx, -sy, sz), (sx, -sy, sz), (sx, sy, sz), (-sx, sy, sz)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    o = mesh_from(name, v, f, mat, parent=parent, loc=loc); o.rotation_euler = rot; return o

def ico(name, r, mat, loc=(0, 0, 0), sub=1, scale=(1, 1, 1), parent=None, smooth=False):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o); me.materials.append(mat)
    for p in me.polygons: p.use_smooth = smooth
    o.location = loc; o.scale = scale
    if parent: o.parent = parent
    return o

def cyl(name, r0, r1, z0, z1, mat, n=8, loc=(0, 0, 0), parent=None, rot=(0, 0, 0)):
    o = loft(name, [ring(0, 0, z0, r0, r0, n), ring(0, 0, z1, r1, r1, n)], mat, parent=parent)
    o.location = loc; o.rotation_euler = rot; return o

def clear_scene():
    for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras, bpy.data.curves):
        for x in list(coll): coll.remove(x)
    _OUTLINE.clear()

def sky_world(top='#3D7BE0', horizon='#BFE6FF', ground='#7FB0D8', strength=1.0):
    """Anime sky: hard-ish gradient on the view direction's z (camera rays only; nothing is lit by it)."""
    w = bpy.data.worlds.get('World') or bpy.data.worlds.new('World'); bpy.context.scene.world = w; w.use_nodes = True; nt = w.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputWorld'); bg = nt.nodes.new('ShaderNodeBackground'); bg.inputs['Strength'].default_value = strength
    tc = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Window'], sep.inputs[0])
    ramp = nt.nodes.new('ShaderNodeValToRGB'); el = ramp.color_ramp.elements
    el[0].position = 0.0; el[0].color = srgb(horizon); el[1].position = 1.0; el[1].color = srgb(top)
    nt.links.new(sep.outputs['Y'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], bg.inputs['Color']); nt.links.new(bg.outputs[0], out.inputs['Surface'])
    return ramp

def setup_toon_render(res_x, res_y, samples=6, fps=30, transparent=False):
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; c = sc.cycles
    c.device = 'CPU'; c.samples = samples; c.use_adaptive_sampling = False; c.use_denoising = False
    c.max_bounces = 0; c.diffuse_bounces = 0; c.glossy_bounces = 0; c.transmission_bounces = 0; c.volume_bounces = 0
    c.transparent_max_bounces = 12; c.caustics_reflective = False; c.caustics_refractive = False
    c.pixel_filter_type = 'BLACKMAN_HARRIS'; c.filter_width = 1.3
    sc.render.film_transparent = transparent; sc.render.use_persistent_data = True
    sc.render.resolution_x = res_x; sc.render.resolution_y = res_y; sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA' if transparent else 'RGB'
    sc.render.image_settings.compression = 15; sc.render.fps = fps
    sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'; sc.view_settings.exposure = 0.0
    sc.use_nodes = False
    # emission-only: no lights needed; remove light-tree / MIS overhead
    c.use_light_tree = False

"""Example images for the 3D edit styles, rendered with Blender (the same tool Claude uses for 3D jobs).

    blender.exe -b -P render_3d.py -- <ReviewRoom folder> <out folder> [style ids...]

Every scene is built from scratch, from the app's Default assets (HDRIs, glTF models, textures) where it needs them.
"""
import bpy, bmesh, math, os, random, sys
from mathutils import Vector, noise

argv = sys.argv[sys.argv.index("--") + 1:]
ROOT, OUT = argv[0], argv[1]
ONLY = set(argv[2:])
DA = os.path.join(ROOT, "workspace", "assets", "Default assets")
HDRI = lambda n: os.path.join(DA, "3D", "HDRI", n + "_2k.hdr")
MODEL = lambda *p: os.path.join(DA, "3D", "Models", *p)
W, H = 960, 540


# ------------------------------------------------------------------ helpers
def reset(engine="CYCLES", samples=64):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    if engine == "CYCLES":
        sc.render.engine = "CYCLES"
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for dev in ("OPTIX", "CUDA"):
            try:
                prefs.compute_device_type = dev; prefs.get_devices()
                for d in prefs.devices: d.use = d.type == dev
                sc.cycles.device = "GPU"; break
            except Exception: pass
        cy = sc.cycles
        cy.samples = samples; cy.use_adaptive_sampling = True; cy.use_denoising = True
        try: cy.denoiser = "OPTIX"
        except Exception: pass
        cy.max_bounces = 10; cy.transmission_bounces = 10; cy.glossy_bounces = 6; cy.sample_clamp_indirect = 10
    else:
        for e in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
            try: sc.render.engine = e; break
            except Exception: pass
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = W, H, 100
    sc.render.image_settings.file_format = "PNG"
    sc.view_settings.view_transform = "AgX"
    try: sc.view_settings.look = "AgX - Medium High Contrast"
    except Exception: pass
    w = bpy.data.worlds.new("W"); sc.world = w
    try: w.use_nodes = True
    except Exception: pass
    return sc


def vivid():
    sc = bpy.context.scene; sc.view_settings.view_transform = "Standard"
    try: sc.view_settings.look = "None"
    except Exception: pass


def link(o): bpy.context.scene.collection.objects.link(o); return o


def nodes(m):
    try: m.use_nodes = True
    except Exception: pass
    return m.node_tree


def setin(node, name, val):
    for n in ([name] if isinstance(name, str) else name):
        if n in node.inputs:
            node.inputs[n].default_value = val; return


def mat(name, color=(0.8, 0.8, 0.8), rough=0.5, metal=0.0, trans=0.0, ior=1.45, emit=None, estr=0.0, coat=0.0, sss=0.0, film=0.0):
    m = bpy.data.materials.new(name); nt = nodes(m)
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    setin(b, "Base Color", (*color, 1)); setin(b, "Roughness", rough); setin(b, "Metallic", metal)
    setin(b, ["Transmission Weight", "Transmission"], trans); setin(b, "IOR", ior); setin(b, ["Coat Weight", "Clearcoat"], coat)
    setin(b, ["Subsurface Weight", "Subsurface"], sss)
    if film: setin(b, "Thin Film Thickness", film); setin(b, "Thin Film IOR", 1.4)
    if emit: setin(b, ["Emission Color", "Emission"], (*emit, 1)); setin(b, "Emission Strength", estr)
    return m


def give(o, m):
    if o.data and hasattr(o.data, "materials"): o.data.materials.clear(); o.data.materials.append(m)
    return o


def world_color(top, bottom=None, strength=1.0):
    nt = nodes(bpy.context.scene.world); nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld"); bg = nt.nodes.new("ShaderNodeBackground"); bg.inputs[1].default_value = strength
    nt.links.new(bg.outputs[0], out.inputs[0])
    if bottom is None: bg.inputs[0].default_value = (*top, 1); return
    tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = -0.2; mr.inputs["From Max"].default_value = 0.6
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    mix.inputs[6].default_value = (*bottom, 1); mix.inputs[7].default_value = (*top, 1)
    nt.links.new(tc.outputs["Generated"], sep.inputs[0]); nt.links.new(sep.outputs["Z"], mr.inputs[0]); nt.links.new(mr.outputs[0], mix.inputs[0])
    nt.links.new(mix.outputs[2], bg.inputs[0])


def world_hdri(path, strength=1.0, rot=0.0, bg=None):
    """HDRI lighting; with bg=(r,g,b) the camera sees that colour instead of the HDRI"""
    nt = nodes(bpy.context.scene.world); nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Rotation"].default_value = (0, 0, math.radians(rot))
    env = nt.nodes.new("ShaderNodeTexEnvironment"); env.image = bpy.data.images.load(path)
    b1 = nt.nodes.new("ShaderNodeBackground"); b1.inputs[1].default_value = strength
    nt.links.new(tc.outputs["Generated"], mp.inputs[0]); nt.links.new(mp.outputs[0], env.inputs[0]); nt.links.new(env.outputs[0], b1.inputs[0])
    if bg is None: nt.links.new(b1.outputs[0], out.inputs[0]); return
    b2 = nt.nodes.new("ShaderNodeBackground"); b2.inputs[0].default_value = (*bg, 1)
    lp = nt.nodes.new("ShaderNodeLightPath"); mx = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Camera Ray"], mx.inputs[0]); nt.links.new(b1.outputs[0], mx.inputs[1]); nt.links.new(b2.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs[0])


def camera(loc, target, lens=50, ortho=None, dof=None):
    c = bpy.data.cameras.new("cam"); o = link(bpy.data.objects.new("cam", c))
    o.location = loc; o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    c.lens = lens
    if ortho: c.type = "ORTHO"; c.ortho_scale = ortho
    if dof: c.dof.use_dof = True; c.dof.focus_distance = (Vector(target) - Vector(loc)).length; c.dof.aperture_fstop = dof
    bpy.context.scene.camera = o
    return o


def area(loc, target, power, size=2.0, color=(1, 1, 1)):
    l = bpy.data.lights.new("a", "AREA"); l.energy = power; l.size = size; l.color = color
    o = link(bpy.data.objects.new("a", l)); o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler(); return o


def sun(rot, strength=3.0, color=(1, 1, 1), angle=2.0):
    l = bpy.data.lights.new("s", "SUN"); l.energy = strength; l.color = color; l.angle = math.radians(angle)
    o = link(bpy.data.objects.new("s", l)); o.rotation_euler = [math.radians(a) for a in rot]; return o


def add(kind, **kw):
    getattr(bpy.ops.mesh, "primitive_" + kind + "_add")(**kw)
    return bpy.context.active_object


def smooth(o, subsurf=0, bevel=0.0):
    if bevel: m = o.modifiers.new("b", "BEVEL"); m.width = bevel; m.segments = 4
    if subsurf: m = o.modifiers.new("s", "SUBSURF"); m.levels = m.render_levels = subsurf
    try: bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active = o; bpy.ops.object.shade_smooth()
    except Exception: pass
    return o


def sweep(color, size=14, rough=0.6):
    """a photo-studio backdrop: floor that curves up into a wall"""
    o = add("grid", x_subdivisions=40, y_subdivisions=40, size=size)
    for v in o.data.vertices:
        y = v.co.y
        if y > 1.5: v.co.z = (y - 1.5) ** 2 * 0.35
    smooth(o); give(o, mat("sweep", color, rough)); return o


def import_model(path, height, at=(0, 0, 0), rot_z=0.0):
    before = set(bpy.data.objects)
    if path.endswith((".glb", ".gltf")): bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in new if o.type == "MESH" for c in o.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    s = height / max(1e-6, mx.z - mn.z)
    g = link(bpy.data.objects.new("grp", None))
    for o in new:
        if o.parent is None: o.parent = g
    c = (mn + mx) / 2
    for o in new:
        if o.parent is g: o.location -= Vector((c.x, c.y, mn.z))
    g.scale = (s, s, s); g.location = at; g.rotation_euler = (0, 0, math.radians(rot_z))
    return g


def render(sid):
    sc = bpy.context.scene; sc.render.filepath = os.path.join(OUT, sid + ".png")
    bpy.ops.render.render(write_still=True); print("RENDERED", sid, flush=True)


# ------------------------------------------------------------------ scenes
def product():
    reset(samples=96)
    world_hdri(HDRI("studio_small_09"), 0.8, rot=40, bg=(0.80, 0.85, 0.90))
    sweep((0.78, 0.84, 0.90), rough=0.5)
    p = smooth(add("cylinder", vertices=96, radius=0.75, depth=0.3, location=(0, 0, 0.15)), bevel=0.03)
    give(p, mat("ped", (0.93, 0.93, 0.92), 0.35))
    import_model(MODEL("Khronos", "WaterBottle.glb"), 1.5, at=(0, 0, 0.3), rot_z=20)
    area((2.6, -2.4, 3.2), (0, 0, 1), 500, 3)
    area((-2.5, 2.5, 2.4), (0, 0, 1), 350, 2, (0.75, 0.85, 1.0))
    camera((0, -4.8, 1.55), (0, 0, 1.0), 58)
    render("product")


def lowpoly():
    reset(samples=48); vivid()
    world_color((0.30, 0.55, 0.92), (1.0, 0.78, 0.55), 0.9)
    t = add("grid", x_subdivisions=34, y_subdivisions=34, size=26)
    random.seed(4)
    for v in t.data.vertices:
        x, y = v.co.x, v.co.y
        v.co.z = noise.noise(Vector((x * 0.16, y * 0.16, 0.3))) * 2.6 + 0.9 * math.exp(-((x + 3) ** 2 + (y - 4) ** 2) / 18) * 3
    bm = bmesh.new(); bm.from_mesh(t.data); bmesh.ops.triangulate(bm, faces=bm.faces); bm.to_mesh(t.data); bm.free()
    m = bpy.data.materials.new("terrain"); nt = nodes(m)
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"); setin(b, "Roughness", 0.9)
    geo = nt.nodes.new("ShaderNodeNewGeometry"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    el = ramp.color_ramp.elements
    el[0].position = 0.0; el[0].color = (0.85, 0.75, 0.45, 1); el[1].position = 0.2; el[1].color = (0.32, 0.62, 0.25, 1)
    for pos, col in ((0.55, (0.2, 0.45, 0.2, 1)), (0.75, (0.5, 0.45, 0.42, 1)), (0.9, (0.97, 0.97, 1.0, 1))):
        e = el.new(pos); e.color = col
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = -0.3; mr.inputs["From Max"].default_value = 4.0
    nt.links.new(geo.outputs["Position"], sep.inputs[0]); nt.links.new(sep.outputs["Z"], mr.inputs[0]); nt.links.new(mr.outputs[0], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], b.inputs["Base Color"]); give(t, m)
    wtr = add("plane", size=26, location=(0, 0, -0.2)); give(wtr, mat("water", (0.12, 0.45, 0.78), 0.2))
    leaf, wood = mat("leaf", (0.12, 0.42, 0.18), 0.85), mat("wood", (0.35, 0.2, 0.1), 0.9)
    for _ in range(60):
        x, y = random.uniform(-10, 10), random.uniform(-6, 10)
        z = noise.noise(Vector((x * 0.16, y * 0.16, 0.3))) * 2.6 + 0.9 * math.exp(-((x + 3) ** 2 + (y - 4) ** 2) / 18) * 3
        if z < 0.2 or z > 2.4: continue
        s = random.uniform(0.6, 1.1)
        give(add("cone", vertices=6, radius1=0.38 * s, depth=1.2 * s, location=(x, y, z + 0.75 * s)), leaf)
        give(add("cylinder", vertices=5, radius=0.07 * s, depth=0.4 * s, location=(x, y, z + 0.15 * s)), wood)
    sun((52, 0, 35), 3.5, (1.0, 0.92, 0.8))
    camera((0, -16, 8.5), (0, 1, 0.5), 32)
    render("lowpoly")


def clay_mat(name, color):
    m = mat(name, color, 0.55, sss=0.08); nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 60; bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.06
    nt.links.new(nz.outputs[0], bump.inputs["Height"]); nt.links.new(bump.outputs[0], b.inputs["Normal"]); return m


def clay():
    reset(samples=64)
    world_color((0.98, 0.88, 0.84), None, 0.7)
    sweep((0.98, 0.80, 0.74), rough=0.8)
    body = smooth(add("uv_sphere", radius=0.75, location=(0, 0, 0.85)), 1); body.scale = (0.85, 0.75, 1.0); give(body, clay_mat("body", (0.95, 0.45, 0.35)))
    for sx in (-0.24, 0.24):
        e = smooth(add("uv_sphere", radius=0.17, location=(sx, -0.6, 1.12))); give(e, clay_mat("eye", (0.98, 0.98, 0.96)))
        p = smooth(add("uv_sphere", radius=0.08, location=(sx, -0.73, 1.1))); give(p, clay_mat("pupil", (0.05, 0.05, 0.06)))
    for sx in (-0.78, 0.78):
        a = smooth(add("uv_sphere", radius=0.2, location=(sx, -0.1, 0.75))); a.scale = (0.8, 0.8, 1.2); give(a, clay_mat("arm", (0.95, 0.45, 0.35)))
    d = smooth(add("torus", major_radius=0.42, minor_radius=0.2, location=(1.7, -0.4, 0.2))); d.rotation_euler = (math.radians(15), 0, 0)
    give(d, clay_mat("donut", (0.98, 0.62, 0.75)))
    c = smooth(add("cube", size=0.7, location=(-1.6, -0.3, 0.35)), bevel=0.18); c.rotation_euler = (0, 0, math.radians(25)); give(c, clay_mat("cube", (0.45, 0.8, 0.7)))
    tr = smooth(add("cone", radius1=0.35, depth=1.0, location=(-1.0, 0.9, 0.5)), 1); give(tr, clay_mat("tree", (0.95, 0.8, 0.35)))
    area((-3, -4, 4), (0, 0, 0.8), 900, 6); area((3, -2, 2.5), (0, 0, 0.8), 250, 3, (1.0, 0.9, 0.85))
    camera((0, -6.2, 2.4), (0, 0, 0.75), 50)
    render("clay")


def toon():
    reset("EEVEE"); vivid()
    world_color((1.0, 0.93, 0.7), None, 1.0)
    sc = bpy.context.scene; sc.render.use_freestyle = True
    try: sc.render.line_thickness_mode = "ABSOLUTE"; sc.render.line_thickness = 1.0
    except Exception: pass
    vl = bpy.context.view_layer; vl.use_freestyle = True; fs = vl.freestyle_settings
    ls = fs.linesets[0] if len(fs.linesets) else fs.linesets.new("lines")
    st = bpy.data.linestyles.new("ink"); st.thickness = 3.0; st.color = (0.08, 0.05, 0.04); ls.linestyle = st
    ls.select_by_visibility = True; ls.select_silhouette = True; ls.select_border = True; ls.select_crease = True

    def tmat(name, light, mid, dark):
        m = bpy.data.materials.new(name); nt = nodes(m); nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial"); dif = nt.nodes.new("ShaderNodeBsdfDiffuse"); s2r = nt.nodes.new("ShaderNodeShaderToRGB")
        ramp = nt.nodes.new("ShaderNodeValToRGB"); ramp.color_ramp.interpolation = "CONSTANT"; em = nt.nodes.new("ShaderNodeEmission")
        el = ramp.color_ramp.elements; el[0].color = (*dark, 1); el[1].position = 0.55; el[1].color = (*light, 1)
        e = el.new(0.2); e.color = (*mid, 1)
        nt.links.new(dif.outputs[0], s2r.inputs[0]); nt.links.new(s2r.outputs[0], ramp.inputs[0]); nt.links.new(ramp.outputs[0], em.inputs[0])
        nt.links.new(em.outputs[0], out.inputs[0]); return m
    m1 = smooth(add("monkey", location=(0, 0, 1.0)), 2); m1.rotation_euler = (math.radians(-10), 0, math.radians(-15))
    give(m1, tmat("orange", (1.0, 0.62, 0.2), (0.85, 0.38, 0.1), (0.45, 0.15, 0.05)))
    s = smooth(add("uv_sphere", radius=0.55, location=(1.8, 0.4, 0.55))); give(s, tmat("blue", (0.35, 0.65, 1.0), (0.2, 0.4, 0.8), (0.08, 0.15, 0.4)))
    c = add("cube", size=0.9, location=(-1.8, 0.3, 0.45)); c.rotation_euler = (0, 0, math.radians(30))
    give(c, tmat("green", (0.5, 0.9, 0.4), (0.3, 0.65, 0.25), (0.12, 0.3, 0.1)))
    f = add("plane", size=12); give(f, tmat("floor", (1.0, 0.93, 0.7), (0.95, 0.82, 0.55), (0.8, 0.65, 0.4)))
    sun((50, 0, 30), 4.0)
    camera((0, -6.5, 2.6), (0, 0, 0.8), 45)
    render("toon")


def diorama():
    reset(samples=80)
    world_color((0.93, 0.90, 0.98), None, 0.9)
    tex = os.path.join(DA, "3D", "Textures", "Laminate floor 02", "laminate_floor_02_diffuse_1k.jpg")
    fl = add("cube", size=1, location=(0, 0, -0.08)); fl.scale = (4.2, 4.2, 0.16)
    fm = mat("floor", (0.7, 0.5, 0.3), 0.45)
    if os.path.exists(tex):
        nt = fm.node_tree; b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        im = nt.nodes.new("ShaderNodeTexImage"); im.image = bpy.data.images.load(tex); im.projection = "BOX"
        tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (0.5, 0.5, 0.5)
        nt.links.new(tc.outputs["Object"], mp.inputs[0]); nt.links.new(mp.outputs[0], im.inputs[0]); nt.links.new(im.outputs[0], b.inputs["Base Color"])
    give(fl, fm)
    wl = add("cube", size=1, location=(0, 2.1, 1.3)); wl.scale = (4.2, 0.16, 2.6); give(wl, mat("wl", (0.62, 0.78, 0.92), 0.8))
    wr = add("cube", size=1, location=(2.1, 0, 1.3)); wr.scale = (0.16, 4.2, 2.6); give(wr, mat("wr", (0.98, 0.78, 0.72), 0.8))
    cut = add("cube", size=1, location=(2.1, -0.4, 1.45)); cut.scale = (0.6, 1.3, 1.0); cut.hide_render = True
    bo = wr.modifiers.new("win", "BOOLEAN"); bo.object = cut; bo.operation = "DIFFERENCE"
    rug = add("plane", size=1, location=(-0.1, -0.1, 0.005)); rug.scale = (1.9, 1.3, 1); give(rug, mat("rug", (0.95, 0.75, 0.25), 0.9))
    import_model(MODEL("Sofa 02", "sofa_02_1k.gltf"), 0.85, at=(-0.2, 1.45, 0), rot_z=0)
    import_model(MODEL("Wooden table 02", "wooden_table_02_1k.gltf"), 0.42, at=(-0.1, 0.0, 0))
    import_model(MODEL("Potted plant 04", "potted_plant_04_1k.gltf"), 1.3, at=(1.45, 1.45, 0))
    import_model(MODEL("Marble bust 01", "marble_bust_01_1k.gltf"), 0.32, at=(-0.1, 0.0, 0.42), rot_z=-30)
    area((0, 0, 4.5), (0, 0, 0), 600, 4); sun((55, 0, 115), 2.5, (1.0, 0.9, 0.75))
    camera((-7, -7, 6.2), (0.3, 0.3, 0.9), ortho=6.4)
    render("diorama")


def abstract():
    reset(samples=80)
    world_color((0.30, 0.10, 0.38), (0.05, 0.04, 0.14), 1.0)
    t = smooth(add("torus", major_radius=1.25, minor_radius=0.42, major_segments=96, minor_segments=48, location=(0, 0.3, 1.2)))
    t.rotation_euler = (math.radians(70), math.radians(15), 0); give(t, mat("iri", (0.92, 0.92, 0.96), 0.12, metal=1.0, film=420))
    give(smooth(add("uv_sphere", radius=0.55, location=(1.55, -0.6, 0.55))), mat("orange", (1.0, 0.42, 0.08), 0.25, coat=0.6))
    give(smooth(add("uv_sphere", radius=0.35, location=(-1.6, -0.9, 1.9))), mat("lilac", (0.7, 0.55, 1.0), 0.6))
    give(smooth(add("uv_sphere", radius=0.3, location=(-0.4, -1.4, 0.45))), mat("glass", (1, 1, 1), 0.02, trans=1.0, ior=1.5))
    cap = smooth(add("cylinder", radius=0.18, depth=1.6, location=(-1.9, 0.4, 0.8)), bevel=0.17); cap.rotation_euler = (math.radians(30), math.radians(40), 0)
    give(cap, mat("pink", (1.0, 0.35, 0.6), 0.3))
    area((-4, -3, 3), (0, 0, 1), 700, 3, (1.0, 0.45, 0.75)); area((4, -2, 2.5), (0, 0, 1), 600, 3, (0.35, 0.8, 1.0)); area((0, -1, 6), (0, 0, 1), 300, 4)
    camera((0, -10.5, 1.8), (0, 0, 1.05), 50, dof=3.5)
    render("abstract")


def glass():
    reset(samples=160)
    world_hdri(HDRI("studio_small_08"), 1.3, rot=200, bg=(0.025, 0.025, 0.035))
    f = add("plane", size=20); give(f, mat("floor", (0.02, 0.02, 0.025), 0.06))
    import_model(MODEL("Khronos", "IridescenceLamp.glb"), 1.45, at=(-0.85, 0.2, 0), rot_z=20)
    import_model(MODEL("Khronos", "GlassVaseFlowers.glb"), 1.15, at=(0.85, 0.35, 0))
    give(smooth(add("uv_sphere", radius=0.3, location=(0.05, -0.75, 0.3))), mat("g", (1, 1, 1), 0.0, trans=1.0, ior=1.5))
    area((0, 3, 2.5), (0, 0, 0.7), 400, 4, (0.8, 0.9, 1.0)); area((-3, -2, 3), (0, 0, 0.7), 250, 2)
    camera((0, -4.6, 1.2), (0, 0, 0.62), 55)
    render("glass")


def logo3d():
    reset(samples=96)
    world_hdri(HDRI("studio_small_03"), 0.9, rot=60, bg=(0.012, 0.012, 0.018))
    f = add("plane", size=30); give(f, mat("floor", (0.015, 0.015, 0.02), 0.08))
    cu = bpy.data.curves.new("t", "FONT"); cu.body = "REVIEW ROOM"; cu.align_x = "CENTER"; cu.align_y = "BOTTOM"
    cu.extrude = 0.16; cu.bevel_depth = 0.025; cu.bevel_resolution = 4; cu.size = 1.0
    for fp in (r"C:\Windows\Fonts\bahnschrift.ttf", r"C:\Windows\Fonts\arialbd.ttf"):
        if os.path.exists(fp): cu.font = bpy.data.fonts.load(fp); break
    t = link(bpy.data.objects.new("t", cu)); t.rotation_euler = (math.radians(90), 0, 0); t.location = (0, 0, 0.0)
    give(t, mat("gold", (1.0, 0.76, 0.33), 0.2, metal=1.0))
    area((0, -3, 4), (0, 0, 0.5), 600, 3, (1.0, 0.9, 0.75)); area((-5, 2, 1.5), (0, 0, 0.5), 500, 2, (0.3, 0.55, 1.0))
    area((5, 2, 1.5), (0, 0, 0.5), 500, 2, (0.3, 0.55, 1.0))
    camera((0, -9.0, 1.3), (0, 0, 0.5), 45)
    render("logo3d")


def medical3d(flip=False, sid="medical3d"):
    reset(samples=96)
    world_hdri(HDRI("studio_small_09"), 0.55, rot=0, bg=(0.05, 0.16, 0.36))
    stl = os.path.join(DA, "3D", "Models", "NIH dental maxilla", "maxillary_teeth_w_base.stl")   # NIH 3D, public domain
    bpy.ops.wm.stl_import(filepath=stl)
    o = bpy.context.selected_objects[0]
    o.rotation_euler = (math.radians(-90), 0, 0)                 # the scan is Y-up: lay the chewing surface flat, facing up
    bpy.context.view_layer.objects.active = o; bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))); mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    s = 2.8 / (mx.x - mn.x); c = (mn + mx) / 2
    g = link(bpy.data.objects.new("g", None)); o.parent = g; o.location -= c
    g.scale = (s, s, s); g.location = (0, 0, (mx.z - mn.z) * s / 2)
    if flip: g.rotation_euler = (math.radians(180), 0, 0)
    give(o, mat("enamel", (0.95, 0.93, 0.88), 0.28, sss=0.15, coat=0.3))
    fl = add("plane", size=20); give(fl, mat("floor", (0.05, 0.16, 0.36), 0.35))
    beam = add("cylinder", radius=0.01, depth=3.0, location=(0, 0.05, 0.92)); beam.rotation_euler = (0, math.radians(90), 0)
    give(beam, mat("beam", (0, 0, 0), emit=(0.2, 0.85, 1.0), estr=30))
    area((2, -3, 4), (0, 0, 0.4), 500, 3); area((-3, 2, 3), (0, 0, 0.4), 250, 3, (0.8, 0.9, 1.0))
    camera((0, -3.9, 4.3), (0, 0.15, 0.25), 40)
    render(sid)


def interior():
    reset(samples=128)
    world_hdri(HDRI("kloofendal_48d_partly_cloudy_puresky"), 1.6, rot=110)
    fl = add("plane", size=1); fl.scale = (7, 6, 1)
    tex = os.path.join(DA, "3D", "Textures", "Laminate floor 02", "laminate_floor_02_diffuse_1k.jpg")
    fm = mat("floor", (0.6, 0.45, 0.3), 0.4)
    if os.path.exists(tex):
        nt = fm.node_tree; b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        im = nt.nodes.new("ShaderNodeTexImage"); im.image = bpy.data.images.load(tex)
        tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (3, 3, 3)
        nt.links.new(tc.outputs["UV"], mp.inputs[0]); nt.links.new(mp.outputs[0], im.inputs[0]); nt.links.new(im.outputs[0], b.inputs["Base Color"])
    give(fl, fm)
    wall = mat("wall", (0.92, 0.9, 0.86), 0.85)
    back = add("cube", size=1, location=(0, 3, 1.5)); back.scale = (7, 0.2, 3); give(back, wall)
    cut = add("cube", size=1, location=(0.6, 3, 1.55)); cut.scale = (3.0, 0.6, 1.9); cut.hide_render = True
    bo = back.modifiers.new("w", "BOOLEAN"); bo.object = cut; bo.operation = "DIFFERENCE"
    left = add("cube", size=1, location=(-3.5, 0, 1.5)); left.scale = (0.2, 6, 3); give(left, wall)
    ceil = add("plane", size=1, location=(0, 0, 3)); ceil.scale = (7, 6, 1); give(ceil, wall)
    rug = add("plane", size=1, location=(-0.5, 0.9, 0.005)); rug.scale = (2.6, 1.8, 1); give(rug, mat("rug", (0.55, 0.6, 0.5), 0.95))
    import_model(MODEL("Sofa 02", "sofa_02_1k.gltf"), 0.9, at=(-0.6, 2.0, 0))
    import_model(MODEL("Wooden table 02", "wooden_table_02_1k.gltf"), 0.45, at=(-0.5, 0.75, 0))
    import_model(MODEL("Potted plant 04", "potted_plant_04_1k.gltf"), 1.5, at=(2.4, 2.4, 0))
    import_model(MODEL("Marble bust 01", "marble_bust_01_1k.gltf"), 0.36, at=(-0.35, 0.7, 0.45), rot_z=-20)
    sun((62, 0, 165), 4.0, (1.0, 0.88, 0.7), 1.5)
    area((0, 0, 2.9), (0, 0, 0), 120, 3, (1.0, 0.95, 0.9))
    camera((2.6, -2.7, 1.35), (-0.6, 1.4, 0.8), 22)
    render("interior")


def space():
    reset(samples=64)
    nt = nodes(bpy.context.scene.world); nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld"); bg = nt.nodes.new("ShaderNodeBackground")
    tc = nt.nodes.new("ShaderNodeTexCoord"); nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 420; nz.inputs["Detail"].default_value = 1
    ramp = nt.nodes.new("ShaderNodeValToRGB"); el = ramp.color_ramp.elements
    el[0].position = 0.68; el[0].color = (0.002, 0.003, 0.012, 1); el[1].position = 0.72; el[1].color = (1, 1, 1, 1)
    nt.links.new(tc.outputs["Generated"], nz.inputs[0]); nt.links.new(nz.outputs[0], ramp.inputs[0]); nt.links.new(ramp.outputs[0], bg.inputs[0])
    nt.links.new(bg.outputs[0], out.inputs[0])
    p = smooth(add("uv_sphere", radius=1.6, segments=96, ring_count=48, location=(0, 0, 0)))
    m = bpy.data.materials.new("planet"); mt = nodes(m); b = next(n for n in mt.nodes if n.type == "BSDF_PRINCIPLED"); setin(b, "Roughness", 0.7)
    n2 = mt.nodes.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 2.2; n2.inputs["Detail"].default_value = 10
    r2 = mt.nodes.new("ShaderNodeValToRGB"); e2 = r2.color_ramp.elements
    e2[0].position = 0.5; e2[0].color = (0.01, 0.06, 0.3, 1); e2[1].position = 0.6; e2[1].color = (0.55, 0.42, 0.25, 1)
    e = e2.new(0.53); e.color = (0.06, 0.3, 0.1, 1); e = e2.new(0.68); e.color = (0.92, 0.92, 0.95, 1)
    mt.links.new(n2.outputs[0], r2.inputs[0]); mt.links.new(r2.outputs[0], b.inputs["Base Color"]); give(p, m)
    atm = smooth(add("uv_sphere", radius=1.7, segments=96, ring_count=48))
    am = bpy.data.materials.new("atm"); at = nodes(am); at.nodes.clear()
    o2 = at.nodes.new("ShaderNodeOutputMaterial"); lw = at.nodes.new("ShaderNodeLayerWeight"); lw.inputs[0].default_value = 0.12
    em = at.nodes.new("ShaderNodeEmission"); em.inputs[0].default_value = (0.3, 0.6, 1.0, 1); em.inputs[1].default_value = 1.6
    tr = at.nodes.new("ShaderNodeBsdfTransparent"); mx = at.nodes.new("ShaderNodeMixShader")
    at.links.new(lw.outputs["Facing"], mx.inputs[0]); at.links.new(tr.outputs[0], mx.inputs[1]); at.links.new(em.outputs[0], mx.inputs[2]); at.links.new(mx.outputs[0], o2.inputs[0])
    give(atm, am)
    give(smooth(add("uv_sphere", radius=0.28, location=(2.7, 1.6, 0.9))), mat("moon", (0.55, 0.55, 0.55), 0.9))
    sun((70, 0, 70), 4.5)
    camera((0, -7.2, 0.9), (0.9, 0, 0.2), 48)
    render("space")


SCENES = {"product": product, "lowpoly": lowpoly, "clay": clay, "toon": toon, "diorama": diorama, "abstract": abstract,
          "glass": glass, "logo3d": logo3d, "medical3d": medical3d, "interior": interior, "space": space}
os.makedirs(OUT, exist_ok=True)
for sid, fn in SCENES.items():
    if ONLY and sid not in ONLY: continue
    try: fn()
    except Exception as ex:
        import traceback; traceback.print_exc(); print("FAILED", sid, ex, flush=True)

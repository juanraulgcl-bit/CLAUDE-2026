"""Modelo 3D (Blender) de los semipórticos + perfil de unión + pérgola. Exporta pergola.glb.
Uso:  blender --background --python blender_model.py -- salida.glb
Ejes Blender: x = hacia fuera de la pared, y = paralelo a la pared, z = vertical."""
import bpy, sys, math

out = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)

H, D, L1, L2, XU = 3.0, 5.85, 4.0, 5.0, 4.0
TW, TH = 0.10, 0.24            # tubo 240x100: 240 mm en el plano vertical / del pórtico

def mat(name, rgb, metal=0.0, rough=0.5):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Metallic"].default_value = metal
    b.inputs["Roughness"].default_value = rough
    return m

M_AL = mat("Aluminio", (0.62, 0.64, 0.67), 0.9, 0.35)
M_PE = mat("Pergola", (0.10, 0.11, 0.13), 0.6, 0.4)
M_WALL = mat("Pared", (0.88, 0.85, 0.80), 0.0, 0.9)
M_FLOOR = mat("Suelo", (0.55, 0.55, 0.53), 0.0, 0.95)

def box(name, c, size, material):
    bpy.ops.mesh.primitive_cube_add(size=1, location=c)
    o = bpy.context.active_object; o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(material)
    return o

# --- entorno
box("Pared", (-0.1, D/2, 2.2), (0.2, D+3.0, 4.4), M_WALL)
box("Suelo", (2.5, D/2, -0.05), (9.0, D+3.0, 0.1), M_FLOOR)

# --- semipórticos (ejes en z = H, tubo centrado en el eje)
box("Dintel_1", (L1/2, 0, H), (L1, TW, TH), M_AL)
box("Pilar_1", (L1, 0, H/2), (TH, TW, H), M_AL)
box("Dintel_2", (L2/2, D, H), (L2, TW, TH), M_AL)
box("Pilar_2", (L2, D, H/2), (TH, TW, H), M_AL)
box("Perfil_union", (XU, D/2, H), (TW, D, TH), M_AL)

# --- pérgola 5,99 x 4,07, apoyada sobre los perfiles (cara superior = H + 0,12)
z0 = H + TH/2
PX, PY0, PY1 = 4.07, -0.07, D + 0.07
BH = 0.322
box("Viga_frontal", (PX-0.125, (PY0+PY1)/2, z0+BH/2), (0.25, PY1-PY0, BH), M_PE)
box("Viga_lateral_1", (PX/2, PY0+0.125, z0+BH/2), (PX, 0.25, BH), M_PE)
box("Viga_lateral_2", (PX/2, PY1-0.125, z0+BH/2), (PX, 0.25, BH), M_PE)
box("Viga_pared", (0.06, (PY0+PY1)/2, z0+BH/2), (0.12, PY1-PY0, BH), M_PE)

N = 29
ya, yb = PY0 + 0.25, PY1 - 0.25
pitch = (yb - ya) / N
for i in range(N):
    box(f"Slat_{i:02d}", (PX/2 - 0.02, ya + pitch*(i+0.5), z0 + BH/2),
        (PX - 0.37, pitch*0.96, 0.05), M_PE)

bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", export_apply=True)
print("OK", out)

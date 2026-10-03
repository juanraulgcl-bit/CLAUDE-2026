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

# --- entorno: patio recreado a partir de las fotos (esquemático, cotas estimadas)
M_TRAV = mat("Travertino", (0.80, 0.76, 0.67), 0.0, 0.85)
M_JUNTA = mat("Junta", (0.30, 0.29, 0.27), 0.0, 1.0)
M_BALD = mat("Baldosa", (0.66, 0.65, 0.62), 0.0, 0.55)
M_BLANCO = mat("MuroBlanco", (0.93, 0.92, 0.89), 0.0, 0.9)
M_VALLA = mat("ValllaNegra", (0.06, 0.06, 0.07), 0.0, 0.9)
M_POSTE = mat("PosteGrafito", (0.13, 0.14, 0.15), 0.5, 0.5)
M_TERR = mat("Terreno", (0.40, 0.40, 0.38), 0.0, 1.0)
M_VENT = mat("Ventana", (0.10, 0.11, 0.13), 0.2, 0.3)

YA, YB, XF = -2.0, 8.5, 6.6        # límite izquierdo, límite derecho, valla del fondo
def juntar(nombre, objs, material):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    bpy.context.active_object.name = nombre
    return bpy.context.active_object

box("Terreno", (8, (YA+YB)/2, -0.08), (40, 40, 0.1), M_TERR)
box("Suelo", (XF/2, (YA+YB)/2, -0.05), (XF, YB-YA, 0.1), M_BALD)
# juntas de baldosa 60 x 60 cm
juntas = []
for i in range(int(XF/0.6)+1):
    juntas.append(box(f"jx{i}", (i*0.6, (YA+YB)/2, 0.002), (0.012, YB-YA, 0.004), M_JUNTA))
for j in range(int((YB-YA)/0.6)+1):
    juntas.append(box(f"jy{j}", (XF/2, YA+j*0.6, 0.002), (XF, 0.012, 0.004), M_JUNTA))
juntar("Juntas_suelo", juntas, M_JUNTA)

# fachada de travertino con juntas
WY0, WY1, WH = -3.0, 9.5, 6.0
box("Fachada", (-0.15, (WY0+WY1)/2, WH/2), (0.3, WY1-WY0, WH), M_TRAV)
wj = []
for r in range(int(WH/0.6)):
    wj.append(box(f"fh{r}", (0.006, (WY0+WY1)/2, (r+1)*0.6), (0.012, WY1-WY0, 0.01), M_JUNTA))
    off = 0.6 if r % 2 else 0.0
    y = WY0 + off
    while y < WY1:
        wj.append(box(f"fv{r}_{y:.1f}", (0.006, y, r*0.6+0.3), (0.012, 0.01, 0.6), M_JUNTA)); y += 1.2
juntar("Juntas_fachada", wj, M_JUNTA)

# muro blanco (lado izquierdo) y vallas negras de lamas (fondo y lado derecho)
box("Muro_blanco", (XF/2, YA-0.1, 1.1), (XF, 0.2, 2.2), M_BLANCO)
box("Valla_fondo", (XF+0.05, (YA+YB)/2, 1.0), (0.05, YB-YA, 2.0), M_VALLA)
box("Valla_derecha", (XF/2, YB+0.05, 1.0), (XF, 0.05, 2.0), M_VALLA)
postes = []
y = YA
while y <= YB + 1e-6:
    postes.append(box(f"pf{y:.1f}", (XF+0.05, y, 1.05), (0.1, 0.1, 2.1), M_POSTE)); y += 2.0
x = 0.0
while x <= XF + 1e-6:
    postes.append(box(f"pd{x:.1f}", (x, YB+0.05, 1.05), (0.1, 0.1, 2.1), M_POSTE)); x += 2.0
juntar("Postes_valla", postes, M_POSTE)

# edificios vecinos (volúmenes simples al fondo)
for k, (cx, cy, h) in enumerate([(20, -1.0, 7.0), (20, 4.0, 6.0), (20, 9.0, 7.0)]):
    box(f"Vecino_{k}", (cx, cy, h/2), (6, 4.2, h), M_BLANCO)
    for w in range(3):
        box(f"Vent_{k}_{w}", (cx-3.02, cy-1.2+w*1.2, h*0.7), (0.05, 0.7, 1.0), M_VENT)

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

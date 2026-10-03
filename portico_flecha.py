"""
Pórtico reticulado plano con apoyos empotrados - flecha vertical del dintel.

Perfil: Extrugasa ref. 1843 (tubo rectangular 240 x 100 x 4, aluminio)
Método: rigidez directa con elementos viga-columna de Euler-Bernoulli (3 gdl/nodo).

Requisitos:  pip install numpy matplotlib
"""
import numpy as np
import matplotlib.pyplot as plt

# ----------------------------------------------------------------- DATOS ---
H = 3.0                 # m  altura de pilares
L = 6.0                 # m  luz del dintel (entre ejes de pilares)
Q_SOBRECARGA = 75.0     # kg/m sobre el dintel
G = 9.81                # m/s2

# Perfil ref. 1843 (240 x 100 x 4) - catálogo Extrugasa, pág. 12
PESO_PERFIL = 7.171     # kg/m
IX_CM4 = 494.48         # cm4  (eje horizontal, lado de 240 mm horizontal)
IY_CM4 = 1946.19        # cm4  (eje vertical,   lado de 240 mm vertical)
A_MM2 = 240*100 - 232*92   # mm2 (= 2656; coherente con 7,171 kg/m a 2700 kg/m3)

# Orientación del tubo en el plano del pórtico:
#   "fuerte": cara de 240 mm en el plano del pórtico (flecta sobre Iy)
#   "debil" : cara de 100 mm en el plano del pórtico (flecta sobre Ix)
ORIENTACION = "fuerte"

E = 70000e6             # Pa  módulo elástico del aluminio (6063 / 6005A)
N_EL = 40               # elementos por barra (malla)
FACTOR_DEFORMADA = 50   # amplificación del dibujo de la deformada
# -----------------------------------------------------------------------------

I = (IY_CM4 if ORIENTACION == "fuerte" else IX_CM4) * 1e-8   # m4
A = A_MM2 * 1e-6                                              # m2
w_pp = PESO_PERFIL * G                                        # N/m peso propio
w_dintel = (PESO_PERFIL + Q_SOBRECARGA) * G                   # N/m (pp + 75 kg/m)

# ------------------------------------------------------------------ MALLA ---
def barra(p0, p1, n):
    return [(p0[0] + (p1[0]-p0[0])*i/n, p0[1] + (p1[1]-p0[1])*i/n) for i in range(n+1)]

nodos, elems, w_el = [], [], []   # w_el: (carga perpendicular local, carga axial local) N/m

def añadir(puntos, wx, wy):
    """Añade una barra; wx,wy = carga global uniforme (N/m) sobre ella."""
    i0 = len(nodos)
    nodos.extend(puntos)
    for k in range(len(puntos)-1):
        elems.append((i0+k, i0+k+1)); w_el.append((wx, wy))
    return i0, i0+len(puntos)-1

# unión de nodos coincidentes se hace después
añadir(barra((0, 0), (0, H), N_EL), 0, -w_pp)          # pilar izquierdo (pp)
añadir(barra((0, H), (L, H), 2*N_EL), 0, -w_dintel)    # dintel (pp + sobrecarga)
añadir(barra((L, 0), (L, H), N_EL), 0, -w_pp)          # pilar derecho (pp)

# fusionar nodos duplicados
uniq, mapa = [], {}
for i, (x, y) in enumerate(nodos):
    for j, (u, v) in enumerate(uniq):
        if abs(x-u) < 1e-9 and abs(y-v) < 1e-9:
            mapa[i] = j; break
    else:
        mapa[i] = len(uniq); uniq.append((x, y))
nodos = np.array(uniq)
elems = [(mapa[a], mapa[b]) for a, b in elems]
nn = len(nodos)

# --------------------------------------------------------------- ENSAMBLE ---
K = np.zeros((3*nn, 3*nn))
F = np.zeros(3*nn)

for (a, b), (wx, wy) in zip(elems, w_el):
    xa, ya = nodos[a]; xb, yb = nodos[b]
    Le = np.hypot(xb-xa, yb-ya)
    c, s = (xb-xa)/Le, (yb-ya)/Le
    EA, EI = E*A, E*I
    kl = np.array([
        [ EA/Le, 0,            0,           -EA/Le, 0,            0],
        [0,  12*EI/Le**3,  6*EI/Le**2, 0, -12*EI/Le**3,  6*EI/Le**2],
        [0,   6*EI/Le**2,  4*EI/Le,    0,  -6*EI/Le**2,  2*EI/Le],
        [-EA/Le, 0,            0,            EA/Le, 0,            0],
        [0, -12*EI/Le**3, -6*EI/Le**2, 0,  12*EI/Le**3, -6*EI/Le**2],
        [0,   6*EI/Le**2,  2*EI/Le,    0,  -6*EI/Le**2,  4*EI/Le]])
    T = np.zeros((6, 6))
    R = np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]])
    T[:3, :3] = R; T[3:, 3:] = R
    # cargas uniformes globales -> locales, cargas nodales equivalentes
    q_ax = wx*c + wy*s
    q_tr = -wx*s + wy*c
    fl = np.array([q_ax*Le/2, q_tr*Le/2, q_tr*Le**2/12,
                   q_ax*Le/2, q_tr*Le/2, -q_tr*Le**2/12])
    dof = [3*a, 3*a+1, 3*a+2, 3*b, 3*b+1, 3*b+2]
    K[np.ix_(dof, dof)] += T.T @ kl @ T
    F[dof] += T.T @ fl

# ---------------------------------------------------------- CONDICIONES ---
base = [i for i, (x, y) in enumerate(nodos) if y < 1e-9]       # empotrados
fijos = [3*i + k for i in base for k in range(3)]
libres = np.setdiff1d(np.arange(3*nn), fijos)

u = np.zeros(3*nn)
u[libres] = np.linalg.solve(K[np.ix_(libres, libres)], F[libres])
ux, uy = u[0::3], u[1::3]

# ------------------------------------------------------------- RESULTADOS ---
medio = int(np.argmin(np.hypot(nodos[:, 0]-L/2, nodos[:, 1]-H)))
f_medio = uy[medio]

# comprobación analítica (portico simétrico, bases empotradas, carga uniforme)
Kc, Kb = 4*E*I/H, 2*E*I/L
M = w_dintel*L**2/12 * Kc/(Kc+Kb)
f_teor = -(5*w_dintel*L**4/(384*E*I) - M*L**2/(8*E*I))

print(f"Perfil ref. 1843 (240x100x4), orientación {ORIENTACION}: I = {I*1e8:.2f} cm4")
print(f"Carga en dintel: {w_dintel/G:.3f} kg/m ({w_dintel:.1f} N/m)")
print(f"Flecha vertical en centro del dintel: {f_medio*1000:.3f} mm  (hacia abajo)")
print(f"Comprobación analítica (sin deformación axial): {f_teor*1000:.3f} mm")
print(f"Relación luz/flecha: L/{L/abs(f_medio):.0f}")

# ----------------------------------------------------------------- GRÁFICA ---
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 9),
                               gridspec_kw={"height_ratios": [1.3, 1]})

def trazo(mask, clave):
    idx = np.where(mask)[0]; idx = idx[np.argsort(nodos[idx, clave])]
    return idx
barras = [trazo(nodos[:, 0] < 1e-9, 1),
          trazo(np.abs(nodos[:, 1]-H) < 1e-9, 0),
          trazo(np.abs(nodos[:, 0]-L) < 1e-9, 1)]
for k, idx in enumerate(barras):
    ax1.plot(nodos[idx, 0], nodos[idx, 1], color="0.75", lw=4,
             label="Original" if k == 0 else None)
    ax1.plot(nodos[idx, 0] + FACTOR_DEFORMADA*ux[idx],
             nodos[idx, 1] + FACTOR_DEFORMADA*uy[idx], color="crimson", lw=2,
             label=f"Deformada (x{FACTOR_DEFORMADA})" if k == 0 else None)
ax1.plot(L/2 + FACTOR_DEFORMADA*ux[medio], H + FACTOR_DEFORMADA*f_medio, "ko")
ax1.annotate(f"f = {abs(f_medio)*1000:.2f} mm",
             (L/2 + FACTOR_DEFORMADA*ux[medio], H + FACTOR_DEFORMADA*f_medio),
             xytext=(10, -25), textcoords="offset points",
             arrowprops=dict(arrowstyle="->"), fontsize=11)
for xb in (0, L):
    ax1.plot([xb-0.25, xb+0.25], [0, 0], "k-", lw=3)
ax1.set_aspect("equal"); ax1.grid(alpha=.3); ax1.legend(loc="upper right")
ax1.set_title("Pórtico empotrado - perfil Extrugasa 1843 (240x100x4)")
ax1.set_xlabel("x (m)"); ax1.set_ylabel("y (m)")

d = barras[1]
ax2.plot(nodos[d, 0], uy[d]*1000, color="crimson", lw=2)
ax2.fill_between(nodos[d, 0], uy[d]*1000, 0, color="crimson", alpha=.15)
ax2.plot(L/2, f_medio*1000, "ko")
ax2.annotate(f"{f_medio*1000:.2f} mm  (L/{L/abs(f_medio):.0f})",
             (L/2, f_medio*1000), xytext=(15, 15), textcoords="offset points")
ax2.axhline(0, color="k", lw=.8); ax2.grid(alpha=.3)
ax2.set_title("Desplazamiento vertical del dintel")
ax2.set_xlabel("x (m)"); ax2.set_ylabel("uy (mm)  [- = hacia abajo]")

plt.tight_layout()
plt.show()

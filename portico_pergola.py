"""
Dos semipórticos empotrados a pared + perfil de unión que soporta una pérgola
bioclimática (Suncontrol IV Grandlux, lamas perpendiculares al muro, suspendida).

Modelo: pórtico espacial (6 gdl/nodo), vigas de Euler-Bernoulli con torsión.
Perfil: Extrugasa ref. 1843 (tubo 240x100x4) en todas las barras.

Ejes: x = hacia fuera desde la pared, y = paralelo a la pared, z = vertical.

Requisitos:  pip install numpy matplotlib
"""
import numpy as np
import matplotlib.pyplot as plt

# ================================================================ DATOS ====
G_GRAV = 9.81
H = 3.0                    # m   altura de pilares
D_PORT = 5.85              # m   distancia entre pórticos
L1, L2 = 4.0, 5.0          # m   dinteles (pórtico 1 y 2)
X_UNION = 4.0              # m   distancia a la pared del perfil de unión

# Perfil ref. 1843 (240x100x4), catálogo Extrugasa
PESO_PERFIL = 7.171                    # kg/m
IFUERTE = 1946.19e-8                   # m4  (bending con lado de 240 mm vertical)
IDEBIL = 494.48e-8                     # m4
A = (240*100 - 232*92) * 1e-6          # m2
AM = (236 * 96) * 1e-6                 # m2  área encerrada por la línea media
T_ESP = 0.004                          # m   espesor
J = 4*AM**2 / ((2*(236+96)*1e-3) / T_ESP)   # m4  torsión (Bredt)
E = 70000e6                            # Pa
NU = 0.33
GM = E / (2*(1+NU))                    # Pa
FY = 110e6                             # Pa  límite elástico 6063-T5 (CONFIRMAR aleación/temple)

# Pérgola (la ficha del fabricante NO da pesos -> ESTIMACIÓN, ajustar si se conoce)
P_LARGO, P_ANCHO = 5.99, 4.07          # m   paralelo a pared / perpendicular a pared
N_LAMAS = 29                           # lamas de 224x50 a ~198 mm de paso
L_LAMA = 4.00                          # m
KG_LAMA = 3.0                          # kg/m  lama doble pared 224x50
KG_VIGA = 9.5                          # kg/m  viga canalón 250x322
KG_ACCESORIOS = 30.0                   # kg    motor, LED, sensores, cableado
NIEVE = 90.0                           # kg/m2 carga de nieve máx. de la pérgola (ficha)

CASOS = {"Peso propio": 0.0, "Peso propio + nieve 90 kg/m2": NIEVE}
CASO_GRAFICA = "Peso propio"
FACTOR_DEF = 40                        # amplificación de la deformada
ELEM_LEN = 0.10                        # m   tamaño de malla
# ============================================================================

# ------------------------------------------------- cargas de la pérgola ----
def cargas_perfil(nieve):
    """Carga que la pérgola transmite al perfil de unión (apoyada en el muro y en el perfil)."""
    w_lamas = N_LAMAS * L_LAMA * KG_LAMA                       # kg
    w_lin = (w_lamas/2 + KG_ACCESORIOS/2) / P_LARGO + KG_VIGA  # kg/m (mitad al frente + viga frontal)
    w_lin += nieve * P_ANCHO / 2                               # kg/m
    # voladizo de 7 cm en cada extremo + mitad de cada viga lateral -> a los nudos extremos
    p_ext = w_lin*0.07 + KG_VIGA*P_ANCHO/2                     # kg por extremo
    return w_lin*G_GRAV, p_ext*G_GRAV                          # N/m , N

# ------------------------------------------------------------- geometría ----
barras = {   # nombre: (p0, p1, dirección del lado de 240 mm)
    "Dintel 1":  ((0, 0, H),       (L1, 0, H),       (0, 0, 1)),
    "Pilar 1":   ((L1, 0, 0),      (L1, 0, H),       (1, 0, 0)),
    "Dintel 2":  ((0, D_PORT, H),  (L2, D_PORT, H),  (0, 0, 1)),
    "Pilar 2":   ((L2, D_PORT, 0), (L2, D_PORT, H),  (1, 0, 0)),
    "Perfil unión": ((X_UNION, 0, H), (X_UNION, D_PORT, H), (0, 0, 1)),
}

def construir():
    nodos, idx = [], {}
    def nodo(p):
        k = tuple(np.round(p, 6))
        if k not in idx:
            idx[k] = len(nodos); nodos.append(k)
        return idx[k]
    elems = []   # (a, b, d240, barra)
    # el dintel 2 debe tener nudo en x = X_UNION
    for nom, (p0, p1, d) in barras.items():
        p0, p1 = np.array(p0, float), np.array(p1, float)
        cortes = [0.0, 1.0]
        if nom == "Dintel 2":
            cortes = [0.0, X_UNION/L2, 1.0]
        for s0, s1 in zip(cortes[:-1], cortes[1:]):
            n = max(1, int(np.ceil((s1-s0)*np.linalg.norm(p1-p0)/ELEM_LEN)))
            for i in range(n):
                a = p0 + (p1-p0)*(s0 + (s1-s0)*i/n)
                b = p0 + (p1-p0)*(s0 + (s1-s0)*(i+1)/n)
                elems.append((nodo(a), nodo(b), np.array(d, float), nom))
    return np.array(nodos), elems

def rotacion(pa, pb, d240):
    ex = (pb-pa); ex /= np.linalg.norm(ex)
    ey = d240 - ex*(d240 @ ex); ey /= np.linalg.norm(ey)   # local y = lado de 240 mm
    ez = np.cross(ex, ey)
    return np.array([ex, ey, ez])

def kloc(L):
    EA, GJ, EIz, EIy = E*A, GM*J, E*IFUERTE, E*IDEBIL
    k = np.zeros((12, 12))
    k[np.ix_([0, 6], [0, 6])] = EA/L*np.array([[1, -1], [-1, 1]])
    k[np.ix_([3, 9], [3, 9])] = GJ/L*np.array([[1, -1], [-1, 1]])
    # flexión en plano x-y (v, thz): gdl 1,5,7,11
    kz = EIz/L**3*np.array([[12, 6*L, -12, 6*L], [6*L, 4*L**2, -6*L, 2*L**2],
                            [-12, -6*L, 12, -6*L], [6*L, 2*L**2, -6*L, 4*L**2]])
    k[np.ix_([1, 5, 7, 11], [1, 5, 7, 11])] = kz
    # flexión en plano x-z (w, thy): gdl 2,4,8,10
    ky = EIy/L**3*np.array([[12, -6*L, -12, -6*L], [-6*L, 4*L**2, 6*L, 2*L**2],
                            [-12, 6*L, 12, 6*L], [-6*L, 2*L**2, 6*L, 4*L**2]])
    k[np.ix_([2, 4, 8, 10], [2, 4, 8, 10])] = ky
    return k

def carga_local(q, L):
    """Vector de empotramiento perfecto (fuerzas aplicadas) para carga uniforme local q=(qx,qy,qz)."""
    qx, qy, qz = q
    return np.array([qx*L/2, qy*L/2, qz*L/2, 0, -qz*L**2/12, qy*L**2/12,
                     qx*L/2, qy*L/2, qz*L/2, 0,  qz*L**2/12, -qy*L**2/12])

# ------------------------------------------------------------------ cálculo --
def resolver(nieve):
    nodos, elems = construir()
    nn = len(nodos)
    w_perg, p_ext = cargas_perfil(nieve)
    w_pp = PESO_PERFIL*G_GRAV
    K = np.zeros((6*nn, 6*nn)); F = np.zeros(6*nn)
    datos = []
    for a, b, d, nom in elems:
        pa, pb = nodos[a], nodos[b]
        L = np.linalg.norm(pb-pa)
        R = rotacion(pa, pb, d)
        T = np.kron(np.eye(4), R)
        w = w_pp + (w_perg if nom == "Perfil unión" else 0.0)
        ql = R @ np.array([0, 0, -w])
        fl = carga_local(ql, L)
        k = kloc(L)
        dof = np.r_[6*a:6*a+6, 6*b:6*b+6]
        K[np.ix_(dof, dof)] += T.T @ k @ T
        F[dof] += T.T @ fl
        datos.append((a, b, nom, T, k, fl, dof, L))
    # cargas puntuales en los extremos del perfil de unión
    for y in (0.0, D_PORT):
        i = int(np.argmin(np.linalg.norm(nodos - np.array([X_UNION, y, H]), axis=1)))
        F[6*i+2] -= p_ext
    # empotramientos: pared (x=0) y bases (z=0)
    fijos = [6*i+k for i, p in enumerate(nodos) if p[0] < 1e-9 or p[2] < 1e-9 for k in range(6)]
    libres = np.setdiff1d(np.arange(6*nn), fijos)
    u = np.zeros(6*nn)
    u[libres] = np.linalg.solve(K[np.ix_(libres, libres)], F[libres])

    # esfuerzos en extremos de cada elemento y tensiones
    res = []
    for a, b, nom, T, k, fl, dof, L in datos:
        f = k @ (T @ u[dof]) - fl            # fuerzas del nudo sobre el elemento (locales)
        for extremo, o in ((0, 0), (1, 6)):
            N, Vy, Vz, Tq, My, Mz = f[o:o+6]
            sig = abs(N)/A + abs(Mz)*0.120/IFUERTE + abs(My)*0.050/IDEBIL
            tau = abs(Tq)/(2*AM*T_ESP) + np.hypot(Vy, Vz)/(2*0.236*T_ESP)
            vm = np.sqrt(sig**2 + 3*tau**2)
            res.append(dict(nom=nom, nodo=(a, b)[extremo], N=N, Vy=Vy, Vz=Vz, T=Tq,
                            My=My, Mz=Mz, sig=sig, tau=tau, vm=vm))
    return nodos, elems, u, res, (w_perg, p_ext)

# --------------------------------------------------------------- resultados --
def informe(nombre, nieve):
    nodos, elems, u, res, (w_perg, p_ext) = resolver(nieve)
    prof = [i for i, p in enumerate(nodos) if abs(p[0]-X_UNION) < 1e-6 and abs(p[2]-H) < 1e-6]
    prof.sort(key=lambda i: nodos[i][1])
    uz = u[6*np.array(prof)+2]
    imax = int(np.argmin(uz))
    crit = max(res, key=lambda r: r['vm'])
    pc = nodos[crit['nodo']]
    print(f"\n=== {nombre} ===")
    print(f"Carga sobre perfil de unión: {w_perg/G_GRAV:.1f} kg/m (+ puntual extremos {p_ext/G_GRAV:.1f} kg)")
    print(f"Flecha vertical máx. del perfil de unión: {uz[imax]*1000:.2f} mm "
          f"en y = {nodos[prof[imax]][1]:.2f} m  (L/{D_PORT/abs(uz[imax]):.0f}, luz entre pórticos)")
    print(f"Sección más crítica: {crit['nom']} en (x={pc[0]:.2f}, y={pc[1]:.2f}, z={pc[2]:.2f}) m")
    print(f"   N={crit['N']/1e3:.2f} kN  Vy={crit['Vy']/1e3:.2f} kN  Vz={crit['Vz']/1e3:.2f} kN  "
          f"T={crit['T']:.0f} N·m  Mz(fuerte)={crit['Mz']:.0f} N·m  My(débil)={crit['My']:.0f} N·m")
    print(f"   Tensión normal máx. = {crit['sig']/1e6:.1f} MPa,  cortante+torsión = {crit['tau']/1e6:.1f} MPa,"
          f"  von Mises = {crit['vm']/1e6:.1f} MPa  ({crit['vm']/FY*100:.0f}% de fy = {FY/1e6:.0f} MPa)")
    return nodos, elems, u, res, prof, uz, crit

if __name__ == "__main__":
    print(f"Perfil 1843: A={A*1e4:.2f} cm2, I fuerte={IFUERTE*1e8:.1f} cm4, J={J*1e8:.0f} cm4")
    out = {n: informe(n, v) for n, v in CASOS.items()}

    nodos, elems, u, res, prof, uz, crit = out[CASO_GRAFICA]
    # tensión von Mises máxima por nodo (para colorear)
    vm_nodo = np.zeros(len(nodos))
    for r in res:
        vm_nodo[r['nodo']] = max(vm_nodo[r['nodo']], r['vm'])

    fig = plt.figure(figsize=(13, 6))
    ax = fig.add_subplot(1, 2, 1, projection="3d")
    for a, b, d, nom in elems:
        ax.plot(*zip(nodos[a], nodos[b]), color="0.8", lw=3)
    dp = nodos + FACTOR_DEF*u.reshape(-1, 6)[:, :3]
    sc = None
    for a, b, d, nom in elems:
        c = plt.cm.jet(min(1, 0.5*(vm_nodo[a]+vm_nodo[b])/FY))
        ax.plot(*zip(dp[a], dp[b]), color=c, lw=2)
    ax.plot([dp[prof[len(prof)//2]][0]], [dp[prof[len(prof)//2]][1]], [dp[prof[len(prof)//2]][2]], "ko")
    pc = nodos[crit['nodo']]
    ax.scatter(*pc, color="magenta", s=80, marker="X", label="Sección crítica")
    ax.set_xlabel("x (m, hacia fuera)"); ax.set_ylabel("y (m)"); ax.set_zlabel("z (m)")
    ax.set_box_aspect((5, 6, 3)); ax.legend()
    ax.set_title(f"Deformada x{FACTOR_DEF} (color = von Mises, rojo = fy)\n{CASO_GRAFICA}")

    ax2 = fig.add_subplot(1, 2, 2)
    y = nodos[prof, 1]
    for n, (_, _, _, _, p, uzz, _) in out.items():
        ax2.plot(nodos[p, 1], uzz*1000, lw=2, label=n)
    ax2.axhline(0, color="k", lw=.8); ax2.grid(alpha=.3); ax2.legend()
    ax2.set_xlabel("y a lo largo del perfil de unión (m)"); ax2.set_ylabel("uz (mm)  [- = hacia abajo]")
    ax2.set_title("Desplazamiento vertical del perfil de unión")
    plt.tight_layout(); plt.show()

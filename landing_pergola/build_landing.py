"""Genera index.html (autocontenido): modelo GLB de Blender + resultados del cálculo."""
import sys, json, base64, pathlib
here = pathlib.Path(__file__).parent
sys.path.insert(0, str(here.parent))
import portico_pergola as pp
import numpy as np

casos = {}
for key, (nombre, nieve) in {"pp": ("Peso propio", 0.0), "nieve": ("Peso propio + nieve 90 kg/m²", pp.NIEVE)}.items():
    nodos, elems, u, res, (w, pext) = pp.resolver(nieve)
    U = u.reshape(-1, 6)[:, :3]
    vm = np.zeros(len(nodos))
    for r in res:
        vm[r['nodo']] = max(vm[r['nodo']], r['vm'])
    prof = sorted([i for i, p in enumerate(nodos) if abs(p[0]-pp.X_UNION) < 1e-6 and abs(p[2]-pp.H) < 1e-6],
                  key=lambda i: nodos[i][1])
    uz = U[prof, 2]; im = int(np.argmin(uz))
    crit = max(res, key=lambda r: r['vm'])
    casos[key] = dict(
        nombre=nombre, w=w/pp.G_GRAV, pext=pext/pp.G_GRAV,
        U=np.round(U, 7).tolist(), vm=np.round(vm/1e6, 3).tolist(),
        flecha=float(uz[im])*1000, y_flecha=float(nodos[prof[im]][1]),
        luz_ratio=float(pp.D_PORT/abs(uz[im])),
        crit=dict(barra=crit['nom'], pos=[float(c) for c in nodos[crit['nodo']]],
                  M=float(abs(crit['Mz'])), sig=crit['sig']/1e6, tau=crit['tau']/1e6, vm=crit['vm']/1e6, N=crit['N']),
        perfil=[[float(nodos[i][1]), float(U[i][2]*1000)] for i in prof])

data = dict(nodos=np.round(nodos, 4).tolist(),
            elems=[[int(a), int(b)] for a, b, d, n in elems],
            casos=casos, fy=pp.FY/1e6, H=pp.H, D=pp.D_PORT)
glb = base64.b64encode((here/"pergola.glb").read_bytes()).decode()
html = (here/"template.html").read_text(encoding="utf-8")
html = html.replace("__DATA__", json.dumps(data)).replace("__GLB__", glb)
(here/"index.html").write_text(html, encoding="utf-8")
print("index.html", len(html)//1024, "KB")

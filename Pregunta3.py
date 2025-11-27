import gurobipy as gp
from gurobipy import GRB


# --- 1. DATOS ---
Origenes = ['Lisboa', 'Madrid', 'Turin']
Destinos = ['Paris', 'Berlin', 'Varsovia']

Oferta = {'Lisboa': 5, 'Madrid': 6, 'Turin': 7}
Demanda = {'Paris': 4, 'Berlin': 5, 'Varsovia': 9}

# Costes en céntimos (igual que en Pregunta1)
costes_raw = {
    ('Lisboa', 'Paris'): 4, ('Lisboa', 'Berlin'): 3, ('Lisboa', 'Varsovia'): 6,
    ('Madrid', 'Paris'): 7, ('Madrid', 'Berlin'): 4, ('Madrid', 'Varsovia'): 9,
    ('Turin', 'Paris'): 9,  ('Turin', 'Berlin'): 5,  ('Turin', 'Varsovia'): 2
}

# Convertir a Euros
C = {k: v / 100.0 for k, v in costes_raw.items()}

# Parámetros operativos (mantener coherencia)
Capacidad_Canal = 10
Coste_Base_Canal = 50.0
Coste_Extra_Canal = 65.0
Max_Canales_Base = 4

# Máximo canales que permitimos por par (cota razonable)
MaxCanalesPorPar = Max_Canales_Base + 1

# Coste fijo por activar un centro de almacenamiento (nuevo)
Coste_Activacion_Almacen = 5000.0

# --- 2. MODELADO ---
m = gp.Model("Pregunta3_Extension2")

# Variables
x = m.addVars(Origenes, Destinos, vtype=GRB.CONTINUOUS, name="x")
y = m.addVars(Origenes, Destinos, vtype=GRB.INTEGER, lb=0, name="y")
u = m.addVars(Origenes, Destinos, vtype=GRB.BINARY, name="u")
z = m.addVar(vtype=GRB.BINARY, name="z_extra")

# s[i] = 1 si el centro de origen i está activado (envía datos)
s = m.addVars(Origenes, vtype=GRB.BINARY, name="s_origen")

# Restricciones
# 1. Oferta
m.addConstrs((x.sum(i, '*') == Oferta[i] for i in Origenes), name="Oferta")

# 2. Demanda
m.addConstrs((x.sum('*', j) == Demanda[j] for j in Destinos), name="Demanda")

# 3. Capacidad vinculada: cada canal aporta 10 MilGb de capacidad
m.addConstrs((x[i, j] <= Capacidad_Canal * y[i, j] for i in Origenes for j in Destinos), name="Capacidad")

# 4. Límite de canales totales
m.addConstr(y.sum() <= Max_Canales_Base + z, name="TotalCanales")

# 5. Enlace entre y y u (activación por par)
m.addConstrs((y[i, j] <= MaxCanalesPorPar * u[i, j] for i in Origenes for j in Destinos), name="Link_y_u_up")
m.addConstrs((y[i, j] >= u[i, j] for i in Origenes for j in Destinos), name="Link_y_u_low")

# 6. Privacidad Berlín
m.addConstr(u['Lisboa', 'Berlin'] + u['Madrid', 'Berlin'] <= 1, name="Privacidad_Berlin")

# 7. Enlace entre s (origen activado) y y
MaxChannelsPerOrigin = MaxCanalesPorPar * len(Destinos)
m.addConstrs((y.sum(i, '*') <= MaxChannelsPerOrigin * s[i] for i in Origenes), name="Link_s_up")
m.addConstrs((y.sum(i, '*') >= s[i] for i in Origenes), name="Link_s_low")


# Función Objetivo
coste_variable = x.prod(C)
coste_fijo_canales = (Coste_Base_Canal * y.sum()) + ((Coste_Extra_Canal - Coste_Base_Canal) * z)
coste_activacion_origenes = Coste_Activacion_Almacen * s.sum()

m.setObjective(coste_variable + coste_fijo_canales + coste_activacion_origenes, GRB.MINIMIZE)

# --- 3. RESOLUCIÓN ---
m.optimize()

# --- 4. RESULTADOS ---
print("\n" + "="*70)
print(f" REPORTE DE SOLUCIÓN - PREGUNTA 3 (Extensión 2)")
print("="*70)

if m.status == GRB.OPTIMAL:
    print(f"Coste Total Mínimo: {m.ObjVal:.2f} €")
    print("-" * 50)
    print("1. Flujos de Datos (x_ij):")
    for i in Origenes:
        for j in Destinos:
            if x[i, j].X > 1e-6:
                print(f"   * {i} -> {j}: {x[i, j].X:.2f} MilGb")

    print("\n2. Canales asignados por par (y_ij):")
    total_canales = 0
    for i in Origenes:
        for j in Destinos:
            if y[i, j].X >= 0.5:
                print(f"   * {i} - {j}: {int(round(y[i,j].X))} canal(es)")
                total_canales += int(round(y[i,j].X))
    print(f"\n   Total canales usados: {total_canales}")

    print("\n3. Centros origen activados (s_i):")
    for i in Origenes:
        if s[i].X > 0.5:
            print(f"   * [ON] Origen {i} (coste activación {Coste_Activacion_Almacen:.2f} €)")

    print("\n4. Pairs activados (u_ij):")
    for i in Origenes:
        for j in Destinos:
            if u[i, j].X > 0.5:
                print(f"   * [ON] Par {i}-{j}")

    print("\n5. Uso de Canal Extra (z):")
    if z.X > 0.5:
        print("   * SÍ se ha alquilado el canal adicional (+15€).")
    else:
        print("   * NO se ha alquilado el canal adicional (Solo base).")

    print("-" * 50)
else:
    print("No se encontró solución óptima.")

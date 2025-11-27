import gurobipy as gp
from gurobipy import GRB


# --- 1. DATOS (mismos que Pregunta1) ---
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

# Parámetros operativos (mantener coherencia con Pregunta1)
Capacidad_Canal = 10
Coste_Base_Canal = 50.0
Coste_Extra_Canal = 65.0
Max_Canales_Base = 4

# Máximo canales que permitimos por par (cota razonable)
MaxCanalesPorPar = Max_Canales_Base + 1

# --- 2. MODELADO ---
m = gp.Model("Pregunta2_Extension1")

# Variables
x = m.addVars(Origenes, Destinos, vtype=GRB.CONTINUOUS, name="x")
y = m.addVars(Origenes, Destinos, vtype=GRB.INTEGER, lb=0, name="y")
u = m.addVars(Origenes, Destinos, vtype=GRB.BINARY, name="u")
z = m.addVar(vtype=GRB.BINARY, name="z_extra")

# Restricciones
# 1. Oferta
m.addConstrs((x.sum(i, '*') == Oferta[i] for i in Origenes), name="Oferta")

# 2. Demanda
m.addConstrs((x.sum('*', j) == Demanda[j] for j in Destinos), name="Demanda")

# 3. Capacidad vinculada: cada canal aporta 10 MilGb de capacidad
m.addConstrs((x[i, j] <= Capacidad_Canal * y[i, j] for i in Origenes for j in Destinos), name="Capacidad")

# 4. Límite de canales totales (suma de canales usados <= canales base + posible extra)
m.addConstr(y.sum() <= Max_Canales_Base + z, name="TotalCanales")

# 5. Enlace entre y (cantidad de canales) y u (activación binaria por par):
m.addConstrs((y[i, j] <= MaxCanalesPorPar * u[i, j] for i in Origenes for j in Destinos), name="Link_y_u_up")
m.addConstrs((y[i, j] >= u[i, j] for i in Origenes for j in Destinos), name="Link_y_u_low")

# 6. Privacidad Berlín: Lisboa y Madrid no pueden enviar simultáneamente a Berlín
m.addConstr(u['Lisboa', 'Berlin'] + u['Madrid', 'Berlin'] <= 1, name="Privacidad_Berlin")

# Función Objetivo

# Coste variable por flujo
coste_variable = x.prod(C)
# Coste fijo: 50€ por cada canal usado; si se alquila el canal extra (z=1)
# añadimos +15€ una única vez, de forma que el canal extra cuesta 65€ en total.
coste_fijo = (Coste_Base_Canal * y.sum()) + ((Coste_Extra_Canal - Coste_Base_Canal) * z)

m.setObjective(coste_variable + coste_fijo, GRB.MINIMIZE)

# --- 3. RESOLUCIÓN ---
m.optimize()

# --- 4. RESULTADOS ---
print("\n" + "="*60)
print(f" REPORTE DE SOLUCIÓN - PREGUNTA 2 (Extensión 1)")
print("="*60)

if m.status == GRB.OPTIMAL:
    print(f"Coste Total Mínimo: {m.ObjVal:.2f} €")
    print("-" * 40)
    print("1. Flujos de Datos (x_ij):")
    hay_flujo = False
    for i in Origenes:
        for j in Destinos:
            if x[i, j].X > 1e-6:
                print(f"   * {i} -> {j}: {x[i, j].X:.2f} MilGb")
                hay_flujo = True
    if not hay_flujo:
        print("   (No hay flujo asignado)")

    print("\n2. Canales asignados por par (y_ij):")
    total_canales = 0
    for i in Origenes:
        for j in Destinos:
            if y[i, j].X >= 0.5:
                print(f"   * {i} - {j}: {int(round(y[i,j].X))} canal(es)")
                total_canales += int(round(y[i,j].X))

    print(f"\n   Total canales usados: {total_canales}")

    print("\n3. Pairs activados (u_ij):")
    for i in Origenes:
        for j in Destinos:
            if u[i, j].X > 0.5:
                print(f"   * [ON] Par {i}-{j}")

    print("\n4. Uso de Canal Extra (z):")
    if z.X > 0.5:
        print("   * SÍ se ha alquilado el canal adicional (+15€).")
    else:
        print("   * NO se ha alquilado el canal adicional (Solo base).")

    print("-" * 40)
else:
    print("No se encontró solución óptima.")

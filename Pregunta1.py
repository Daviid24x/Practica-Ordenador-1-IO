import gurobipy as gp
from gurobipy import GRB

# --- 1. DATOS ---
Origenes = ['Lisboa', 'Madrid', 'Turin']
Destinos = ['Paris', 'Berlin', 'Varsovia']

Oferta = {'Lisboa': 5, 'Madrid': 6, 'Turin': 7}
Demanda = {'Paris': 4, 'Berlin': 5, 'Varsovia': 9}

# Costes en céntimos
costes_raw = {
    ('Lisboa', 'Paris'): 4, ('Lisboa', 'Berlin'): 3, ('Lisboa', 'Varsovia'): 6,
    ('Madrid', 'Paris'): 7, ('Madrid', 'Berlin'): 4, ('Madrid', 'Varsovia'): 9,
    ('Turin', 'Paris'): 9,  ('Turin', 'Berlin'): 5,  ('Turin', 'Varsovia'): 2
}

# Convertir a Euros
C = {k: v / 100.0 for k, v in costes_raw.items()}

# Parámetros operativos
Capacidad_Canal = 10
Coste_Base_Canal = 50.0
Coste_Extra_Canal = 65.0
Max_Canales_Base = 4

# --- 2. MODELADO ---
m = gp.Model("Pregunta1_ModeloBase")

# Variables
x = m.addVars(Origenes, Destinos, vtype=GRB.CONTINUOUS, name="x") # Flujo
y = m.addVars(Origenes, Destinos, vtype=GRB.BINARY, name="y")     # Activación canal
z = m.addVar(vtype=GRB.BINARY, name="z_extra")                    # Canal extra

# Restricciones
# 1. Oferta
m.addConstrs((x.sum(i, '*') == Oferta[i] for i in Origenes), name="Oferta")

# 2. Demanda
m.addConstrs((x.sum('*', j) == Demanda[j] for j in Destinos), name="Demanda")

# 3. Capacidad y Vinculación
m.addConstrs((x[i, j] <= Capacidad_Canal * y[i, j] for i in Origenes for j in Destinos), name="Capacidad")

# 4. Límite de Canales
m.addConstr(y.sum() <= Max_Canales_Base + z, name="TotalCanales")

# 5. Privacidad Berlín
m.addConstr(y['Lisboa', 'Berlin'] + y['Madrid', 'Berlin'] <= 1, name="Privacidad_Berlin")

# Función Objetivo
coste_variable = x.prod(C)
coste_fijo = (Coste_Base_Canal * y.sum()) + ((Coste_Extra_Canal - Coste_Base_Canal) * z)

m.setObjective(coste_variable + coste_fijo, GRB.MINIMIZE)

# --- 3. RESOLUCIÓN ---
m.optimize()

# --- 4. RESULTADOS ---
print("\n" + "="*50)
print(f" REPORTE DE SOLUCIÓN - PREGUNTA 1")
print("="*50)

if m.status == GRB.OPTIMAL:
    print(f"Coste Total Mínimo: {m.ObjVal:.2f} €")
    print("-" * 30)
    
    print("1. Flujos de Datos (x_ij):")
    hay_flujo = False
    for i in Origenes:
        for j in Destinos:
            if x[i, j].X > 1e-6:
                print(f"   * {i} -> {j}: {x[i, j].X:.2f} MilGb")
                hay_flujo = True
    if not hay_flujo: print("   (No hay flujo asignado)")

    print("\n2. Canales Activados (y_ij):")
    total_canales = 0
    for i in Origenes:
        for j in Destinos:
            if y[i, j].X > 0.5:
                print(f"   * [ON] Canal {i}-{j}")
                total_canales += 1
    
    print(f"\n   Total canales usados: {total_canales}")
    
    print("\n3. Uso de Canal Extra (z):")
    if z.X > 0.5:
        print("   * SÍ se ha alquilado el canal adicional (+15€).")
    else:
        print("   * NO se ha alquilado el canal adicional (Solo base).")
        
    print("-" * 30)
else:
    print("No se encontró solución óptima.")
import gurobipy as gp
from gurobipy import GRB

# --- 1. DATOS ---
Origenes = ['Lisboa', 'Madrid', 'Turin']
Destinos = ['Paris', 'Berlin', 'Varsovia']
Transbordo = ['Zurich']

Oferta = {'Lisboa': 5, 'Madrid': 6, 'Turin': 7}
Demanda = {'Paris': 4, 'Berlin': 5, 'Varsovia': 9}

# Costes en céntimos para arcos directos Origen->Destino (igual que antes)
costes_raw = {
	('Lisboa', 'Paris'): 4, ('Lisboa', 'Berlin'): 3, ('Lisboa', 'Varsovia'): 6,
	('Madrid', 'Paris'): 7, ('Madrid', 'Berlin'): 4, ('Madrid', 'Varsovia'): 9,
	('Turin', 'Paris'): 9,  ('Turin', 'Berlin'): 5,  ('Turin', 'Varsovia'): 2
}

# Convertir a Euros para arcos directos
C_direct = {k: v / 100.0 for k, v in costes_raw.items()}

# Coste variable para arcos que incluyen Zurich: 5 céntimos = 0.05 €
Coste_Zurich = 0.05

# Parámetros operativos
Capacidad_Canal = 10
Coste_Base_Canal = 50.0
Coste_Extra_Canal = 65.0
Max_Canales_Base = 4

# Máximo canales que permitimos por par (cota razonable)
MaxCanalesPorPar = Max_Canales_Base + 1

# Coste fijo por activar un centro de almacenamiento (pregunta 3)
Coste_Activacion_Almacen = 5000.0

# --- 2. MODELADO ---
m = gp.Model("Pregunta4_Extension3")

# Definir todos los arcos: Origen->Destino, Origen->Zurich, Zurich->Destino
arcos_OD = [(i, j) for i in Origenes for j in Destinos]
arcos_OZ = [(i, 'Zurich') for i in Origenes]
arcos_ZD = [('Zurich', j) for j in Destinos]
arcos = arcos_OD + arcos_OZ + arcos_ZD

# Variables de flujo y canales/activación sobre todos los arcos
x = m.addVars(arcos, vtype=GRB.CONTINUOUS, name="x")
y = m.addVars(arcos, vtype=GRB.INTEGER, lb=0, name="y")
u = m.addVars(arcos, vtype=GRB.BINARY, name="u")
z = m.addVar(vtype=GRB.BINARY, name="z_extra")

# s[i] = 1 si el centro de origen i está activado (envía datos)
s = m.addVars(Origenes, vtype=GRB.BINARY, name="s_origen")

# --- Costes por arco: combinar costes directos y costes Zurich
C = {}
for arc in arcos:
	if arc in C_direct:
		C[arc] = C_direct[arc]
	else:
		# arcos que involucran Zurich usan coste fijo 0.05 € / MilGb
		C[arc] = Coste_Zurich

# Restricciones
# 1. Oferta: origenes pueden enviar directamente a destinos o a Zurich
m.addConstrs((x.sum(i, '*') == Oferta[i] for i in Origenes), name="Oferta")

# 2. Demanda: destinos reciben flujo directo desde orígenes y desde Zurich
m.addConstrs((x.sum('*', j) == Demanda[j] for j in Destinos), name="Demanda")

# 3. Balance en Zurich: entrada = salida
m.addConstr(gp.quicksum(x[i, 'Zurich'] for i in Origenes) == gp.quicksum(x['Zurich', j] for j in Destinos), name="Balance_Zurich")

# 4. Capacidad vinculada: cada canal aporta 10 MilGb de capacidad en todos los arcos
m.addConstrs((x[arc] <= Capacidad_Canal * y[arc] for arc in arcos), name="Capacidad")

# 5. Límite de canales totales (suma de canales usados <= canales base + posible extra)
m.addConstr(y.sum() <= Max_Canales_Base + z, name="TotalCanales")

# 6. Enlace entre y (cantidad de canales) y u (activación binaria por arco)
m.addConstrs((y[arc] <= MaxCanalesPorPar * u[arc] for arc in arcos), name="Link_y_u_up")
m.addConstrs((y[arc] >= u[arc] for arc in arcos), name="Link_y_u_low")

# 7. Privacidad Berlín: Lisboa y Madrid no pueden enviar simultáneamente a Berlín (sobre activaciones u)
m.addConstr(u['Lisboa', 'Berlin'] + u['Madrid', 'Berlin'] <= 1, name="Privacidad_Berlin")

# 8. Enlace entre s (origen activado) e y
MaxChannelsPerOrigin = MaxCanalesPorPar * len(Destinos)
m.addConstrs((y.sum(i, '*') <= MaxChannelsPerOrigin * s[i] for i in Origenes), name="Link_s_up")
m.addConstrs((y.sum(i, '*') >= s[i] for i in Origenes), name="Link_s_low")

# 9. Condición adicional: si el canal Zurich->Paris está activado, debe transportar al menos 0.5 MilGb
#    vinculamos mediante x['Zurich','Paris'] >= 0.5 * u['Zurich','Paris']
m.addConstr(x['Zurich', 'Paris'] >= 0.5 * u['Zurich', 'Paris'], name="Min_Zurich_Paris")

# Función Objetivo
coste_variable = x.prod(C)
coste_fijo_canales = (Coste_Base_Canal * y.sum()) + ((Coste_Extra_Canal - Coste_Base_Canal) * z)
coste_activacion_origenes = Coste_Activacion_Almacen * s.sum()

m.setObjective(coste_variable + coste_fijo_canales + coste_activacion_origenes, GRB.MINIMIZE)

# --- 3. RESOLUCIÓN ---
m.optimize()

# --- 4. RESULTADOS ---
print("\n" + "="*80)
print(f" REPORTE DE SOLUCIÓN - PREGUNTA 4 (Extensión 3)")
print("="*80)

if m.status == GRB.OPTIMAL:
	print(f"Coste Total Mínimo: {m.ObjVal:.2f} €")
	print("-" * 60)
	print("1. Flujos directos Origen->Destino (x_od):")
	for i in Origenes:
		for j in Destinos:
			if x[i, j].X > 1e-6:
				print(f"   * {i} -> {j}: {x[i, j].X:.2f} MilGb")

	print("\n2. Flujos via Zurich (Origen->Zurich and Zurich->Destino):")
	for i in Origenes:
		if x[i, 'Zurich'].X > 1e-6:
			print(f"   * {i} -> Zurich: {x[i, 'Zurich'].X:.2f} MilGb")
	for j in Destinos:
		if x['Zurich', j].X > 1e-6:
			print(f"   * Zurich -> {j}: {x['Zurich', j].X:.2f} MilGb")

	print("\n3. Canales asignados por arco (y_ij):")
	total_canales = 0
	for arc in arcos:
		if y[arc].X >= 0.5:
			print(f"   * {arc[0]} - {arc[1]}: {int(round(y[arc].X))} canal(es)")
			total_canales += int(round(y[arc].X))
	print(f"\n   Total canales usados: {total_canales}")

	print("\n4. Centros origen activados (s_i):")
	for i in Origenes:
		if s[i].X > 0.5:
			print(f"   * [ON] Origen {i} (coste activación {Coste_Activacion_Almacen:.2f} €)")

	print("\n5. Pairs activados (u_ij):")
	for arc in arcos:
		if u[arc].X > 0.5:
			print(f"   * [ON] Par {arc[0]}-{arc[1]}")

	print("\n6. Uso de Canal Extra (z):")
	if z.X > 0.5:
		print("   * SÍ se ha alquilado el canal adicional (+15€).")
	else:
		print("   * NO se ha alquilado el canal adicional (Solo base).")

	print("-" * 60)
else:
	print("No se encontró solución óptima.")


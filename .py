import re


# -----1. ESTRUCTURAS DE DATOS Y ÁRBOL SINTÁCTICO (WFF)----

class Atom:
    def __init__(self, nombre, texto):
        self.nombre = nombre  # Letra (p, q, r...)
        self.texto = texto    # Significado ("es de día")
    def __str__(self): return self.nombre
    def __repr__(self): return self.nombre
    def __eq__(self, o): return isinstance(o, Atom) and self.nombre == o.nombre
    def __hash__(self): return hash(self.nombre)

class Not:
    def __init__(self, sub): self.sub = sub
    def __str__(self): return f"¬{self.sub}" if isinstance(self.sub, Atom) else f"¬({self.sub})"
    def __repr__(self): return str(self)
    def __eq__(self, o): return isinstance(o, Not) and self.sub == o.sub
    def __hash__(self): return hash(('Not', self.sub))

class BinaryOp:
    def __init__(self, izq, der, sim): self.izq, self.der, self.sim = izq, der, sim
    def __str__(self): return f"({self.izq} {self.sim} {self.der})"
    def __repr__(self): return str(self)
    def __eq__(self, o): return type(o) == type(self) and self.izq == o.izq and self.der == o.der
    def __hash__(self): return hash((type(self), self.izq, self.der))

class And(BinaryOp):
    def __init__(self, i, d): super().__init__(i, d, "∧")
class Or(BinaryOp):
    def __init__(self, i, d): super().__init__(i, d, "∨")
class Imp(BinaryOp):
    def __init__(self, i, d): super().__init__(i, d, "→")
class Iff(BinaryOp):
    def __init__(self, i, d): super().__init__(i, d, "↔")


# 2. PARSER DE LENGUAJE NATURAL

LETRAS = ['p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']

class ParserNL:
    def __init__(self):
        self.texto_a_atomo = {}
        self.atomo_a_texto = {}
        self.idx = 0

    def _obtener_atomo(self, texto):
        if texto not in self.texto_a_atomo:
            letra = LETRAS[self.idx % len(LETRAS)] + (str(self.idx // len(LETRAS)) if self.idx >= len(LETRAS) else "")
            self.idx += 1
            atomo = Atom(letra, texto)
            self.texto_a_atomo[texto] = atomo
            self.atomo_a_texto[letra] = texto
        return self.texto_a_atomo[texto]

    def parsear(self, texto):
        t = re.sub(r'[.,;!¡?¿]', '', texto.lower().strip())
        t = re.sub(r'\s+', ' ', t)

        if t.startswith('no es cierto que '):
            return Not(self.parsear(t[17:]))
        if ' si y solo si ' in t:
            i, d = t.split(' si y solo si ', 1)
            return Iff(self.parsear(i), self.parsear(d))
        m = re.match(r'^si\s+(.+?)\s+entonces\s+(.+)$', t)
        if m:
            return Imp(self.parsear(m.group(1)), self.parsear(m.group(2)))
        if ' o ' in t:
            i, d = t.split(' o ', 1)
            return Or(self.parsear(i), self.parsear(d))
        if ' y ' in t:
            i, d = t.split(' y ', 1)
            return And(self.parsear(i), self.parsear(d))
        if t.startswith('no '):
            return Not(self._obtener_atomo(t[3:].strip()))
        return self._obtener_atomo(t)

# ==============================================================================
# 3. REGLAS DE EXPANSIÓN Y MOTOR TABLEAU
# ==============================================================================

def es_literal(f):
    return isinstance(f, Atom) or (isinstance(f, Not) and isinstance(f.sub, Atom))

def obtener_regla(f):
    # Alfa: una sola rama | Beta: bifurcación
    if isinstance(f, Not) and isinstance(f.sub, Not): return ('ALPHA', [f.sub.sub])
    if isinstance(f, And): return ('ALPHA', [f.izq, f.der])
    if isinstance(f, Not) and isinstance(f.sub, Or): return ('ALPHA', [Not(f.sub.izq), Not(f.sub.der)])
    if isinstance(f, Not) and isinstance(f.sub, Imp): return ('ALPHA', [f.sub.izq, Not(f.sub.der)])

    if isinstance(f, Or): return ('BETA', [[f.izq], [f.der]])
    if isinstance(f, Imp): return ('BETA', [[Not(f.izq)], [f.der]])
    if isinstance(f, Not) and isinstance(f.sub, And): return ('BETA', [[Not(f.sub.izq)], [Not(f.sub.der)]])
    if isinstance(f, Iff): return ('BETA', [[f.izq, f.der], [Not(f.izq), Not(f.der)]])
    if isinstance(f, Not) and isinstance(f.sub, Iff): return ('BETA', [[f.sub.izq, Not(f.sub.der)], [Not(f.sub.izq), f.sub.der]])
    return None

class NodoTableau:
    def __init__(self, formulas_nuevas, formulas_rama=None, aplicadas=None):
        self.formulas = list(formulas_nuevas)
        self.formulas_rama = list(formulas_rama) if formulas_rama else list(formulas_nuevas)
        self.aplicadas = set(aplicadas) if aplicadas else set()
        self.hijos = []
        self.cerrado = False
        self.motivo_cierre = None
        self.formula_expandida = None
        self._verificar_cierre()

    def _verificar_cierre(self):
        literales = [f for f in self.formulas_rama if es_literal(f)]
        for f in literales:
            if isinstance(f, Atom) and Not(f) in literales:
                self.cerrado = True
                self.motivo_cierre = (f, Not(f))
                return
            elif isinstance(f, Not) and f.sub in literales:
                self.cerrado = True
                self.motivo_cierre = (f.sub, f)
                return

    def expandir(self):
        if self.cerrado: return
        f_exp = next((f for f in self.formulas_rama if not es_literal(f) and f not in self.aplicadas), None)
        if not f_exp: return

        self.formula_expandida = f_exp
        self.aplicadas.add(f_exp)
        tipo, res = obtener_regla(f_exp)

        if tipo == 'ALPHA':
            hijo = NodoTableau(res, self.formulas_rama + res, self.aplicadas)
            self.hijos.append(hijo)
            hijo.expandir()
        elif tipo == 'BETA':
            for rama in res:
                hijo = NodoTableau(rama, self.formulas_rama + rama, self.aplicadas)
                self.hijos.append(hijo)
                hijo.expandir()

# ==============================================================================
# 4. VISUALIZACIÓN EN CONSOLA Y EJECUCIÓN
# ==============================================================================

def imprimir_arbol(nodo, prefijo="", es_ultimo=True):
    conector = "└── " if es_ultimo else "├── "
    f_str = ", ".join(str(f) for f in nodo.formulas)
    
    if nodo.cerrado:
        estado = f"✕ (CERRADA por {nodo.motivo_cierre[0]} y {nodo.motivo_cierre[1]})"
    elif not nodo.hijos:
        estado = "✓ (ABIERTA)"
    else:
        estado = f" [al expandir: {nodo.formula_expandida}]"

    print(f"{prefijo}{conector}{f_str} {estado}")

    nuevo_prefijo = prefijo + ("    " if es_ultimo else "│   ")
    for i, hijo in enumerate(nodo.hijos):
        imprimir_arbol(hijo, nuevo_prefijo, i == len(nodo.hijos) - 1)

def obtener_hojas(nodo):
    if not nodo.hijos: return [nodo]
    return [h for hijo in nodo.hijos for h in obtener_hojas(hijo)]

def resolver_base_conocimiento(reglas_texto):
    parser = ParserNL()
    formulas = [parser.parsear(r) for r in reglas_texto if r.strip()]

    print("\n" + "="*55)
    print(" 1. TABLA DE ÁTOMOS Y FÓRMULAS GENERADAS")
    print("="*55)
    for letra, texto in parser.atomo_a_texto.items():
        print(f"  {letra} = {texto}")
    print("\nFórmulas bien formadas:")
    for i, f in enumerate(formulas, 1):
        print(f"  R{i}: {f}")

    print("\n" + "="*55)
    print(" 2. ÁRBOL SEMÁNTICO (TABLEAU)")
    print("="*55 + "\n")
    raiz = NodoTableau(formulas)
    raiz.expandir()
    imprimir_arbol(raiz)

    hojas = obtener_hojas(raiz)
    cerradas = sum(1 for h in hojas if h.cerrado)
    abiertas = sum(1 for h in hojas if not h.cerrado)

    print("\n" + "="*55)
    print(" 3. VEREDICTO DE CONSISTENCIA")
    print("="*55)
    print(f"Ramas totales: {len(hojas)} → {cerradas} cerradas (✕) y {abiertas} abiertas (✓)\n")

    if abiertas > 0:
        print("[RESULTADO]: LA BASE DE CONOCIMIENTO ES CONSISTENTE (SATISFACIBLE)")
        print("Modelos (asignaciones) que satisfacen las reglas:")
        for idx, h in enumerate([h for h in hojas if not h.cerrado], 1):
            literales = [f for f in h.formulas_rama if es_literal(f)]
            modelo = {}
            for lit in literales:
                if isinstance(lit, Atom): modelo[lit.nombre] = "V"
                else: modelo[lit.sub.nombre] = "F"
            asig = ", ".join(f"{k} = {v}" for k, v in sorted(modelo.items()))
            print(f"  Modelo {idx}: ({asig})")
    else:
        print("[RESULTADO]: LA BASE DE CONOCIMIENTO ES INCONSISTENTE")

if __name__ == "__main__":
    print("=== MOTOR DE INFERENCIA POR ÁRBOLES SEMÁNTICOS ===")
    print("1. Ejecutar Caso de Prueba Mínimo")
    print("2. Ingresar reglas manualmente")
    
    opc = input("\nOpción (1-2): ").strip()
    if opc == '2':
        print("\nIngrese las reglas (una por línea). Presione ENTER en una línea vacía para procesar:")
        reglas = []
        while True:
            l = input("> ").strip()
            if not l: break
            reglas.append(l)
    else:
        reglas = [
            "Si es de día, entonces voy a trabajar",
            "Si llueve, entonces no voy a trabajar",
            "Es de día"
        ]
    
    resolver_base_conocimiento(reglas)
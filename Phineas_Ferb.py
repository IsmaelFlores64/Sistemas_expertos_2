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


# -------2. PARSER DE LENGUAJE NATURAL---------

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


# --------3. REGLAS DE EXPANSIÓN Y MOTOR TABLEAU----------

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


# ---------4. PERSONAJES Y ESCENARIOS--------
# Cada personaje tiene: su forma de hablar, y sus propios casos de prueba.

PERSONAJES = {
    '1': {
        "nombre": "Mayor Monogram y Carl",
        "expande": "Carl descompone",
        "cerrada": "¡TRAMPA FALLIDA!",
        "abierta": "RUTA LIBRE",
        "escenario": "Episodio",
        "saludo": [
            ("Mayor Monogram", "Buenos días, Agente P. Hemos interceptado unas reglas sospechosas. ¡Carl, el expediente!"),
            ("Carl", "Aquí está, señor. Esto fue lo que logramos descifrar:"),
        ],
        "ok": [
            ("Mayor Monogram", "¡Excelente trabajo, Agente P! Las reglas son CONSISTENTES: no hay contradicción alguna."),
        ],
        "fin_ok": [
            ("Carl", "Señor, ¿y Perry el ornitorrinco? ...¿Dónde está Perry?"),
            ("Mayor Monogram", "Seguro que está ocupado, Carl. Caso cerrado... ¡por ahora!"),
        ],
        "mal": [
            ("Mayor Monogram", "¡Es una trampa! Las reglas son INCONSISTENTES: todas las ramas terminan en contradicción."),
            ("Carl", "¡Se contradicen a sí mismas, señor! Ni el Dr. Doofenshmirtz haría un plan así... bueno, quizá sí."),
            ("Mayor Monogram", "Buen trabajo, Agente P. Puede retirarse."),
        ],
        "casos": {
            '1': ("Un día de verano en Danville (consistente)", [
                "Si es verano, entonces los chicos construyen algo",
                "Si los chicos construyen algo, entonces Candace intenta acusarlos o Isabella pregunta qué están haciendo",
                "Si Candace intenta acusarlos, entonces Perry desaparece",
                "Es verano",
            ]),
            '2': ("Perry el agente (inconsistente)", [
                "Si Perry es agente, entonces Perry va a la guarida",
                "Perry es agente",
                "No es cierto que Perry va a la guarida",
            ]),
            '3': ("La misión de Perry (varios episodios)", [
                "Si Perry es agente, entonces Perry va a la guarida",
                "Si Perry va a la guarida, entonces Doofenshmirtz lo atrapa o Perry escapa",
                "Si Doofenshmirtz lo atrapa, entonces Doofenshmirtz cuenta su pasado trágico",
                "Perry es agente",
            ]),
        },
    },
    '2': {
        "nombre": "Dr. Doofenshmirtz",
        "expande": "Descompongo",
        "cerrada": "¡Imposible!",
        "abierta": "¡Mi plan sigue en pie!",
        "escenario": "Posible desenlace",
        "saludo": [
            ("Dr. Doofenshmirtz", "¡Ah, Perry el ornitorrinco! Llegas justo a tiempo para que te explique mi malvado plan... ¡con lógica proposicional!"),
            ("Dr. Doofenshmirtz", "Aquí están las reglas de mi plan. Y las letras son un código secreto, ¡ja!"),
        ],
        "ok": [
            ("Dr. Doofenshmirtz", "¡Mi plan es CONSISTENTE! ¡Nada se contradice! ¡Soy un genio malvado!"),
        ],
        "fin_ok": [
            ("Dr. Doofenshmirtz", "Aunque seguro llegas tú y lo arruinas todo, ¿verdad? ¡Perry el ornitorrinco!"),
        ],
        "mal": [
            ("Dr. Doofenshmirtz", "¡INCONSISTENTE! ¡Mi propio plan se contradice! ¿Cómo no me di cuenta?"),
            ("Dr. Doofenshmirtz", "Esto me pasa desde que era niño en Gimmelshtump... ¡Y seguro es culpa de Perry el ornitorrinco!"),
        ],
        "casos": {
            '1': ("El inador conquistador (consistente)", [
                "Si Doofenshmirtz termina el inador, entonces Doofenshmirtz conquista Danville",
                "Si Perry llega a la guarida, entonces Perry destruye el inador",
                "Si Perry destruye el inador, entonces no es cierto que Doofenshmirtz conquista Danville",
                "Doofenshmirtz termina el inador",
            ]),
            '2': ("El botón de autodestrucción (inconsistente)", [
                "Si Doofenshmirtz presiona el botón, entonces la guarida explota",
                "Doofenshmirtz presiona el botón",
                "No es cierto que la guarida explota",
            ]),
            '3': ("Un día de planes malvados (varios desenlaces)", [
                "Si Doofenshmirtz tiene un plan, entonces Doofenshmirtz construye un inador",
                "Si Doofenshmirtz construye un inador, entonces Perry lo detiene o Vanessa lo interrumpe",
                "Si Perry lo detiene, entonces Doofenshmirtz grita el nombre de Perry",
                "Doofenshmirtz tiene un plan",
            ]),
            '4': ("El ornitorrinco sin sombrero (2 desenlaces)", [
                "El ornitorrinco tiene sombrero si y solo si Doofenshmirtz cree que es Perry",
                "Doofenshmirtz cree que es un ornitorrinco cualquiera si y solo si no es cierto que el ornitorrinco tiene sombrero",
                "Doofenshmirtz activa la trampa si y solo si Doofenshmirtz cree que es Perry",
                "Doofenshmirtz lo ignora si y solo si Doofenshmirtz cree que es un ornitorrinco cualquiera",
            ]),
        },
    },
}

NOMBRES = ["Phineas", "Ferb", "Perry", "Candace", "Doofenshmirtz", "Isabella",
           "Buford", "Baljeet", "Danville", "Vanessa"]

def con_mayusculas(t):
    # El parser pasa todo a minúsculas; aquí devolvemos las mayúsculas a los nombres
    for n in NOMBRES:
        t = re.sub(rf'\b{n.lower()}\b', n, t)
    return t

def decir(lineas):
    for quien, msg in lineas:
        print(f"\n  {quien}: {msg}")


# ---------5. IMPRESIÓN DEL ÁRBOL Y EJECUCIÓN--------

def imprimir_arbol(nodo, p, prefijo="", es_ultimo=True):
    conector = "└── " if es_ultimo else "├── "
    f_str = ", ".join(str(f) for f in nodo.formulas)

    if nodo.cerrado:
        estado = f"✕ ({p['cerrada']} {nodo.motivo_cierre[0]} y {nodo.motivo_cierre[1]} chocan)"
    elif not nodo.hijos:
        estado = f"✓ ({p['abierta']})"
    else:
        estado = f"[{p['expande']}: {nodo.formula_expandida}]"

    print(f"{prefijo}{conector}{f_str} {estado}")

    nuevo = prefijo + ("    " if es_ultimo else "│   ")
    for i, hijo in enumerate(nodo.hijos):
        imprimir_arbol(hijo, p, nuevo, i == len(nodo.hijos) - 1)

def obtener_hojas(nodo):
    if not nodo.hijos: return [nodo]
    return [h for hijo in nodo.hijos for h in obtener_hojas(hijo)]

def resolver(reglas_texto, p):
    parser = ParserNL()
    formulas = [parser.parsear(r) for r in reglas_texto if r.strip()]

    # 1. Saludo, átomos y reglas
    print("\n" + "="*60)
    decir(p["saludo"])
    print("\n  Átomos:")
    for letra, texto in parser.atomo_a_texto.items():
        print(f"    {letra} = {con_mayusculas(texto)}")
    print("\n  Reglas:")
    for i, f in enumerate(formulas, 1):
        print(f"    R{i}: {f}")

    # 2. Árbol (tableau)
    print("\n" + "-"*60)
    raiz = NodoTableau(formulas)
    raiz.expandir()
    imprimir_arbol(raiz, p)

    # 3. Veredicto
    hojas = obtener_hojas(raiz)
    abiertas = [h for h in hojas if not h.cerrado]
    print("\n" + "-"*60)
    print(f"  Ramas: {len(hojas)} → {len(hojas) - len(abiertas)} cerradas (✕) y {len(abiertas)} abiertas (✓)")

    if abiertas:
        decir(p["ok"])
        for idx, h in enumerate(abiertas, 1):
            modelo = {}
            for lit in [f for f in h.formulas_rama if es_literal(f)]:
                if isinstance(lit, Atom): modelo[lit.nombre] = "V"
                else: modelo[lit.sub.nombre] = "F"
            asig = ", ".join(f"{k} = {v}" for k, v in sorted(modelo.items()))
            print(f"\n    ▶ {p['escenario']} {idx}: ({asig})")
            for k, v in sorted(modelo.items()):
                print(f"       · {'Ocurre' if v == 'V' else 'NO ocurre'}: {con_mayusculas(parser.atomo_a_texto[k])}")
        decir(p["fin_ok"])
    else:
        decir(p["mal"])

if __name__ == "__main__":
    print("=== MOTOR DE INFERENCIA POR ÁRBOLES SEMÁNTICOS ===")
    print("Elige personaje:")
    for k, per in PERSONAJES.items():
        print(f"  {k}. {per['nombre']}")
    personaje = PERSONAJES.get(input("\nOpción: ").strip(), PERSONAJES['1'])

    print(f"\nEscenarios de {personaje['nombre']}:")
    for k, (titulo, _) in personaje["casos"].items():
        print(f"  {k}. {titulo}")
    manual = str(len(personaje["casos"]) + 1)
    print(f"  {manual}. Escribir mis propias reglas")

    opc = input("\nOpción: ").strip()
    if opc == manual:
        print("Escribe una regla por línea (línea vacía para terminar):")
        reglas = []
        while True:
            linea = input("> ").strip()
            if not linea: break
            reglas.append(linea)
    else:
        reglas = personaje["casos"].get(opc, personaje["casos"]['1'])[1]

    resolver(reglas, personaje)
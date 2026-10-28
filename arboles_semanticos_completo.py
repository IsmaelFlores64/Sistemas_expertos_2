import re
import queue
import textwrap
import threading

try:
    import tkinter as tk
    from tkinter import ttk, font as tkfont
    from tkinter.scrolledtext import ScrolledText
    HAY_TK = True
except ImportError:
    HAY_TK = False


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

        if t.startswith('si ') and ' entonces ' not in t:
            raise ValueError(f"Falta 'entonces' en la regla: «{texto.strip()}»")

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


# ---------4. PERSONAJE Y ESCENARIOS--------

PERSONAJE = {
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
}

CASOS = {
    '1': ("Consistente", [
        "Si es de día, entonces voy a trabajar",
        "Si llueve, entonces no voy a trabajar",
        "Es de día",
    ]),
    '2': ("Inconsistente", [
        "Si es de día, entonces voy a trabajar",
        "Si llueve, entonces no voy a trabajar",
        "Es de día",
        "Llueve",
    ]),
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


# ---------5. MODO CONSOLA--------

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

def modelo_de_rama(hoja):
    modelo = {}
    for lit in [f for f in hoja.formulas_rama if es_literal(f)]:
        if isinstance(lit, Atom): modelo[lit.nombre] = "V"
        else: modelo[lit.sub.nombre] = "F"
    return modelo

def resolver(reglas_texto, p):
    parser = ParserNL()
    try:
        formulas = [parser.parsear(r) for r in reglas_texto if r.strip()]
    except ValueError as e:
        print("\n" + "="*60)
        print(f"\n  Carl: Señor, hay un problema con el expediente. {e}")
        print("  Mayor Monogram: Corrígela con el formato «Si ..., entonces ...» e inténtalo de nuevo, Agente P.")
        return

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
            modelo = modelo_de_rama(h)
            asig = ", ".join(f"{k} = {v}" for k, v in sorted(modelo.items()))
            print(f"\n    ▶ {p['escenario']} {idx}: ({asig})")
            for k, v in sorted(modelo.items()):
                print(f"       · {'Ocurre' if v == 'V' else 'NO ocurre'}: {con_mayusculas(parser.atomo_a_texto[k])}")
        decir(p["fin_ok"])
    else:
        decir(p["mal"])

def pedir_reglas_manual():
    print("Escribe una regla por línea (línea vacía para terminar):")
    reglas = []
    while True:
        linea = input("> ").strip()
        if not linea: break
        reglas.append(linea)
    return reglas

def menu_consola(cola=None):
    """Menú en bucle. Si hay 'cola', también manda cada regla a la ventana gráfica."""
    while True:
        print(f"\nEscenarios de {PERSONAJE['nombre']}:")
        for k, (titulo, _) in CASOS.items():
            print(f"  {k}. {titulo}")
        print("  3. Escribir mis propias reglas")
        print("  0. Salir")

        opc = input("\nOpción: ").strip()

        if opc == '0':
            print("\n  Mayor Monogram: ¡Hasta la próxima, Agente P!")
            if cola is not None:
                cola.put(("salir", None))
            break
        elif opc == '3':
            reglas = pedir_reglas_manual()
            if not reglas:
                print("No escribiste ninguna regla.")
                continue
        elif opc in CASOS:
            reglas = CASOS[opc][1]
        else:
            print("Opción no válida, intenta de nuevo.")
            continue

        resolver(reglas, PERSONAJE)
        if cola is not None:
            cola.put(("reglas", reglas))   # la ventana dibuja el mismo árbol
        input("\nPresiona Enter para volver al menú...")


# ---------6. INTERFAZ GRÁFICA (tkinter)--------

PAD_X, PAD_Y = 12, 8
GAP_X, GAP_Y = 26, 55
WRAP = 34          # caracteres por línea dentro de cada caja
MARGEN = 40

ESTILOS = {
    "cerrado":   {"fill": "#fdecea", "line": "#c0392b", "estado": "#c0392b"},
    "abierto":   {"fill": "#e7f5ec", "line": "#2e8b57", "estado": "#2e8b57"},
    "expandido": {"fill": "#eef3fb", "line": "#4a6fa5", "estado": "#4a6fa5"},
}

class Caja:
    """Información de dibujo de un nodo del tableau."""
    def __init__(self, nodo, p, fuente):
        self.nodo = nodo
        f_str = ", ".join(str(f) for f in nodo.formulas)
        self.lineas = textwrap.wrap(f_str, WRAP, break_long_words=False) or [""]

        if nodo.cerrado:
            self.tipo = "cerrado"
            a, b = nodo.motivo_cierre
            estado = f"✕ {p['cerrada']} {a} y {b} chocan"
        elif not nodo.hijos:
            self.tipo = "abierto"
            estado = f"✓ {p['abierta']}"
        else:
            self.tipo = "expandido"
            estado = f"[{p['expande']}: {nodo.formula_expandida}]"
        self.estado = textwrap.wrap(estado, WRAP, break_long_words=False)

        todas = self.lineas + self.estado
        self.ancho = max(fuente.measure(l) for l in todas) + 2 * PAD_X
        self.alto = (len(todas) * fuente.metrics("linespace")) + 2 * PAD_Y + 4

        self.hijos = [Caja(h, p, fuente) for h in nodo.hijos]

        if self.hijos:
            suma = sum(h.ancho_sub for h in self.hijos) + GAP_X * (len(self.hijos) - 1)
            self.ancho_sub = max(self.ancho, suma)
        else:
            self.ancho_sub = self.ancho
        self.cx = 0
        self.y = 0

    def posicionar(self, x_izq, y):
        self.cx = x_izq + self.ancho_sub / 2
        self.y = y
        if self.hijos:
            total = sum(h.ancho_sub for h in self.hijos) + GAP_X * (len(self.hijos) - 1)
            cursor = x_izq + (self.ancho_sub - total) / 2
            for h in self.hijos:
                h.posicionar(cursor, y + self.alto + GAP_Y)
                cursor += h.ancho_sub + GAP_X

    def profundidad_y(self):
        base = self.y + self.alto
        return max([base] + [h.profundidad_y() for h in self.hijos])


def construir_reporte(parser, formulas, raiz):
    p = PERSONAJE
    out = []

    def dec(lineas):
        for quien, msg in lineas:
            out.append(f"{quien}: {msg}\n")

    dec(p["saludo"])
    out.append("\nÁtomos:\n")
    for letra, texto in parser.atomo_a_texto.items():
        out.append(f"  {letra} = {con_mayusculas(texto)}\n")
    out.append("\nReglas:\n")
    for i, f in enumerate(formulas, 1):
        out.append(f"  R{i}: {f}\n")

    hojas = obtener_hojas(raiz)
    abiertas = [h for h in hojas if not h.cerrado]
    out.append(f"\nRamas: {len(hojas)} → {len(hojas) - len(abiertas)} cerradas (✕) "
               f"y {len(abiertas)} abiertas (✓)\n\n")

    if abiertas:
        dec(p["ok"])
        for idx, h in enumerate(abiertas, 1):
            modelo = modelo_de_rama(h)
            asig = ", ".join(f"{k} = {v}" for k, v in sorted(modelo.items()))
            out.append(f"\n▶ {p['escenario']} {idx}: ({asig})\n")
            for k, v in sorted(modelo.items()):
                marca = "Ocurre" if v == "V" else "NO ocurre"
                out.append(f"   · {marca}: {con_mayusculas(parser.atomo_a_texto[k])}\n")
        out.append("\n")
        dec(p["fin_ok"])
    else:
        dec(p["mal"])
    return "".join(out)


class App:
    def __init__(self, root, cola=None):
        self.root = root
        self.cola = cola
        root.title("Árboles semánticos – Mayor Monogram y Carl")
        root.geometry("1300x780")

        self.fuente = tkfont.nametofont("TkDefaultFont").copy()
        self.fuente.configure(size=10)
        self.fuente_b = self.fuente.copy()
        self.fuente_b.configure(weight="bold")

        panel = ttk.PanedWindow(root, orient="horizontal")
        panel.pack(fill="both", expand=True)

        # ----- Izquierda: controles + reporte -----
        izq = ttk.Frame(panel, padding=8)
        panel.add(izq, weight=1)

        ttk.Label(izq, text="Escenario:").pack(anchor="w")
        self.combo = ttk.Combobox(
            izq, state="readonly",
            values=[titulo for titulo, _ in CASOS.values()] + ["Mis propias reglas"],
        )
        self.combo.current(0)
        self.combo.pack(fill="x", pady=(0, 6))
        self.combo.bind("<<ComboboxSelected>>", self.cargar_escenario)

        ttk.Label(izq, text="Reglas (una por línea):").pack(anchor="w")
        self.txt_reglas = tk.Text(izq, height=8, wrap="word", font=self.fuente)
        self.txt_reglas.pack(fill="x", pady=(0, 6))

        botones = ttk.Frame(izq)
        botones.pack(fill="x", pady=(0, 6))
        ttk.Button(botones, text="Resolver y graficar", command=self.resolver).pack(side="left")
        ttk.Button(botones, text="Limpiar", command=self.limpiar).pack(side="left", padx=6)

        ttk.Label(izq, text="Expediente:").pack(anchor="w")
        self.reporte = ScrolledText(izq, wrap="word", font=self.fuente, state="disabled")
        self.reporte.pack(fill="both", expand=True)

        # ----- Derecha: canvas con scroll -----
        der = ttk.Frame(panel)
        panel.add(der, weight=4)

        self.canvas = tk.Canvas(der, bg="white", highlightthickness=0)
        sb_y = ttk.Scrollbar(der, orient="vertical", command=self.canvas.yview)
        sb_x = ttk.Scrollbar(der, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)
        sb_y.pack(side="right", fill="y")
        sb_x.pack(side="bottom", fill="x")
        self.canvas.pack(fill="both", expand=True)

        # Arrastrar con el mouse y rueda para desplazarse
        self.canvas.bind("<ButtonPress-1>", lambda e: self.canvas.scan_mark(e.x, e.y))
        self.canvas.bind("<B1-Motion>", lambda e: self.canvas.scan_dragto(e.x, e.y, gain=1))
        self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(-1 * (e.delta // 120), "units"))
        self.canvas.bind("<Shift-MouseWheel>", lambda e: self.canvas.xview_scroll(-1 * (e.delta // 120), "units"))
        self.canvas.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))

        self.cargar_escenario()
        if self.cola is not None:
            self.revisar_cola()

    # ---------- Comunicación con la consola (modo "ambas") ----------
    def revisar_cola(self):
        try:
            while True:
                tipo, dato = self.cola.get_nowait()
                if tipo == "reglas":
                    self.combo.current(len(self.combo["values"]) - 1)
                    self.txt_reglas.delete("1.0", "end")
                    self.txt_reglas.insert("1.0", "\n".join(dato))
                    self.resolver()
                elif tipo == "salir":
                    self.root.destroy()
                    return
        except queue.Empty:
            pass
        self.root.after(150, self.revisar_cola)

    # ---------- Acciones ----------
    def cargar_escenario(self, _evento=None):
        idx = self.combo.current()
        self.txt_reglas.delete("1.0", "end")
        claves = list(CASOS.keys())
        if idx < len(claves):
            self.txt_reglas.insert("1.0", "\n".join(CASOS[claves[idx]][1]))

    def limpiar(self):
        self.txt_reglas.delete("1.0", "end")
        self.canvas.delete("all")
        self.mostrar_reporte("")

    def mostrar_reporte(self, texto):
        self.reporte.configure(state="normal")
        self.reporte.delete("1.0", "end")
        self.reporte.insert("1.0", texto)
        self.reporte.configure(state="disabled")

    def resolver(self):
        reglas = [l for l in self.txt_reglas.get("1.0", "end").splitlines() if l.strip()]
        if not reglas:
            self.mostrar_reporte("Escribe al menos una regla.")
            self.canvas.delete("all")
            return

        parser = ParserNL()
        try:
            formulas = [parser.parsear(r) for r in reglas]
        except ValueError as e:
            self.canvas.delete("all")
            self.mostrar_reporte(
                f"Carl: Señor, hay un problema con el expediente. {e}\n\n"
                "Mayor Monogram: Corrígela con el formato «Si ..., entonces ...» "
                "e inténtalo de nuevo, Agente P."
            )
            return

        raiz = NodoTableau(formulas)
        raiz.expandir()
        self.mostrar_reporte(construir_reporte(parser, formulas, raiz))
        self.dibujar(raiz)

    # ---------- Dibujo ----------
    def dibujar(self, raiz):
        self.canvas.delete("all")
        arbol = Caja(raiz, PERSONAJE, self.fuente)
        arbol.posicionar(MARGEN, MARGEN)

        ancho_total = arbol.ancho_sub + 2 * MARGEN
        alto_total = arbol.profundidad_y() + MARGEN
        self.canvas.configure(scrollregion=(0, 0, ancho_total, alto_total))

        self._dibujar_aristas(arbol)
        self._dibujar_cajas(arbol)

        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)

    def _dibujar_aristas(self, caja):
        for h in caja.hijos:
            self.canvas.create_line(
                caja.cx, caja.y + caja.alto, h.cx, h.y,
                fill="#7f8c8d", width=1.5, arrow="last",
            )
            self._dibujar_aristas(h)

    def _dibujar_cajas(self, caja):
        est = ESTILOS[caja.tipo]
        x1, y1 = caja.cx - caja.ancho / 2, caja.y
        x2, y2 = caja.cx + caja.ancho / 2, caja.y + caja.alto
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=est["fill"], outline=est["line"], width=2)

        paso = self.fuente.metrics("linespace")
        y = y1 + PAD_Y
        for linea in caja.lineas:
            self.canvas.create_text(caja.cx, y, text=linea, anchor="n",
                                    font=self.fuente, fill="#222222")
            y += paso
        y += 4
        for linea in caja.estado:
            self.canvas.create_text(caja.cx, y, text=linea, anchor="n",
                                    font=self.fuente_b, fill=est["estado"])
            y += paso

        for h in caja.hijos:
            self._dibujar_cajas(h)


# ---------7. PROGRAMA PRINCIPAL--------

def abrir_gui(cola=None):
    ventana = tk.Tk()
    App(ventana, cola)
    return ventana

if __name__ == "__main__":
    print("=== MOTOR DE INFERENCIA POR ÁRBOLES SEMÁNTICOS ===")
    print("Elige el modo:")
    print("  1. Interfaz gráfica")
    print("  2. Consola")
    print("  3. Ambas a la vez (menú en consola + árbol dibujado en la ventana)")
    modo = input("\nOpción: ").strip()

    if modo in ('1', '3') and not HAY_TK:
        print("\nNo se encontró tkinter en este Python; usando solo la consola.")
        modo = '2'

    if modo == '1':
        abrir_gui().mainloop()
    elif modo == '3':
        cola = queue.Queue()
        ventana = abrir_gui(cola)
        # La consola corre en otro hilo; la ventana debe quedarse en el hilo principal
        threading.Thread(target=menu_consola, args=(cola,), daemon=True).start()
        ventana.mainloop()
    else:
        menu_consola()
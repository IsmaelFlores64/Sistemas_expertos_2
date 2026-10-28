# Motor de inferencia por árboles semánticos

Programa en Python que recibe reglas escritas en español, las convierte a lógica proposicional y usa el **método de árboles semánticos (tableau)** para decidir si el conjunto de reglas es **consistente** o **inconsistente**. Las explicaciones las dan **Mayor Monogram y Carl**.

Incluye dos formas de usarlo, que también pueden funcionar al mismo tiempo:

- **Consola:** menú de texto que imprime el árbol con caracteres.
- **Interfaz gráfica (tkinter):** dibuja el árbol, muestra los átomos en una tabla y permite guardar y cargar reglas.

Todo está en un solo archivo: `arboles_semanticos_completo.py`.

---

## Requisitos

- Python 3.8 o superior.
- No necesita instalar librerías externas.
- Para la interfaz gráfica se necesita **tkinter**, que ya viene con Python en Windows y macOS. En Linux, si falta:
  ```bash
  sudo apt install python3-tk
  ```

---

## Cómo ejecutarlo

```bash
python arboles_semanticos_completo.py
```

Al iniciar pregunta el modo:

| Opción | Modo | Qué hace |
|---|---|---|
| 1 | Interfaz gráfica | Abre la ventana con el árbol dibujado |
| 2 | Consola | Menú en texto, el árbol se imprime con caracteres |
| 3 | Ambas a la vez | Usas el menú en la consola y cada resultado también se dibuja en la ventana |

> **Importante:** la interfaz gráfica necesita una pantalla. En entornos sin pantalla, como **GitHub Codespaces** o un servidor, no puede abrir la ventana. En ese caso el programa avisa y sigue automáticamente en modo consola. Para usar la interfaz, ejecútalo en tu computadora.

### Menú de la consola

```
1. Consistente
2. Inconsistente
3. Escribir mis propias reglas
0. Salir
```

El menú se repite hasta que escribes `0`. En la opción 3 escribes una regla por línea y terminas con una línea vacía.

---

## Cómo escribir las reglas

Las reglas se escriben en español natural, una por línea. El parser reconoce estos conectores:

| Lo que escribes | Símbolo | Ejemplo |
|---|---|---|
| `Si ..., entonces ...` | → (implica) | `Si es de día, entonces voy a trabajar` |
| `... si y solo si ...` | ↔ (equivale) | `Voy a trabajar si y solo si es de día` |
| `... y ...` | ∧ (y) | `Llueve y hace frío` |
| `... o ...` | ∨ (o) | `Llueve o hace frío` |
| `No ...` | ¬ (negación) | `No voy a trabajar` |
| `No es cierto que ...` | ¬ (negación de algo compuesto) | `No es cierto que llueve y hace frío` |

Una oración que no tiene ningún conector es un **átomo** (una proposición simple). A cada átomo distinto se le asigna una letra: `p`, `q`, `r`, `s`... y si se acaban, `p1`, `q1`, etc.

### Cosas a tener en cuenta

- Si una regla empieza con "si" y le falta el **"entonces"**, el programa avisa del error en lugar de interpretarla mal.
- Acepta variantes con acento: `sí y sólo sí`, `ó`.
- Mayúsculas y signos de puntuación se ignoran.
- Escribe igual los mismos hechos. `Es de día` y `Es de noche` son átomos distintos, y `llueve` y `esta lloviendo` también.
- No hay paréntesis. Si una regla mezcla varios conectores, el parser corta primero en el `si y solo si`, luego en el `si... entonces`, luego en `o` y al final en `y`. Para evitar confusiones, usa un solo conector por regla y separa el resto en reglas distintas.
- Una frase que usa "solo si" (sin "y") no se reconoce como bicondicional.

---

## Ejemplo

Reglas del escenario **Inconsistente**:

```
Si es de día, entonces voy a trabajar
Si llueve, entonces no voy a trabajar
Es de día
Llueve
```

Resultado en consola:

```
Átomos:
  p = es de día
  q = voy a trabajar
  r = llueve

Reglas:
  R1: (p → q)
  R2: (r → ¬q)
  R3: p
  R4: r

└── (p → q), (r → ¬q), p, r [Carl descompone: (p → q)]
    ├── ¬p ✕ (¡TRAMPA FALLIDA! p y ¬p chocan)
    └── q [Carl descompone: (r → ¬q)]
        ├── ¬r ✕ (¡TRAMPA FALLIDA! r y ¬r chocan)
        └── ¬q ✕ (¡TRAMPA FALLIDA! q y ¬q chocan)

Ramas: 3 → 3 cerradas (✕) y 0 abiertas (✓)
Las reglas son INCONSISTENTES
```

Todas las ramas se cierran, así que las reglas se contradicen. Si quitas la regla `Llueve`, queda una rama abierta y el resultado es **consistente**.

---

## La interfaz gráfica

- **Panel izquierdo:**
  - Selector de escenario (Consistente, Inconsistente, Mis propias reglas).
  - Cuadro de texto con las reglas, editable.
  - Botones **Resolver y graficar**, **Limpiar**, **Guardar reglas** y **Cargar reglas**.
  - El *expediente*: diálogos de Monogram y Carl, reglas con sus fórmulas, y los episodios (modelos) cuando las reglas son consistentes.
- **Panel derecho:** el árbol dibujado.
  - Cajas **azules**: nodos que se descomponen (indica qué fórmula expande Carl).
  - Cajas **rojas**: ramas cerradas (✕), con el par de literales que chocan.
  - Cajas **verdes**: ramas abiertas (✓).
  - Se puede mover arrastrando con el mouse o con la rueda (con Shift, horizontal).
- **Tabla de átomos:** debajo del árbol, con la letra de cada átomo y su significado.

### Guardar y cargar reglas

- **Guardar reglas:** guarda lo que tengas en el cuadro en un archivo `.txt`, una regla por línea (se propone `mis_reglas.txt`).
- **Cargar reglas:** abre cualquier `.txt` con una regla por línea y lo pone en el cuadro.

---

## Cómo funciona el código

El archivo está dividido en secciones:

### 1. Estructuras de datos (fórmulas bien formadas)
Clases para representar las fórmulas como un árbol sintáctico:
`Atom` (proposición simple), `Not` (negación) y `BinaryOp` con sus subclases `And`, `Or`, `Imp` e `Iff`. Cada una sabe imprimirse (`(p → q)`) y compararse con otra.

### 2. Parser de lenguaje natural (`ParserNL`)
Convierte cada frase en una fórmula. Pasa el texto a minúsculas, quita puntuación y busca los conectores en este orden: `no es cierto que`, `si y solo si`, `si... entonces`, `o`, `y`, `no`. Lo que queda sin conector se vuelve un átomo. El parser lleva un diccionario que le asigna una letra a cada texto, y lanza un error si falta el "entonces".

### 3. Motor del tableau
- `es_literal(f)`: un literal es un átomo o su negación.
- `obtener_regla(f)`: dice cómo se descompone una fórmula.
  - **Reglas alfa** (una sola rama, ambas partes se cumplen): `A ∧ B`, `¬(A ∨ B)`, `¬(A → B)`, `¬¬A`.
  - **Reglas beta** (se bifurca el árbol): `A ∨ B`, `A → B` (se vuelve `¬A` o `B`), `¬(A ∧ B)`, `A ↔ B`, `¬(A ↔ B)`.
- `NodoTableau`: un nodo del árbol. Guarda las fórmulas de su rama, detecta si la rama se **cierra** (si tiene un átomo y su negación a la vez) y se **expande** eligiendo una fórmula pendiente y aplicándole su regla.

**Criterio de decisión:**
- Si **todas** las ramas se cierran → las reglas son **inconsistentes**.
- Si **alguna** rama queda abierta → son **consistentes**, y cada rama abierta es un posible escenario (qué átomos son verdaderos y cuáles falsos).

### 4. Personaje y escenarios
`PERSONAJE` guarda los diálogos de Mayor Monogram y Carl y los textos del dibujo (`Carl descompone`, `¡TRAMPA FALLIDA!`, `RUTA LIBRE`). `CASOS` tiene las reglas de los escenarios por defecto.

### 5. Modo consola
`imprimir_arbol` dibuja el árbol con caracteres, `resolver` junta todo (saludo, átomos, reglas, árbol y veredicto) y `menu_consola` es el menú en bucle.

### 6. Interfaz gráfica
- `Caja`: calcula tamaño y posición de cada nodo para que las ramas no se encimen.
- `construir_reporte`: arma el texto del expediente.
- `App`: la ventana (botones, cuadros de texto, tabla de átomos, canvas) y las funciones de resolver, dibujar, guardar y cargar.

### 7. Programa principal
Pregunta el modo. En el modo 3, la ventana corre en el hilo principal (tkinter lo exige) y el menú de la consola en un hilo aparte. Se comunican con una cola (`queue`) para que cada regla resuelta en la consola se dibuje también en la ventana.

---

## Límites conocidos

- **Muchas reglas:** guardar y cargar no tiene problema con cientos de reglas, pero resolver depende de cuánto se ramifica el árbol. Cada `o` o `si... entonces` sin hechos que cierren ramas duplica las ramas. Unas 18 implicaciones independientes ya generan más de 260,000 ramas y tardan decenas de segundos, y con unas 25 el programa no termina.
- **Profundidad:** el árbol se recorre con recursión (límite de Python: unas 1000 reglas encadenadas).
- **Dibujo:** un árbol con cientos de ramas se dibuja, pero deja de ser legible.
- **Lenguaje:** el parser es sencillo y solo entiende las estructuras de la tabla de arriba.

---

## Solución de problemas

| Mensaje | Causa | Solución |
|---|---|---|
| `no display name and no $DISPLAY environment variable` | Estás en un entorno sin pantalla (Codespaces, servidor) | Ejecútalo en tu computadora; el programa ya continúa en modo consola |
| `No se encontró tkinter en este Python` | Tu Python no trae tkinter | Reinstala Python marcando tcl/tk, o en Linux `sudo apt install python3-tk` |
| `Falta 'entonces' en la regla` | Una regla empieza con "si" pero no tiene "entonces" | Escríbela como `Si ..., entonces ...` |
| Una regla aparece como un solo átomo largo | El parser no encontró ningún conector | Revisa que uses `y`, `o`, `entonces`, `si y solo si` o `no` tal como en la tabla |
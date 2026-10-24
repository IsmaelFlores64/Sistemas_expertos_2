# Sistemas_expertos_2
# Motor de Inferencia por Árboles Semánticos (Tableaux)

Este proyecto implementa un **Motor de Inferencia Proposicional** en Python 3 utilizando únicamente la librería estándar. Traduce enunciados en lenguaje natural a fórmulas lógicas, construye el árbol semántico y evalúa si la base de conocimiento es consistente.

## Estructura del Código (`main.py`)
1. **Estructura de Datos (WFF)**: Clases orientadas a objetos para representar átomos, negaciones y conectivos proposicionales.
2. **Parser de Lenguaje Natural**: Convierte texto en español a expresiones lógicas mediante Expresiones Regulares.
3. **Motor Tableau**: Aplica las reglas Alfa (no ramificadas) y Beta (ramificadas), detecta contradicciones ($p$ y $\neg p$) y cierra ramas.
4. **Visualizador**: Imprime el árbol con identación ASCII y extrae las asignaciones de verdad (modelos).

## Tabla de Reglas de Expansión

| Reglas Alfa ($\alpha$) | Reglas Beta ($\beta$) |
| :--- | :--- |
| $A \land B \implies A, B$ | $A \lor B \implies A \mid B$ |
| $\neg(A \lor B) \implies \neg A, \neg B$ | $A \rightarrow B \implies \neg A \mid B$ |
| $\neg(A \rightarrow B) \implies A, \neg B$ | $\neg(A \land B) \implies \neg A \mid \neg B$ |
| $\neg\neg A \implies A$ | $A \leftrightarrow B \implies (A, B) \mid (\neg A, \neg B)$ |

## Cómo ejecutar
```bash
python main.py
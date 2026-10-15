---
marp: true
paginate: true
---

# 1. Pregunta e hipótesis

**LEXICON-X · Eráviri → español**

¿Qué estrategia generaliza a combinaciones nuevas con pocos pares bilingües?

**Hipótesis:** separar vocabulario y estructura supera la recuperación de frases
completas por similitud.

- 420 pares para aprender; 120 para validar.
- Orden observado: `S O [L] [nu] V`.
- 59 formas fuente conocidas; 87/120 ejemplos de validación tienen una terna
  sujeto–objeto–raíz nueva.
- Pistas oficiales contrastadas; sin ajustes por frase de validación.

---

# 2. Métodos y resultados

| Sistema | Exact match | chrF |
|---|---:|---:|
| Recuperación Jaccard | 0,00 % | 64,63 |
| Composicional | 100,00 % | 100,00 |
| Sin tiempo | 68,33 % | 94,28 |
| Sin negación | 85,83 % | 98,09 |
| Sin reordenamiento | 0,00 % | 84,08 |

Léxico inducido solo de entrenamiento; gramática explícita respaldada por el EDA.
Cada ablación cambia un componente de generación. Métricas sobre 120 pares,
normalizados; chrF de sacrebleu 2.6.0, orden 6, beta 2.

---

# 3. Generalización y tres errores

Composicional: **87/87** ternas nuevas, **33/33** vistas; 17/17 negaciones,
16/16 pasados y 22/22 futuros. Sin errores observados en esta validación.

Errores reales de Jaccard:

1. `telu tavi nemi`: cambia **el alimento** por **la carta**.
2. `vonu suni rilo kori`: cambia **guarda** por **elige**.
3. `naku kava kuna nu vasi`: pierde **no** y cambia **la carta** por **el mapa**.

chrF alto puede ocultar errores de significado: sin negación conserva 98,09 chrF,
pero falla en las 17 frases negativas.

---

# 4. Conclusión, límites y reproducibilidad

La composición supera la recuperación en los datos disponibles. La validación
ya fue explorada; el 100 % no garantiza el test oculto. Las 30 conjugaciones
están en entrenamiento: no se ha demostrado traducción de vocabulario nuevo.

El LM del notebook 03 mejora probabilidad de Eráviri, pero no interviene en este
traductor. No se le atribuyen mejoras de traducción. Los saludos oficiales se
tratan como memoria explícita, fuera de la métrica principal.

Entrega: notebook 04, `predicciones.csv` de 40 filas y fase 5 separada. Código,
versiones, hashes, métricas y modelo JSON reproducibles. Registro de IA y
bibliotecas en `REGISTRO_HERRAMIENTAS.md`.

Siguiente investigación: vocabulario y formas no observadas, nuevas estructuras
y evaluación independiente con comparación de modelos adicionales.

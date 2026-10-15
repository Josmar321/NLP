# 04 · Traducción de Eráviri al español

El notebook `04_Traduccion.ipynb` implementa entrenamiento, inferencia, métricas,
ablaciones y exportación de la entrega. El código está en `lexicon/translation.py`.
No usa modelos externos de traducción ni archivos privados del docente.

## 1. Hipótesis y protocolo

Hipótesis falsable: un traductor que separa vocabulario y estructura logra más
exact matches en combinaciones nuevas que recuperar una traducción completa
por similitud de palabras. La comparación principal usa los mismos 420 pares
de entrenamiento y los mismos 120 pares de validación.

Antes de evaluar se fijan la gramática respaldada por el EDA, el uso de las
formas verbales observadas y la generación española. No se añaden excepciones
por oración de validación. Esta validación ya fue explorada en los cuadernos
anteriores: no es una evaluación ciega independiente. El test oficial oculto
sigue siendo la evaluación pendiente de generalización externa.

## 2. Baseline obligatorio: Jaccard

Se tokeniza la entrada y cada fuente de entrenamiento, se convierten en conjuntos
y se calcula intersección/unión. Se copia la traducción del ejemplo con mayor
similitud. Los empates se resuelven por el primer ejemplo de entrenamiento,
igual que en la plantilla original.

El baseline reconoce elementos comunes, pero no combina traducciones, no usa
el orden y puede cambiar objeto, acción, lugar o negación al recuperar un vecino.

## 3. Traductor composicional y qué aprende realmente

Se aplica la hipótesis de estructura de los pares controlados:

```text
Eráviri: SUJETO OBJETO [LUGAR] [nu] VERBO
Español: SUJETO [no] VERBO OBJETO [en LUGAR]
```

Las reglas son explícitas y se justifican con entrenamiento; no se presentan
como una gramática descubierta automáticamente de cualquier idioma. El léxico
sí se induce contando correspondencias de los 420 pares: diez sujetos, doce
objetos, seis lugares y treinta formas verbales. No se almacenan las frases de
validación ni sus traducciones como excepciones.

Las correspondencias con traducciones contradictorias producen un error de
entrenamiento, en vez de elegir silenciosamente una. Todas las fuentes de
entrenamiento deben ser compatibles con la plantilla. Las pistas oficiales
se contrastan después y no se utilizan para ajustar el léxico del experimento.

Ejemplo observado en entrenamiento:

```text
vonu zura miri nu lomuta.
  sujeto: vonu       → el viajero
  objeto: zura       → la llave
  lugar: miri        → en el bosque
  negación: nu       → no
  verbo: lomuta      → buscó

el viajero no buscó la llave en el bosque.
```

Se conservan las conjugaciones españolas observadas: no se generan formas
irregulares concatenando terminaciones. El análisis identifica raíz y tiempo,
pero la realización española consulta la forma verbal completa aprendida. Las
30 formas ya aparecen en entrenamiento. Por tanto, el experimento demuestra
recombinación de formas conocidas, **no** conjugación de un verbo nunca visto.

Una fuente desconocida o fuera de la gramática produce `UnsupportedSentence`.
No se sustituye por una frase parecida que pudiera alterar el sentido. Para
exportar los CSV requerimos cobertura completa de sus cuarenta entradas.

## 4. Métricas y normalización

Exact match usa NFC, minúsculas, espacios uniformes y eliminación de puntuación
final. Se preservan tildes y puntuación interna. Se mide la proporción de frases
completamente iguales a la referencia.

chrF se calcula con **sacrebleu 2.6.0**, sobre las mismas cadenas normalizadas:
orden de caracteres 6, orden de palabras 0, beta 2, sin espacios y con orden
efectivo. Se registra la firma del evaluador y su versión. Su escala es 0–100;
exact match se guarda como proporción 0–1.

No se usa BLEU como indicador principal. chrF permite ver semejanza parcial,
pero puede ser alto aunque falte una negación o cambie el tiempo verbal.

## 5. Resultado principal en validación

| Sistema | Aciertos | Exact match | chrF |
|---|---:|---:|---:|
| Jaccard | 0/120 | 0,00 % | 64,63 |
| Composicional completo | 120/120 | 100,00 % | 100,00 |
| Ablación: sin tiempo | 82/120 | 68,33 % | 94,28 |
| Ablación: sin negación | 103/120 | 85,83 % | 98,09 |
| Ablación: sin reordenamiento | 0/120 | 0,00 % | 84,08 |

Los sistemas no se ajustan frase por frase después de observar estos resultados.
La comparación respalda la hipótesis dentro de los datos sintéticos disponibles.
No se atribuye el 100 % a un dominio general del idioma ni se garantiza el test
oculto. La gramática es muy regular y todos los tokens de validación son conocidos.

## 6. Generalización y análisis por fenómeno

El modelo completo obtiene 17/17 en negación, 16/16 en pasado, 22/22 en futuro,
85/85 con lugar y 35/35 sin lugar. Los grupos se solapan.

Se define terna nueva como sujeto–objeto–raíz verbal ausente de entrenamiento:
el modelo completo obtiene **87/87** en ternas nuevas y **33/33** en ternas vistas.
Jaccard obtiene cero en ambos grupos. La ausencia de la oración completa no se
confunde con vocabulario desconocido ni con un cambio de distribución demostrado.

`metricas_grupos.csv` muestra todos los subconjuntos y sus tamaños. Los grupos
vacíos tienen métricas nulas, no una falsa precisión de cero. No se observa
ninguna abstención del modelo completo en los conjuntos disponibles.

## 7. Ablaciones: qué cambia y qué se conserva

Sin tiempo: el analizador sigue identificando la forma de entrada, pero el
generador utiliza la traducción presente de su raíz. Léxico, orden y negación
se conservan. Falla en los 38 casos pasados/futuros y conserva los 82 presentes.
Esto mide la contribución de conservar tiempo, no la capacidad de aprender
conjugaciones nuevas ni una ablación total del analizador morfológico.

Sin negación: solo se omite `no` en la generación. Falla exactamente en las
17 frases negativas. Su chrF de 98,09 ilustra que semejanza superficial alta
no asegura conservación del significado.

Sin reordenamiento: se mantienen las traducciones de cada componente, los
artículos, el tiempo y la negación, pero se colocan según el orden fuente.
La caída de exact match mide el aporte del orden español en esta generación.
Cada ablación cambia un único componente y conserva todo lo demás.

## 8. Tres errores reales, sin inventar fallos del modelo completo

El modelo completo no tiene errores en esta validación. Para cumplir el análisis
crítico se estudian errores reales del baseline y de las ablaciones, identificando
siempre el sistema al que pertenecen.

1. **Objeto cambiado — Jaccard**
   Fuente: `telu tavi nemi.`
   Referencia: «el maestro recuerda el alimento.»
   Predicción: «el maestro recuerda la carta.»
   Recupera una oración cercana sin reemplazar el objeto por el de la entrada.

2. **Acción cambiada — Jaccard**
   Fuente: `vonu suni rilo kori.`
   Referencia: «el viajero guarda el libro en el río.»
   Predicción: «el viajero elige el libro en el río.»
   Comparte participantes y lugar, pero comunica una acción diferente.

3. **Negación perdida y objeto cambiado — Jaccard**
   Fuente: `naku kava kuna nu vasi.`
   Referencia: «el niño no comparte la carta en el mercado.»
   Predicción: «el niño comparte el mapa en el mercado.»
   Jaccard no exige conservar ni el objeto ni la polaridad de la entrada.

La taxonomía automática compara campos del español controlado y se usa como
diagnóstico, no como métrica semántica universal. `errores.csv` conserva todos
los casos, incluidas las ablaciones, y `validacion_detalle.csv` conserva los 600
resultados de los cinco sistemas sobre las mismas 120 referencias.

## 9. Relación con el modelo estadístico del notebook 03

El bigrama de Eráviri modela la probabilidad de una fuente; el traductor actual
modela sus correspondencias y estructura. No se incorpora el LM como un factor
artificial de confianza o un supuesto selector de traducciones: para una misma
fuente, su probabilidad es la misma frente a cualquier candidato español.

El monolingüe ayudó a estudiar estructura y mejoró la estimación probabilística
en el experimento 03. El traductor completo **no** utiliza sus conteos. Por tanto,
no se afirma una mejora de traducción causada por el monolingüe. Una comparación
con y sin un componente que el sistema no usa sería una ablación vacía.

## 10. Expresiones oficiales y exportación

Un enrutador separado reconoce por coincidencia normalizada las 18 expresiones
oficiales y devuelve su traducción publicada. Conserva `?`: `seni?` no se confunde
con `seni`. La ruta `official_phrase_memory` se diferencia de `compositional`.
No se suman esos aciertos a la evaluación de validación: son memoria de ejemplos
conocidos, no una prueba de generalización conversacional. Se conservan las
alternativas oficiales como «Disculpa / Perdón» sin inventar una referencia única.

Se producen dos archivos independientes en la raíz:

- `predicciones.csv`: público original, 40 filas, columnas `id,prediccion`.
- `predicciones_fase5.csv`: fase 5, 40 filas, IDs `F5-...`.

Se comprueban tamaño, IDs únicos, predicciones no vacías, columnas y orden contra
cada archivo fuente. Hay copias y trazas estructurales en `resultados/traduccion_04/`.
No hay referencias para medir exactitud del público ni de fase 5; su cobertura
de análisis no se presenta como precisión verificada. No se mezclan los 80 mensajes.

## 11. Reproducibilidad, limitaciones y defensa

`traductor_composicional.json` guarda conteos léxicos y análisis de formas; puede
cargarse sin leer validación. No guarda una tabla de traducciones de validación.
Se registran versiones, configuración de métricas y hashes de los siete CSV.
El algoritmo es determinista; el baseline desempata por orden de entrenamiento.

Las limitaciones son el español y la gramática controlados, vocabulario cerrado,
conjugaciones observadas, una validación ya explorada y ausencia del test oculto.
Con una semana adicional estudiaríamos separación por composiciones más difícil,
formas verbales no observadas, evaluación independiente y alternativas neuronales
o probabilísticas de alineamiento, comparadas con este sistema interpretable.

El resultado cumple la comparación y las ablaciones solicitadas, pero el rigor
de la defensa depende de explicar por qué funciona aquí y dónde deja de estar
respaldado por evidencia. El miniinforme y el registro de herramientas acompañan
al notebook; la evaluación oficial sigue pendiente.

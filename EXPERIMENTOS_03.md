# 03 · Experimentos estadísticos y nuevos datos

Este cuaderno continúa el EDA con modelos de lenguaje de palabras en Eráviri.
Estima probabilidades de secuencias; todavía no traduce al español. Las cifras
se obtienen ejecutando `python -m lexicon.experimental`. Los gráficos se regeneran
con `python -m lexicon.experimental_plots` en un entorno con Matplotlib.
Los modelos y sus pruebas numéricas usan solo la biblioteca estándar.

## 1. Qué llegó en fase 5 y cómo cambia el problema

| Archivo nuevo | Filas | Función experimental |
|---|---:|---|
| Pistas léxicas | 21 | Evidencia oficial para contrastar correspondencias |
| Comunicación inicial de Noelia | 18 | Expresiones conversacionales con traducción |
| Nuevos mensajes de fase 5 | 40 | Entradas nuevas sin referencia española |

Las 21 pistas son consistentes con entrenamiento: cinco sujetos, seis objetos,
cuatro verbos presentes, tres lugares, negación y dos sufijos. No constituyen
21 oraciones nuevas ni añaden raíces nuevas al vocabulario original. Para
comparar lugares se homogeneiza la representación: la pista dice `en la casa`
y el lexicón inducido guarda `la casa`. El prefijo `en` se añade al generar español.

Los sufijos `-ta` y `-ri` conservan su guion como metadato. No deben pasar por
tokenización general y convertirse en falsas palabras independientes `ta`/`ri`.
El contraste de estas pistas confirma la consistencia de una hipótesis; no
equivale a medir una mejora de traducción. Se exporta el soporte en entrenamiento
de cada pista a `contraste_pistas.csv`.

Las 18 expresiones conversacionales introducen 15 formas fuente nuevas. De sus
26 ocurrencias léxicas, 25 están fuera del vocabulario del LM principal: solo
`nelo` ya era conocido. Además tienen estructuras como `salia neri` o `mira?`
que no siguen necesariamente la plantilla sujeto–objeto–verbo. `noku` es una
respuesta aislada «No»; no debemos sustituir por ella la negación oracional `nu`.
El `?` se conserva en los originales y será importante para un futuro módulo
de expresiones; el LM actual utiliza la tokenización de palabras del proyecto.

Las expresiones son pares oficiales disponibles, no un conjunto de prueba
independiente. Memorizar sus 18 traducciones no demostraría generalización.
Hay traducciones con alternativas, como `Disculpa / Perdón`, que necesitarían
una política de referencias múltiples si se evaluaran automáticamente.

**Decisión:** mantener tres roles separados. No mezclar pistas, saludos y
oraciones declarativas para aumentar artificialmente el tamaño del corpus.
Un futuro traductor puede tener un módulo de expresiones conocidas y otro
composicional; debe distinguir respuestas conocidas de mensajes no cubiertos.

## 2. Auditoría de los cuarenta mensajes nuevos

Los IDs son únicos y no hay fuentes idénticas a entrenamiento, validación,
monolingüe ni público original. No aparecen palabras nuevas respecto a los
420 pares; los 40 mensajes se pueden analizar con la hipótesis de estructura
obtenida de entrenamiento. Son compatibles con la gramática, no traducciones
ya verificadas.

En fase 5 hay 16 negaciones (40 %), 13 pasados (32,5 %), 13 futuros (32,5 %) y
20 lugares explícitos (50 %). En entrenamiento había 20,2 % de negaciones y
70,5 % de lugares. Es un cambio descriptivo relevante para probar robustez;
cuarenta ejemplos no bastan para inferir una distribución poblacional.

**Decisión:** no retocar reglas oración por oración ni inventar etiquetas. El
LM congelado puede asignar probabilidades a las fuentes, pero no medir exactitud
de traducción sin referencias. Fase 5 mantiene sus IDs `F5-...`; no se sustituye
el público original de 40 filas `NX-...` ni se sobrescribe su entrega.

## 3. Preguntas e hipótesis experimentales

H1: añadir orden local (bigrama) reduce perplejidad respecto a frecuencias sin
contexto (unigrama), evaluando los mismos mensajes y vocabulario.

H2: el trigrama podría mejorar al bigrama por su contexto adicional, pero sufre
escasez de observaciones; esta hipótesis puede ser refutada por los datos.

H3: el monolingüe ofrece mejor estimación de contextos que solo 420 fuentes
bilingües. Hay que comparar corpus con el modelo fijo y considerar el tamaño
muestral como explicación, no atribuir toda diferencia al origen de los datos.

H4: las expresiones conversacionales quedan fuera del dominio del LM declarativo;
su OOV debe informarse junto con su perplejidad.

No se usan las pistas para modificar las probabilidades ni las traducciones de
validación para entrenar. La condición principal excluye las fuentes públicas
exactas del monolingüe; la exposición transductiva se analiza por separado.

## 4. División de datos antes de ajustar modelos

Se excluyen del monolingüe las fuentes exactas del público original y de fase 5.
La intersección real es de 28 mensajes públicos y cero de fase 5. Quedan 2.972
oraciones. Con una permutación de semilla `20261014` se crean:

| Partición del LM | Oraciones | Uso |
|---|---:|---|
| Entrenamiento | 2.377 | Ajustar vocabulario y conteos |
| Desarrollo | 297 | Elegir parámetros y familia del modelo principal |
| Prueba | 298 | Evaluación reservada; no elige parámetros |

El manifiesto `particiones_lm.csv` conserva IDs y textos para reconstruir la
división. Se verifica ausencia de fuentes compartidas entre las tres partes.
Esta división no reemplaza los CSV bilingües originales.

El vocabulario se ajusta solo con las 2.377 fuentes de entrenamiento del LM:
59 formas léxicas. Se añaden `<unk>` y `</s>` como posibles predicciones: 61
símbolos en total. `<s>` representa inicio, es contexto y nunca se predice.
Se comprueba que el entrenamiento bilingüe contiene el mismo inventario para
comparar corpus con un vocabulario idéntico. No se amplía con desarrollo o prueba.

## 5. Qué calcula cada modelo

Unigrama: `P(palabra)`. Ejemplo: estima la probabilidad de `lomu` sin mirar
las palabras anteriores.

Bigrama: `P(palabra | anterior)`. Considera, por ejemplo, qué suele seguir a `nu`.

Trigrama: `P(palabra | dos anteriores)`. Tiene más contexto, pero reparte las
observaciones entre muchas más situaciones.

Se aplica suavizado aditivo:

```text
P(palabra | contexto) =
    (conteo(contexto, palabra) + alpha)
    / (conteo(contexto) + alpha × tamaño_del_vocabulario)
```

Alpha evita probabilidades cero. Demasiado suavizado hace las predicciones
más uniformes; demasiado poco penaliza mucho los contextos nuevos. Los
contextos que nunca se observaron tienen distribución uniforme en este modelo.

También se prueba interpolación: una media ponderada de probabilidades de
unigrama, bigrama y trigrama. Los pesos se eligen con desarrollo entre tres
alternativas, no se aprenden mirando la prueba.

Cada oración empieza con fronteras según el orden y termina en `</s>`. Nunca
se cuentan secuencias que crucen de una oración a otra. Las probabilidades
suman uno sobre los 61 símbolos de predicción para cualquier contexto.

`<unk>` recibe toda palabra no observada en entrenamiento. El suavizado reserva
probabilidad para él, incluso cuando no tiene ocurrencias de entrenamiento.
Como palabras distintas se colapsan a un solo símbolo, una perplejidad con muchos
OOV debe interpretarse con cautela y acompañarse de su tasa de desconocidos.

## 6. Diseño de comparación y búsqueda

Se prueban alpha `0.01, 0.05, 0.1, 0.5, 1.0`. El interpolado usa pesos
unigrama/bigrama/trigrama `(0.1,0.3,0.6)`, `(0.1,0.6,0.3)` y `(0.2,0.4,0.4)`.
Son 30 configuraciones por condición, 150 en total:

| Condición | Fuentes de entrenamiento | Propósito |
|---|---:|---|
| train_420 | 420 | Control con las fuentes bilingües originales |
| mono_clean | 2.377 | Experimento principal, sin exposición pública exacta |
| train_plus_mono | 2.797 | Añadir las 420 fuentes al monolingüe de entrenamiento |
| mono_transductive | 2.405 | Añadir las 28 fuentes públicas excluidas |
| mono_sample_420 | 420 | Control de tamaño: muestra solo de mono/train |

La muestra de 420 utiliza una semilla fija distinta (`20261015`) y no contiene
oraciones de desarrollo/prueba. Una sola muestra no permite estimar la
variabilidad entre muestras; este control es descriptivo.

Para cada familia y condición se eligen sus parámetros por menor perplejidad
de desarrollo. El modelo principal se elige entre las cuatro familias de
`mono_clean`, también usando exclusivamente desarrollo. No se reajusta con
desarrollo antes de medir prueba. Las otras condiciones responden preguntas
secundarias y no sustituyen al principal por obtener una cifra de prueba menor.

La perplejidad se calcula sobre todos los tokens predichos, incluyendo EOS:
`exp(suma de sorpresas / número total de tokens predichos)`. Se acumulan
logaritmos para evitar errores numéricos. No se promedian perplejidades de
oraciones, porque eso ponderaría incorrectamente sus distintas longitudes.

## 7. Resultados del experimento principal

| Modelo | Alpha elegido | Pesos uni/bi/tri | Desarrollo | Prueba |
|---|---:|---|---:|---:|
| Unigrama | 0,01 | — | 35,95 | 36,75 |
| Bigrama | 0,01 | — | **8,46** | **9,08** |
| Trigrama | 0,05 | — | 12,14 | 13,77 |
| Interpolado | 0,01 | 0,1 / 0,6 / 0,3 | 9,39 | 10,00 |

Se favorece H1: el orden local aporta mucho frente a frecuencias aisladas.
H2 no se sostiene en esta comparación: el trigrama no mejora al bigrama. La
escasez de contextos es una explicación compatible con el EDA, no una prueba
causal aislada. La interpolación recupera parte del desempeño del trigrama,
pero sigue detrás del bigrama en desarrollo.

**Decisión:** congelar como LM principal el bigrama aditivo con alpha 0,01.
Es la mejor opción del espacio explorado, no un óptimo universal. Su alpha
está en el borde inferior de la grilla; probar valores menores sería un nuevo
experimento de desarrollo y no debe justificarse mirando la prueba.

## 8. Aporte del corpus y control de factores

Comparar cada modelo con su mejor alpha cambiaría corpus e hiperparámetro a
la vez. Por eso se exporta además una comparación con **bigrama, alpha 0,01 y
vocabulario idénticos**:

| Corpus | Perplejidad de desarrollo | Perplejidad de prueba |
|---|---:|---:|
| 420 fuentes bilingües | 13,06 | 13,70 |
| 2.377 fuentes monolingües limpias | 8,46 | 9,08 |
| Bilingüe + monolingüe | 8,46 | 8,99 |
| Monolingüe + 28 entradas públicas | 8,46 | 9,08 |
| Muestra monolingüe de 420 | 11,58 | 12,17 |

El monolingüe resulta útil en este experimento. La comparación con una muestra
de 420 muestra que el volumen de datos también es un factor relevante. No se
afirma que un corpus sea intrínsecamente mejor a partir de una sola muestra.
Añadir las 420 fuentes al mono no mejora desarrollo; no se cambia de ganador
por su prueba ligeramente menor. Las diferencias pequeñas no se presentan
como mejoras estadísticamente significativas.

## 9. Diagnóstico de los archivos externos con el LM congelado

| Fuentes evaluadas | Oraciones | Perplejidad | OOV léxico |
|---|---:|---:|---:|
| Validación bilingüe, solo Eráviri | 120 | 8,82 | 0 % |
| Público original | 40 | 8,99 | 0 % |
| Fase 5 | 40 | 10,54 | 0 % |
| Expresiones conversacionales | 18 | 2.050,19 | 96,15 % |

Estas evaluaciones no eligen el modelo. La fase 5 tiene algo más de sorpresa
para este LM, pero eso no demuestra errores de traducción. Las traducciones de validación no se leen
para ajustar el LM; solo se usan las fuentes.

La conversación tiene otro dominio y casi todo su vocabulario es desconocido.
Su cifra no es un ranking justo de calidad de traducción frente a los otros
archivos. Un LM entrenado en saludos podría responder a otra pregunta, pero
dieciocho expresiones no ofrecen aquí una base robusta de entrenamiento y
evaluación independientes.

`scores_phase5.csv` identifica mensajes de mayor sorpresa media por token.
Es una ayuda para inspección lingüística. No es una puntuación calibrada de
confianza, ni sirve para decidir automáticamente qué traducción es correcta.

## 10. Qué queda listo y qué sigue pendiente

`modelo_principal.json` guarda vocabulario y conteos del modelo elegido. Se
puede cargar con `NGramLM.load` sin volver a entrenar ni leer los datos fuente.
El formato es JSON, sin dependencias binarias ni deserialización de código.

Queda implementado un LM de Eráviri con suavizado, interpolación, búsqueda de
parámetros, particiones reproducibles y evaluación separada. Los resultados
guardan versiones, semillas y hashes de todos los CSV. Los tests verifican
normalización de probabilidades, conteos manuales, fronteras, manejo de OOV,
consistencia de pistas y ausencia de fuentes compartidas en las particiones.

El próximo módulo debe aprender la relación Eráviri–español y compararse con
Jaccard. Un LM fuente no puede escoger por sí solo entre traducciones españolas
porque todas parten de la misma fuente. Si más adelante se usa un LM español
para ordenar candidatos, deberá demostrarse que mejora sin cambiar el sentido.

Para el traductor: conservar acción, participantes, lugar, negación y tiempo;
usar las pistas como evidencia declarada; tratar las expresiones oficiales
con una política explícita; evaluar exact match, chrF, fenómenos y combinaciones
nuevas. No se generó todavía `predicciones.csv` ni se inventaron referencias
para los 40 mensajes nuevos.

# EDA de Eráviri: evidencia y decisiones

Este análisis describe los archivos disponibles, no el test oculto. Es una
exploración de un idioma sintético controlado y no permite extrapolar resultados
a lenguas indígenas reales. El código reproducible está en `lexicon/eda.py`;
gráficos PNG/SVG, tablas y métricas en `resultados/eda/`. La galería autónoma
`resultados/eda/informe_visual.html` puede abrirse en el navegador sin internet.

## 1. Integridad y separación experimental

Se validan columnas, cantidades, campos no vacíos, IDs únicos dentro de cada
archivo y tokens no vacíos. Los originales no se modifican. Se conserva la
normalización Unicode NFC y no se eliminan negación, tildes ni sufijos.
Las fuentes se comparan después de normalizar espacios, minúsculas y puntuación
final. No hay duplicados de fuente dentro de cada partición ni contradicciones
de etiqueta para una misma fuente dentro de los bilingües disponibles.

El léxico, las categorías posicionales y el inventario de formas verbales se
obtienen **exclusivamente de entrenamiento**. La regla de segmentación temporal
es una hipótesis explícita comprobada allí, no un descubrimiento no supervisado
automático. Validación y público sirven para medir cobertura y patrones; ninguna
de sus traducciones entra en la inducción. Analizar validación sigue exponiendo
información sobre ella: no debe reutilizarse indefinidamente para elegir modelos.

## 2. Tamaño, longitud y cobertura

| Partición | Oraciones | Tokens fuente | Formas distintas | Longitud media |
|---|---:|---:|---:|---:|
| Entrenamiento | 420 | 1.641 | 59 | 3,91 |
| Validación | 120 | 462 | 58 | 3,85 |
| Monolingüe | 3.000 | 11.663 | 59 | 3,89 |
| Público | 40 | 157 | 46 | 3,93 |

Las oraciones tienen entre tres y cinco tokens fuente. El español necesita más
tokens porque explicita artículos, preposiciones y otra posición del verbo.
Por ello no se debe asumir alineamiento palabra a palabra por el mismo índice.

No hay tokens fuente desconocidos en validación, monolingüe ni público respecto
a entrenamiento. Tampoco hay palabras españolas desconocidas en validación.
Entrenamiento tiene cero formas fuente que aparezcan una sola vez; validación
tiene nueve, pero eso describe su tamaño muestral, no rareza en entrenamiento.

Las curvas de vocabulario muestran saturación rápida: con 100 oraciones
aleatorias de entrenamiento se observan en promedio 56,05 de las 59 formas;
con 200, 58,65. Se usan 20 permutaciones con semilla fija. La banda muestra
variación por orden de muestreo; **no** es un intervalo de confianza poblacional.
El monolingüe aporta más contextos, pero ninguna forma superficial nueva.

**Decisión:** tokenización por palabras para el primer modelo de lenguaje.
No hay evidencia aquí que justifique introducir BPE, quitar stopwords o aplicar
stemming. Conservar las formas superficiales permite comparar después contra
una representación morfológica como ablación.

## 3. Estructura y correspondencias

Los 420 pares de entrenamiento son compatibles con:

```text
Eráviri: SUJETO OBJETO [LUGAR] [nu] VERBO
Español: SUJETO [no] VERBO OBJETO [en LUGAR]
```

Se observan diez sujetos, doce objetos, seis lugares, diez raíces verbales con
tres formas cada una y `nu`. Las correspondencias dentro de cada categoría no
presentan conflictos en entrenamiento. `lexico_train.csv` registra traducción
y soporte de cada forma para que la afirmación sea auditable.

La gramática propuesta logra analizar 420/420 fuentes de entrenamiento,
120/120 de validación, 3.000/3.000 monolingües y 40/40 públicas. Esto verifica
compatibilidad con una hipótesis de estructura; **no mide precisión de traducción**.
El analizador rechaza entradas fuera de ella en vez de inventar una interpretación.

Hay cuatro plantillas. En entrenamiento: `S O V` tiene 95 casos; `S O NEG V`,
29; `S O L V`, 240; `S O L NEG V`, 56. La concentración de cada forma en primera,
segunda, intermedia o última posición da evidencia para separar categorías.

**Decisión:** aprender vocabulario y estructura por separado. Un traductor que
recupere frases completas no puede aprovechar directamente esa composición.
La evidencia posicional respalda un traductor composicional como comparación
principal, aunque todavía falta implementar y evaluar su traducción completa.

## 4. Morfología: corregir la regla antes de contar

No basta `endswith('ri')` para clasificar futuro: **kori es presente** (“guarda”).
Su futuro es `koriri`. La segmentación exige que al quitar `ta` o `ri` exista
la raíz verbal en el inventario aprendido de entrenamiento. Las correspondencias
españolas de las formas confirman allí la interpretación temporal.

| Fenómeno | Entrenamiento | Validación | Monolingüe | Público |
|---|---:|---:|---:|---:|
| Negación | 85 (20,2 %) | 17 (14,2 %) | 574 (19,1 %) | 8 (20,0 %) |
| Pasado | 73 (17,4 %) | 16 (13,3 %) | 592 (19,7 %) | 4 (10,0 %) |
| Futuro | 87 (20,7 %) | 22 (18,3 %) | 578 (19,3 %) | 7 (17,5 %) |
| Lugar explícito | 296 (70,5 %) | 85 (70,8 %) | 2.089 (69,6 %) | 29 (72,5 %) |

Las categorías se solapan; no deben sumarse como clases excluyentes. Las
diferencias en público son inestables por tener solo 40 casos. No hay base para
afirmar un cambio poblacional a partir de esos porcentajes.

**Corrección del análisis inicial:** validación tiene 22 futuros, no 28; la
cuenta anterior incluía `kori`. El EDA actual y sus pruebas usan la segmentación
condicionada por el inventario de raíces.

**Decisión:** conservar negación y tiempos como dimensiones explícitas de
evaluación. Las 30 formas verbales tienen soporte en entrenamiento, pero no
uniforme: algunas aparecen solo cuatro veces. Un modelo debe demostrar que
mantiene la acción y el tiempo al combinar otros participantes.

## 5. Generalización: medir más que palabras y parejas

Entrenamiento cubre 106 de las 120 parejas sujeto–objeto posibles dentro de su
inventario, 93/100 sujeto–raíz y 119/120 objeto–raíz. Cubrir casi todas las
parejas no significa haber visto la oración completa.

| Combinación ausente de entrenamiento | Validación | Público |
|---|---:|---:|
| Sujeto–objeto | 4/120 | 0/40 |
| Objeto–raíz verbal | 2/120 | 2/40 |
| Lugar–raíz verbal | 1/120 | 1/40 |
| Sujeto–objeto–raíz verbal | 87/120 (72,5 %) | 34/40 (85,0 %) |
| Objeto–lugar–raíz verbal | 64/120 (53,3 %) | 20/40 (50,0 %) |
| Raíz–tiempo–negación | 1/120 | 0/40 |
| Configuración completa | 120/120 | 40/40 |

La ausencia de lugar se representa como `∅` para estas combinaciones. Las filas
se pueden solapar y no deben sumarse. La configuración completa incluye sujeto,
objeto, lugar/ausencia, negación, raíz y tiempo.

**Decisión:** definir “combinación nueva” de forma operacional. Usar la terna
sujeto–objeto–raíz como corte principal y los otros como análisis secundarios.
No llamar “OOD léxico” a estos conjuntos: no tienen vocabulario fuente nuevo.
Tampoco afirmar un cambio de distribución demostrado por la mera novedad de
la oración. El test oculto puede contener condiciones diferentes.

## 6. Qué aporta el monolingüe al modelo probabilístico

Se cuentan n-gramas con fronteras de oración: para orden n se añaden n−1
marcadores `<s>` al inicio y un `</s>` al final. No se cuentan secuencias que
crucen de una oración a otra. La medida siguiente pondera **ocurrencias**, no
tipos distintos, e incluye esos marcadores de frontera.

| Partición evaluada | Bigramas no vistos en train | Trigramas no vistos en train |
|---|---:|---:|
| Validación | 6,87 % | 35,57 % |
| Público | 6,09 % | 35,03 % |

Con el monolingüe como referencia, los trigramas no observados bajan al 10,82 %
en validación. Esto muestra cobertura contextual adicional, pero no prueba
todavía una mejora en perplejidad ni en traducción. Un modelo sin suavizado
asignaría probabilidad cero a contextos no vistos.

**Decisión:** comparar unigramas, bigramas y trigramas suavizados, sin asumir que
el orden más alto será mejor. Introducir fronteras y una política explícita
para `<unk>`. Elegir suavizado e hiperparámetros con una partición de desarrollo
del monolingüe; reservar su prueba para una evaluación final de perplejidad.
No utilizar validación bilingüe como banco ilimitado de ajustes del LM.

## 7. Coincidencias y protocolo recomendado

No hay fuentes compartidas entre entrenamiento, validación y público. Tampoco
hay fuentes de entrenamiento/validación en monolingüe. Sí aparecen 28/40 fuentes
públicas dentro del monolingüe. No llevan traducciones españolas; la exposición
es transductiva, no evidencia por sí sola de fuga de etiquetas.

El diagnóstico recalcula también la cobertura eliminando esas 28 fuentes del
monolingüe: quedan **2.972 oraciones**. En público, los trigramas no observados
pasan de 4,06 % con mono completo a 14,21 % con mono sin público. La coincidencia
exacta influye en esa medida y conviene hacer visible su efecto.

**Decisión:** usar como experimento principal del LM el monolingüe sin las
fuentes públicas exactas, con división reproducible entrenamiento/desarrollo/
prueba. Conservar el uso de mono completo como condición transductiva separada,
sin atribuir su ventaja a generalización completamente inédita. No borrar
físicamente ninguna fila de los CSV originales.

La divergencia Jensen–Shannon de frecuencias fuente respecto a entrenamiento es
0,0057 bits para monolingüe, 0,0301 para validación y 0,0787 para público. Es una
comparación descriptiva en [0,1], no una prueba de significancia; el tamaño
reducido del público puede aumentar la variación de sus frecuencias.

## 8. Experimento que sigue

1. Congelar este preprocesamiento y la definición de combinaciones nuevas.
2. Separar el monolingüe sin fuentes públicas con semilla 20261014 y verificar
   que no haya fuentes idénticas entre sus particiones.
3. Ajustar vocabulario del LM solo con su entrenamiento; reservar `<unk>` para
   los tokens que no entren en él, aunque el EDA global conozca el inventario.
4. Entrenar unigramas, bigramas y trigramas; seleccionar suavizado en desarrollo.
5. Reportar perplejidad sobre exactamente los mismos tokens, vocabulario y
   tratamiento de fronteras. La perplejidad entre lenguas/tokenizaciones distintas
   no es una comparación justa. No confundir perplejidad con exactitud de traducción.
6. Implementar el traductor bilingüe por separado. Medir exact match, chrF,
   fenómenos y ternas conocidas/nuevas; luego estudiar si el LM realmente ayuda.

Se prefirieron gráficos de proporciones, soporte, cobertura y estructura a una
nube de palabras o una proyección de embeddings: responden directamente a las
decisiones del caso. No se entrenó aún un LM ni un segundo traductor; este EDA
deja formuladas las decisiones y condiciones para evaluarlos honestamente.

# An?lisis del proyecto LEXICON-X

Fecha: 14 de octubre de 2026. Alcance: enunciado completo, imagen del caso aportada, notebook principal, cuatro CSV, seis notebooks en total y archivos auxiliares de material_previo. Se ejecutaron en memoria las celdas de carga, exploraci?n, baseline, propuesta y errores del notebook principal. No se entrenaron los modelos de los talleres, no se descargaron modelos externos y no se generaron predicciones de entrega. Los notebooks originales y los datos no se modificaron.

## 1. Qu? pide realmente el caso

Es un experimento de traducci?n autom?tica de pocos recursos, del idioma sint?tico Er?viri al espa?ol. La pregunta central es qu? estrategia generaliza a combinaciones nuevas con pocos pares biling?es. No es una tarea de clasificaci?n, sentimiento ni generaci?n libre. El ?xito incluye evidencia ling??stica, hip?tesis falsable, baseline, segundo m?todo, comparaci?n, ablaci?n, errores y reproducibilidad; una puntuaci?n alta aislada no satisface el enunciado.

Los roles son ling??stica computacional, modelos y validaci?n/comunicaci?n. Todos deben defender el sistema completo. Hay tres consultas oficiales a Noelia: cada una requiere un hallazgo propio y una pregunta concreta. No se permite consultar archivos privados del docente ni corregir validaci?n frase por frase. Los modelos externos, internet y asistentes est?n permitidos si se declaran. Las conclusiones sobre este idioma sint?tico no se extrapolan a lenguas ind?genas reales.

La entrega del minuto 155 incluye: notebook con entrenamiento/inferencia, semilla y dependencias; predicciones.csv con columnas id,prediccion y 40 filas en el orden p?blico; miniinforme de hasta dos p?ginas o cuatro diapositivas; registro de herramientas y limitaciones. La evaluaci?n oculta es distinta de los 40 ejemplos p?blicos. El reto del minuto 130 est? clasificado: su contenido no puede deducirse del repositorio.

La r?brica asigna 20 puntos a investigaci?n, 25 a implementaci?n/reproducibilidad, 25 a comparaci?n/ablaci?n, 15 a generalizaci?n y 15 a defensa. Por ello, la mitad de los puntos depende directamente de implementaci?n y experimentaci?n, y el resto exige investigaci?n defendible.

## 2. Inventario y estado real

- ENUNCIADO.md: especificaci?n del trabajo y reglas.
- LEXICON_X_Colab.ipynb: plantilla de 13 celdas, sin ejecuciones ni resultados guardados.
- datos/: los cuatro conjuntos est?n presentes y tienen las cantidades anunciadas.
- assets/portada.png: presentaci?n narrativa del caso.
- README.md: ?nicamente t?tulo NLP y texto Actividad; no explica instalaci?n ni ejecuci?n.
- material_previo/C4: clasificaci?n de pel?culas con FFNN y ejemplo de lenguaje con RNN; incluye train_data.txt (54.214 l?neas) y SpamData.csv.
- material_previo/C5: etiquetado POS con LSTM/BiLSTM y ejemplo seq2seq ingl?s-franc?s.
- material_previo/C7: generaci?n con DistilGPT2, taller BERT/RoBERTa y cuatro archivos espa?ol/shiwilu.
- material_previo/C8: otro taller BERT/RoBERTa.

Los materiales previos son referencias educativas, no una implementaci?n del traductor Er?viri. No hay segundo m?todo real, ablaci?n implementada, miniinforme, registro de herramientas ni manifiesto de dependencias. El archivo de predicciones tampoco estaba presente.

## 3. Auditor?a de datos

| Conjunto | Filas | Fuentes ?nicas | Vocabulario fuente | Longitudes de 3/4/5 tokens |
|---|---:|---:|---:|---|
| Entrenamiento | 420 | 420 | 59 | 95 / 269 / 56 |
| Validaci?n | 120 | 120 | 58 | 30 / 78 / 12 |
| Monoling?e | 3.000 | 3.000 | 59 | 736 / 1.865 / 399 |
| P?blico | 40 | 40 | 46 | 11 / 21 / 8 |

Se encontraron cero campos vac?os y cero identificadores repetidos dentro de cada archivo. Los biling?es usan id,naviri,espanol; los otros, id,naviri. El nombre de columna es naviri aunque el caso se llama Er?viri: debe respetarse en c?digo.

No hay fuentes id?nticas entre entrenamiento y validaci?n, entrenamiento y p?blico, ni validaci?n y p?blico. El monoling?e tampoco coincide con las fuentes de entrenamiento o validaci?n. S? contiene 28 de las 40 fuentes p?blicas. Esto permite exposici?n no supervisada a entradas p?blicas y debe declararse como condici?n transductiva; no proporciona sus traducciones ni demuestra por s? solo una fuga de etiquetas. No se debe afirmar que esas 28 fuentes son completamente in?ditas para un sistema que usa todo el monoling?e.

Todos los tokens de validaci?n, monoling?e y p?blico est?n en entrenamiento. En los conjuntos disponibles, el reto l?xico no consiste en palabras desconocidas: consiste principalmente en recombinar elementos conocidos. No sabemos si el test oculto conserva esa condici?n. Los identificadores se reinician entre archivos, por lo que no son claves globales y no deben usarse para unir traducciones entre particiones.

## 4. Evidencia ling??stica

El an?lisis de los 420 pares de entrenamiento respalda la estructura:

    SUJETO OBJETO [LUGAR] [nu] VERBO

La realizaci?n espa?ola observada sigue:

    SUJETO [no] VERBO OBJETO [en LUGAR]

Se identifican 10 sujetos, 12 objetos, 6 lugares, 10 ra?ces verbales con 3 formas cada una y la part?cula nu: 59 formas superficiales. Las correspondencias extra?das por posici?n son consistentes en los 420 pares; no se observaron traducciones diferentes para una misma forma dentro de su categor?a. Esto describe la evidencia disponible, no una garant?a sobre cualquier mensaje futuro.

Ejemplos de entrenamiento:

- vonu pira hala yelo. ? el viajero elige el agua en la casa.
- penu moru kuna dema. ? el guardi?n lleva el mapa en el mercado.
- vonu zura miri nu lomuta. ? el viajero no busc? la llave en el bosque.
- yami rima pavo demari. ? la estudiante llevar? la flor en el laboratorio.

Las formas sin sufijo corresponden al presente observado; -ta al pasado y -ri al futuro. Ejemplo: dema/lleva, demata/llev?, demari/llevar?. La negaci?n nu precede al verbo fuente y corresponde a no antes del verbo espa?ol. El lugar aparece entre objeto y negaci?n/verbo; hala corresponde a la casa, kuna al mercado, miri al bosque, pavo al laboratorio, rilo al r?o y sova a la escuela.

No basta concatenar una traducci?n de ra?z con una terminaci?n espa?ola: hay formas como elige/eligi?/elegir? y encuentra/encontr?/encontrar?. Art?culos y tildes tambi?n importan para exact match. Aprender unidades como el agua evita errores por reglas simplistas de g?nero.

Una hip?tesis falsable apropiada ser?a: un sistema que separa vocabulario, estructura y tiempo verbal logra mayor exact match en validaci?n que la recuperaci?n de frases completas. Otra: retirar la transformaci?n de orden o el manejo de negaci?n reduce el desempe?o en los subconjuntos afectados. Su comprobaci?n requiere implementar y medir; todav?a no se ha hecho.

## 5. Resultado real del notebook principal

Las celdas de carga, exploraci?n, baseline, propuesta y errores se ejecutaron en memoria sin dependencias externas.

| Sistema actual | Aciertos | Exact match de validaci?n |
|---|---:|---:|
| Recuperaci?n Jaccard | 0/120 | 0 % |
| my_translate actual | 0/120 | 0 % |

La propuesta llama directamente a baseline_translate: no constituye un segundo enfoque. El baseline selecciona un par de entrenamiento por Jaccard de conjuntos de tokens y copia su traducci?n. Pierde orden, ignora multiplicidad y resuelve empates por el primer ejemplo encontrado. Como no compone traducciones y las fuentes de validaci?n no est?n en entrenamiento, puede parecer cercano sin producir una traducci?n id?ntica. El 0 % observado no significa que no reconozca ning?n contenido; faltan m?tricas complementarias para medir semejanza parcial.

Tres errores ejecutados:

1. telu tavi nemi.: referencia el maestro recuerda el alimento.; predicci?n el maestro recuerda la carta. Mantiene sujeto y verbo pero cambia objeto.
2. vonu suni rilo kori.: referencia el viajero guarda el libro en el r?o.; predicci?n el viajero elige el libro en el r?o. Cambia la acci?n.
3. naku kava kuna nu vasi.: referencia el ni?o no comparte la carta en el mercado.; predicci?n el ni?o comparte el mapa en el mercado. Cambia objeto y elimina negaci?n, un error sem?ntico importante para comunicaci?n.

En validaci?n hay 17 oraciones negativas, 16 pasadas, 22 futuras y 85 con lugar; las categor?as se solapan. El baseline obtiene cero exact matches en cada subconjunto. La plantilla muestra hasta cinco errores pero no implementa an?lisis por fen?meno. chrF est? solamente comentado: no hay un resultado calculado y no debe reportarse uno como si existiera.

## 6. Problemas concretos y discrepancias

1. La normalizaci?n implementada elimina puntuaci?n en cualquier posici?n; el enunciado pide eliminar puntuaci?n final. Tambi?n importa unicodedata pero no aplica normalizaci?n Unicode. Conviene fijar una funci?n que refleje exactamente el protocolo y usarla para todos los m?todos.
2. El notebook pide al menos dos hip?tesis; el enunciado exige una hip?tesis falsable. Se pueden cumplir ambos formulando dos.
3. El enunciado dice que el paquete no incluye datasets, pero los cuatro CSV s? est?n presentes: es una nota desactualizada.
4. La portada anuncia cinco equipos y cuatro minutos por presentaci?n; el texto del cronograma habla de cuatro defensas de cinco minutos, y la secci?n final de cinco minutos por equipo. Cinco equipos por cinco minutos consumen todos los 25 minutos y no dejan discusi?n. La organizaci?n debe aclararlo.
5. El notebook menciona ejecutar desde estudiantes/, carpeta que no existe aqu?. La ruta relativa datos/ s? funciona desde la ra?z.
6. La exportaci?n escribe filas pero no comprueba expl?citamente tama?o, unicidad, correspondencia de IDs ni predicciones no vac?as. Deben a?adirse validaciones antes de entregar.
7. La semilla est? definida, pero no hay versiones de entorno ni instrucciones completas. Si se incorporan redes, la semilla de random sola no controla NumPy ni el framework.
8. El README no permite reproducir el proyecto sin leer las celdas.

## 7. Revisi?n de los talleres anteriores

C4 ense?a representaci?n y clasificaci?n, pero su tokenizaci?n ocurre antes de dividir datos, por lo que el vocabulario utiliza informaci?n del conjunto de evaluaci?n. En la clasificaci?n resta uno a los ?ndices antes de Embedding: el padding cero pasa a -1, fuera del rango esperado. En el ejemplo RNN el entrenamiento usa ventanas de cinco tokens, mientras generate_text rellena a sequence_length, definido como seis: hay una discrepancia entre contexto de entrenamiento e inferencia. No debe copiarse sin corregir.

C5 es el material m?s cercano por contener seq2seq, pero su entrenamiento alimenta el decoder con y_train y lo eval?a contra el mismo y_train sin desplazar un token. El decoder puede aprender a copiar el token que recibe, en vez de predecir el siguiente. La validaci?n tambi?n recibe la secuencia objetivo completa. Adem?s, el tokenizador transforma START, mientras la inferencia busca literalmente '<START> ' y cae en el valor por defecto; la reconstrucci?n usa posiciones de una lista de claves en vez de un mapa ?ndice?palabra y no maneja correctamente el ?ndice de padding. El etiquetado POS tambi?n resta uno y presenta problemas de padding/?ndices. Estas observaciones se derivan del c?digo; no se entren? el taller para cuantificar su efecto.

C7 muestra generaci?n de texto y clasificaci?n/representaciones; no implementa traducci?n Er?viri. Algunas celdas con top-k/top-p son markdown que contienen c?digo, por lo que no se ejecutan como ejemplos activos. Los archivos espa?ol/shiwilu tienen 385 l?neas por archivo y los sint?ticos 1.000. Coincidir en cantidad no verifica alineaci?n ni calidad. Se observan frases sint?ticas como ellos lee un libro. No deben mezclarse con Er?viri ni tratarse como datos biling?es del caso.

C8 carga train.csv y test.csv, archivos que no est?n en el repositorio. Depende adem?s de descargas y modelos externos. Los talleres tienen salidas guardadas, pero eso no prueba que hoy se ejecuten de principio a fin. No se valid? compatibilidad con versiones actuales de sus bibliotecas.

## 8. Dise?o experimental propuesto

La opci?n inicial m?s justificada por estos datos es comparar el baseline obligatorio con un traductor composicional aprendido de entrenamiento: lexicones por categor?a, an?lisis de posiciones y marcadores, generaci?n espa?ola con orden y conjugaci?n controlados. Es una propuesta basada en la regularidad observada, no un resultado de rendimiento ya demostrado. Una red peque?a puede servir como comparaci?n adicional si queda tiempo, pero no es requisito del enunciado.

Para mantener rigor: inducir reglas y l?xico con entrenamiento; reservar validaci?n para contrastar decisiones metodol?gicas; no a?adir correcciones espec?ficas por oraci?n; congelar el m?todo antes de generar el p?blico. Si se seleccionan muchas alternativas, crear una partici?n interna de entrenamiento para reducir sobreajuste a validaci?n.

El monoling?e puede apoyar frecuencias, clases distribucionales y patrones de posici?n, pero no aporta traducciones espa?olas por s? solo. Dado que entrenamiento ya cubre las 59 formas, podr?a no mejorar el resultado. Debe medirse con/sin monoling?e manteniendo lo dem?s constante y aceptar una diferencia nula. Si el m?todo no utiliza monoling?e, declararlo; no atribuirle beneficios ficticios.

Comparaci?n m?nima: baseline, m?todo completo y una ablaci?n que retire un ?nico componente. Reportar exact match normalizado y chrF con configuraci?n y versi?n; desglosar negaci?n, tiempos y locativo. Definir OOD de forma operativa mediante combinaciones ausentes de entrenamiento, no mediante la mera ausencia de la oraci?n completa ni por intuici?n.

La ablaci?n de sufijos debe retirar el tratamiento temporal sin modificar simult?neamente l?xico ni orden. Una variante sin reordenamiento permite estudiar estructura. Si se obtuviera exactitud perfecta en estos datos, seguir?an siendo necesarias la ablaci?n, las limitaciones y la evaluaci?n oculta; se pueden analizar errores del baseline sin inventar fallos del sistema propuesto.

## 9. Prioridades para completar la entrega

1. Documentar hip?tesis y tres observaciones con ejemplos de entrenamiento.
2. Implementar el segundo m?todo separando inducci?n, traducci?n y evaluaci?n.
3. Alinear normalizaci?n con el enunciado e incorporar chrF y desglose por fen?meno.
4. Ejecutar una ablaci?n controlada y analizar tres errores concretos.
5. Verificar ejecuci?n completa desde un entorno limpio con versiones declaradas.
6. Generar predicciones.csv y validar exactamente 40 filas, columnas, IDs y orden.
7. Redactar miniinforme y registro de IA/herramientas; explicar cruces con monoling?e y l?mites de generalizaci?n.

El repositorio es un punto de partida educativo coherente con el caso, pero todav?a no una investigaci?n ni una entrega completa. Su principal oportunidad es explotar y comprobar la composici?n ling??stica; sus principales riesgos actuales son presentar el baseline como segundo m?todo, copiar errores de los talleres y confundir cobertura de vocabulario con generalizaci?n estructural.


Actualizacion EDA: el conteo temporal distingue la raiz kori del sufijo de futuro. Validacion tiene 22 futuros, no 28. Consultar EDA_CORPUS.md y resultados/eda/metricas.json para el analisis actualizado y sus graficos.

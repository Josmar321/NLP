# LEXICON-X · Eráviri → español

Guion completo de exposición de las cuatro etapas, con gráficas, notas orales,
preguntas de defensa y recorrido de cinco minutos: [PRESENTACION.MD](PRESENTACION.MD).

Etapas implementadas: preprocesamiento, EDA, modelos estadísticos de lenguaje
y traducción composicional Eráviri–español. Se incluyen evaluación, tres
ablaciones y predicciones separadas del público y de fase 5.

## Ejecución local en Windows

Abrir esta carpeta en VS Code. Desde PowerShell en la raíz:

```powershell
python -m lexicon.preprocessing
python -m unittest discover -s tests -p test_preprocessing.py -v
```

El preprocesamiento usa únicamente la biblioteca estándar de Python 3.10 o
superior. La versión ejecutada queda registrada en la auditoría. Para los
notebooks seleccionar un kernel con Jupyter/ipykernel. Si hace falta instalarlo:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install jupyterlab ipykernel
.\.venv\Scripts\python -m jupyterlab
```

Abrir `01_Preprocesamiento.ipynb`, después `02_EDA_Corpus.ipynb` y
`03_Experimental.ipynb` y `04_Traduccion.ipynb`.
`LEXICON_X_Colab.ipynb` conserva la plantilla inicial del baseline.
Los notebooks encuentran la raíz desde cualquier subcarpeta del repositorio;
no fijan una letra de unidad ni una ruta de usuario. Para Colab, subir o clonar
el repositorio completo y situarse dentro de él.

## EDA y gráficos

```powershell
python -m pip install -r requirements-eda.txt
python -m lexicon.eda
python -m unittest discover -s tests -v
```

Las dependencias se instalan en el entorno Python activo. El módulo no carga
`.deps/`: esa carpeta histórica contiene binarios de otro intérprete y no debe
añadirse a `sys.path`. El notebook 02 incluye una celda `%pip` para instalar en
el kernel seleccionado. Tras un error de NumPy con la versión anterior,
reiniciar el kernel y ejecutar el notebook desde el inicio.
El comando genera diez figuras en PNG y SVG, tablas CSV, `metricas.json` y una
galería HTML autónoma en `resultados/eda/`. Las versiones, semilla y hashes de
los CSV quedan registrados en las métricas. Los gráficos se pueden regenerar
sin descargar modelos. Las interpretaciones y decisiones están en
`EDA_CORPUS.md`. El notebook 02 presenta las figuras y el análisis por etapas.

El EDA corrige un conteo inicial de tiempos: `kori` es presente; solo se trata
`-ri` como futuro cuando se reconoce una raíz verbal. Hay 22 futuros en
validación. El protocolo propuesto para el LM separa una condición sin fuentes
públicas exactas de otra transductiva con todo el monolingüe.

## Experimentos 03 y datos de fase 5

```powershell
python -m lexicon.experimental
python -m lexicon.experimental_plots
python -m unittest discover -s tests -v
```

`03_Experimental.ipynb` presenta la auditoría de los tres archivos nuevos y
150 configuraciones de unigramas, bigramas, trigramas e interpolación. La selección
usa desarrollo; prueba queda separada. El protocolo principal excluye del
monolingüe las fuentes públicas exactas. Las pistas se contrastan contra
entrenamiento y las expresiones conversacionales se estudian como otro dominio.

Los resultados, particiones, puntuaciones por oración, cinco gráficos y
`modelo_principal.json` quedan en `resultados/experimental_03/`. El modelo se
puede cargar sin repetir el entrenamiento:

```python
from lexicon.ngram import NGramLM
lm = NGramLM.load('resultados/experimental_03/modelo_principal.json')
lm.evaluate([['vonu', 'zura', 'miri', 'nu', 'lomuta']])
```

La explicación de métodos, resultados y limitaciones está en
`EXPERIMENTOS_03.md`. La perplejidad mide probabilidad de Eráviri, no precisión
de traducción.

## Traducción y entrega del notebook 04

```powershell
python -m pip install -r requirements-traduccion.txt
python -m lexicon.translation
python -m lexicon.translation_plots
python -m unittest discover -s tests -v
```

El notebook 04 incluye las mismas operaciones y la instalación en el kernel.
Aprende el léxico solo de los 420 pares, compara Jaccard con reglas composicionales
y evalúa ablaciones de tiempo, negación y orden. Exporta en la raíz:

- `predicciones.csv`: 40 mensajes del público original, columnas `id,prediccion`.
- `predicciones_fase5.csv`: 40 mensajes de fase 5, independientes del público.

Métricas, errores, trazas, gráficos y modelo JSON están en
`resultados/traduccion_04/`. El informe técnico es `TRADUCCION_04.md`;
`MINIINFORME.md` tiene cuatro diapositivas en Markdown compatible con Marp;
`REGISTRO_HERRAMIENTAS.md` declara herramientas, IA y limitaciones.
No hay referencias públicas para verificar las predicciones del test o fase 5.

## Política de preprocesamiento

- Los CSV originales permanecen intactos; se conservan IDs y orden.
- Normalización Unicode NFC, minúsculas y espacios uniformes.
- Tokenización separando puntuación, conservando tildes, negación y sufijos.
- Sin eliminación de stopwords, stemming ni lematización.
- Vocabulario de referencia ajustado únicamente con entrenamiento.
- Exact match quita solo puntuación final; conserva puntuación interna.
- Auditoría de fuentes repetidas, cruces y vocabulario desconocido.

Se exportan cuatro JSONL con originales y derivados y `auditoria.json` en
`resultados/preprocesamiento/`. No se generan traducciones. Los 28 mensajes
públicos presentes en monolingüe no tienen etiquetas españolas; esa exposición
debe declararse. El contrato valida cantidades y columnas del enunciado.

## Notebooks previos

Los cinco notebooks de `material_previo/` tienen rutas adaptadas, pero requieren
sus propias dependencias (TensorFlow, pandas, scikit-learn, NLTK o
Transformers/PyTorch/datasets según el taller). No se instalaron ni entrenaron
esos modelos durante la adaptación. Algunas celdas necesitan internet.

C8 espera AG News en `material_previo/C8/train.csv` y `test.csv`, ausentes en
este repositorio; ahora muestra un error descriptivo. No sustituirlos por los
CSV Eráviri. Los problemas metodológicos de los talleres están documentados en
`ANALISIS_PROYECTO.md`; la adaptación de rutas no corrige sus modelos.

La plantilla `LEXICON_X_Colab.ipynb` conserva Jaccard y `my_translate` pendiente.
Su exportación de ejemplo escribe `resultados/predicciones_baseline.csv`, que
no es la entrega del notebook 04. Para la entrega usar el `predicciones.csv`
de la raíz, generado por `04_Traduccion.ipynb`.

Se utilizó asistencia de IA (Codex) para revisión, código y documentación.
No se utilizaron modelos externos de traducción ni archivos privados del docente.

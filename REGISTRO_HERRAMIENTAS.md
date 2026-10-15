# Registro de herramientas y limitaciones

- **Asistencia de IA:** Codex/ChatGPT para análisis, implementación, revisión,
  pruebas y documentación. Los resultados cuantitativos se calcularon ejecutando
  el código local; deben poder reproducirse sin consultar al asistente.
- **Python:** ejecución de referencia 3.14.3 en Windows. Preprocesamiento,
  conteos, modelos de n-gramas y traducción composicional usan biblioteca estándar.
- **Matplotlib:** 3.11.2 en la ejecución de referencia; genera gráficos PNG/SVG.
  Su dependencia NumPy se usa para visualización y por bibliotecas externas,
  no para entrenar redes neuronales.
- **sacrebleu:** 2.6.0 para chrF, orden de caracteres 6, beta 2, sin n-gramas de
  palabras. Firma y preprocesamiento registrados en las métricas del notebook 04.
- **Modelos externos:** no se descargaron ni usaron modelos preentrenados de
  traducción o generación para resolver el caso. Los talleres previos que los
  mencionan no constituyen entrenamiento del sistema entregado.
- **Datos:** cuatro CSV originales y tres CSV oficiales de `evento_fase_5`.
  No se buscaron ni utilizaron archivos privados del docente. Las pistas se
  contrastan contra entrenamiento; las expresiones oficiales se usan solo en
  una memoria separada. Los CSV originales se conservan intactos.
- **Entornos:** los notebooks instalan dependencias con `%pip` en su kernel.
  La carpeta histórica `.deps` contiene binarios de la ejecución de referencia;
  ningún módulo del proyecto la añade automáticamente a `sys.path`. No debe
  copiarse como entorno portátil entre versiones de Python.

## Limitaciones declaradas

La lengua es sintética y el corpus sigue plantillas regulares. La validación fue
explorada en el EDA; no es una prueba ciega. No hay palabras nuevas en los
conjuntos declarativos públicos disponibles y las 30 formas verbales aparecen
en entrenamiento. El sistema rechaza vocabulario o estructuras no cubiertos.
Las 18 expresiones conversacionales no son un benchmark independiente.

El monolingüe contiene 28 fuentes públicas exactas, sin traducciones. El modelo
de lenguaje principal las excluye y las condiciones transductivas se informan
por separado. El traductor del notebook 04 no usa conteos del monolingüe ni
del LM; no se afirma una mejora de traducción producida por ellos.

Las traducciones del público y fase 5 son predicciones sin referencia disponible.
La evaluación oficial oculta está pendiente. Los resultados no se extrapolan a
lenguas indígenas reales.

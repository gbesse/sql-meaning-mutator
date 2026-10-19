# SQL Meaning Mutator

[Français](README.md) · [English](README.en.md)

**Una consulta SQL puede pasar una prueba y duplicar los ingresos. Este laboratorio produce la pequeña base que lo demuestra.**

El motor ejecuta una consulta candidata y una referencia proporcionada, modifica datos relacionales y reduce el contraejemplo. Sin LLM, claves ni bases reales: utiliza verdaderas bases SQLite en memoria.

![Contraejemplo SQLite sintético con cuatro filas](docs/preview-fr.png)

## Probar

Python 3.11 o posterior, solo biblioteca estándar.

```sh
python3 -m sql_meaning serve --lang es
```

Abrir `http://127.0.0.1:8766/?lang=es`. El caso inicial pasa; buscar un contraejemplo. Una línea de pedido duplicada cambia el total de **2.000 a 4.000 céntimos**. El testigo reducido conserva cuatro filas y todas las restricciones declaradas. Probar después la referencia: no encontrar testigos nunca se presenta como prueba de corrección.

```sh
python3 -m sql_meaning search sql_meaning/examples/revenue.json > informe.json
python3 -m sql_meaning search mi-contrato.json
python3 -m sql_meaning compare sql-counterexample.json
```

Salida **1**: contraejemplo o diferencia; **0**: ningún testigo encontrado o resultados iguales; **2**: entrada o consulta inicial no válida. `pip install .` ofrece también `sql-meaning`. CLI e interfaz en FR/EN/ES.

## Contrato ejecutable

Un caso JSON incluye `tables`, `reference_sql`, `candidate_sql` y opcionalmente:

- `mutate_tables`: limitar las tablas modificables;
- `numeric_boundaries`: valores frontera que explorar;
- `required_children`: reglas que exigen al menos un hijo por fila padre, como `[parent_table, child_table, foreign_key]`;
- `ordered: true`: comparar el orden. Por defecto se usan multiconjuntos que conservan duplicados.

Admite columnas `INTEGER`, `REAL`, `TEXT`, claves primarias simples, claves externas simples y nulabilidad explícita. Cada fila proporciona todas las columnas. Las mutaciones clonan o eliminan filas, introducen `NULL` permitido y exploran fronteras numéricas y valores vecinos. Verifica claves, tipos e hijos obligatorios antes de aceptar un testigo.

La búsqueda en anchura tiene límites de profundidad, casos y tiempo. Tras una diferencia, reduce mediante eliminaciones con cierre de dependencias externas. Conserva la categoría del fallo: número de filas o valores. `row_deletion_minimal` solo es verdadero tras agotar estas reducciones; **no es un mínimo global** ni prueba de la causa de negocio. Si se agota el presupuesto conserva el testigo sin afirmar minimalidad.

El informe vincula el caso inicial con SHA-256, explica la mutación, muestra ambos resultados e incluye el caso reducido. La exportación del navegador se reproduce directamente con `compare`.

## Límites de la prueba

La referencia es una hipótesis proporcionada, no una verdad descubierta. Defectos compartidos o mutaciones insuficientes pueden ocultar errores. No deduce restricciones de negocio ausentes. `search_complete` solo indica que se exploró el espacio acotado configurado. Los flotantes no enteros se comparan exactamente; usar céntimos enteros para ejemplos financieros.

Se dirige a SQLite, no a equivalencia general entre dialectos PostgreSQL, DuckDB o MariaDB. Durante la evaluación se bloquean escrituras, `ATTACH`, pragmas y funciones de carga de extensiones/archivos; se limita trabajo SQL y resultados. No constituye aislamiento del sistema operativo frente a adversarios: añadir procesos o contenedores para consultas realmente hostiles.

## Herramientas existentes y diferencia

[SQLancer](https://github.com/sqlancer/sqlancer) busca defectos en motores de bases. [Test Suite SQL Evaluation](https://github.com/taoyds/test-suite-sql-eval) evalúa consultas mediante suites de ejecución. Este proyecto se inspira en esas ideas sin afirmar teoría nueva: busca **un contraejemplo relacional entre dos consultas de negocio proporcionadas**, conserva restricciones declaradas y exporta un caso localmente mínimo. [Query Contract CI](https://github.com/gbesse/query-contract-ci) comprueba contratos existentes; aquí los casos se modifican para desafiar su cobertura. No afirma resultados SOTA.

## Validación

```sh
python3 -m unittest discover -s tests -v
npm ci
npx playwright install chromium
npm run test:browser
npm run format:check
```

Dieciséis pruebas cubren el testigo de join, reducción, fronteras, `NULL`, multiplicidad, orden, restricciones, presupuestos y rechazo de escrituras/cargas. Navegador FR/EN/ES y móvil; CI Python 3.11/3.12 e instalación de rueda fuera de fuentes. Licencia MIT; alfa de investigación con datos sintéticos.

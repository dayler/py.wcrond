# MS-02: Modelos de Datos y Configuración

> **Estado General:** 🟢 Completado  
> **Última Actualización:** 2026-08-07  
> **Razón/Descripción:** Modelos, parser y config implementados. Tests pasados.

---

## 1. Objetivo y Alcance

Implementar los modelos de datos core y el sistema de configuración de `wcrond`:

- **`config.py`** — Clase `WcrondConfig`: carga y validación de `wcrond.toml`.
- **`job.py`** — Clases `CronJob` y `RetryConfig`: modelos de datos de jobs.
- **`parser.py`** — Parser de archivos `wcrontab.toml` y directorio `jobs.d/`.
- **`logging_config.py`** — Configuración del sistema de logging con `RotatingFileHandler`.

### Enfoque Técnico

1. **`WcrondConfig`**: Usar `dataclass` para modelar la configuración. Cargar TOML con `tomllib` (3.11+) o `tomli` (backport). Resolver rutas relativas al directorio `~/.wcrond/`. Validar tipos y rangos de valores.

2. **`CronJob` y `RetryConfig`**: Usar `dataclass`. `RetryConfig` tiene valores por defecto heredados de `WcrondConfig`. `CronJob` incluye todos los campos del PRD sección 3.5: `job_id`, `name`, `schedule`, `command`, `shell`, `enabled`, `timeout`, `overlap_policy`, `retry`, `env`, `working_dir`.

3. **`parser.py`**: Parsear `wcrontab.toml` principal. Iterar sobre `jobs.d/*.toml` y fusionar. Validar expresiones cron con `croniter.is_valid()`. Detectar `job_id` duplicados. Resolver shortcuts (`@daily`, etc.).

4. **`logging_config.py`**: Configurar `logging` con `RotatingFileHandler`. Crear directorio de logs si no existe. Soporte para `capture_job_output` (logs individuales por job).

---

## 2. Dependencias

| Milestone | Estado | Tipo |
|-----------|--------|------|
| MS-01 — Fundación del Proyecto | ⚪ | Obligatoria — Estructura de paquetes y pyproject.toml |

---

## 3. Plan de Unit Tests

### Estrategia

Testear cada componente de forma aislada con datos de prueba TOML en fixtures.

### Tests a Implementar

| Test | Archivo | Descripción | Cobertura |
|------|---------|-------------|-----------|
| `test_load_default_config` | `tests/test_config.py` | Cargar wcrond.toml con valores por defecto | Config loader |
| `test_load_custom_config` | `tests/test_config.py` | Cargar wcrond.toml con valores custom | Config loader |
| `test_config_validation_errors` | `tests/test_config.py` | Detectar errores de validación (valores inválidos) | Validación |
| `test_config_path_resolution` | `tests/test_config.py` | Rutas relativas se resuelven a ~/.wcrond/ | Path resolution |
| `test_parse_cronjob` | `tests/test_parser.py` | Parsear un job TOML completo a CronJob | Parser |
| `test_parse_minimal_job` | `tests/test_parser.py` | Job con solo campos obligatorios | Parser defaults |
| `test_parse_retry_config` | `tests/test_parser.py` | Parsear configuración de retry por job | RetryConfig |
| `test_parse_env_vars` | `tests/test_parser.py` | Parsear variables de entorno por job | Env vars |
| `test_parse_jobs_d_directory` | `tests/test_parser.py` | Cargar jobs desde jobs.d/*.toml | Multi-file |
| `test_duplicate_job_ids` | `tests/test_parser.py` | Detectar y rechazar job_ids duplicados | Validación |
| `test_invalid_cron_expression` | `tests/test_parser.py` | Rechazar expresiones cron inválidas | Validación |
| `test_cron_shortcuts` | `tests/test_parser.py` | Parsear @daily, @hourly, @reboot, etc. | Shortcuts |
| `test_overlap_policy_values` | `tests/test_parser.py` | Validar solo skip/allow/kill_previous | Validación |
| `test_logging_config_setup` | `tests/test_config.py` | Verificar que el logging se configura correctamente | Logging |
| `test_logging_rotation` | `tests/test_config.py` | Verificar configuración de rotación | Logging |

### Cobertura Esperada

- **Objetivo:** ≥ 90% en `config.py`, `job.py`, `parser.py`, `logging_config.py`
- **Comando:** `pytest tests/test_config.py tests/test_parser.py -v --cov=wcrond.config --cov=wcrond.job --cov=wcrond.parser --cov=wcrond.logging_config`

---

## 4. Plan de Pruebas Automatizadas

### Integración Config → Parser

Verificar que la configuración cargada se integra correctamente con el parser:

1. Crear archivos TOML temporales con configuración y jobs.
2. Cargar config, parsear jobs, verificar que los defaults de retry se heredan.
3. Verificar que los paths se resuelven correctamente.

### Criterios de Éxito

- Parser carga exitosamente los archivos de ejemplo del PRD.
- Configuraciones inválidas producen mensajes de error claros.
- Los defaults de `WcrondConfig` se propagan a `CronJob.retry`.

---

## 5. Control de Estado (Semáforos)

| # | Tarea | Estado | Razón/Descripción |
|---|-------|--------|-------------------|
| 1 | Implementar `WcrondConfig` (config.py) | 🟢 | Completado |
| 2 | Implementar `CronJob` y `RetryConfig` (job.py) | 🟢 | Completado |
| 3 | Implementar parser de wcrontab (parser.py) | 🟢 | Completado |
| 4 | Implementar logging_config.py | 🟢 | Completado |
| 5 | Ejecutar y pasar todos los unit tests | 🟢 | Completado, todos en verde |

---

## 6. Archivos a Crear/Modificar

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `src/wcrond/config.py` | IMPLEMENTAR | Clase WcrondConfig con carga TOML |
| `src/wcrond/job.py` | IMPLEMENTAR | Clases CronJob y RetryConfig |
| `src/wcrond/parser.py` | IMPLEMENTAR | Parser de wcrontab.toml y jobs.d/ |
| `src/wcrond/logging_config.py` | IMPLEMENTAR | Configuración de logging rotativo |
| `tests/test_config.py` | CREAR | Unit tests de configuración |
| `tests/test_parser.py` | CREAR | Unit tests del parser |
| `tests/conftest.py` | CREAR | Fixtures compartidas (temp dirs, TOML samples) |

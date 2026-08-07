# MS-03: State Store (SQLite)

> **Estado General:** 🟢 Completado  
> **Última Actualización:** 2026-08-07  
> **Razón/Descripción:** StateStore implementado y testeado con éxito.

---

## 1. Objetivo y Alcance

Implementar la capa de persistencia con SQLite para almacenamiento de estado e historial de ejecuciones:

- **`state.py`** — Clase `StateStore`: wrapper SQLite para el ciclo de vida de ejecuciones.
- **Modelo `TaskExecution`**: Dataclass para representar una ejecución individual.
- **Tablas**: `executions` y `retry_queue` según el PRD sección 4.5.1.
- **Funcionalidades**: CRUD de ejecuciones, consulta de historial, gestión de retry queue, limpieza automática.

### Enfoque Técnico

1. **Inicialización**: Crear la base de datos y tablas con `CREATE TABLE IF NOT EXISTS`. Usar `sqlite3` de la stdlib. Asegurar thread-safety con `check_same_thread=False` y un `threading.Lock` para operaciones de escritura.

2. **Tabla `executions`**: Según PRD sección 4.5.1. Columnas: `execution_id` (UUID PK), `job_id`, `job_name`, `start_time` (ISO8601), `end_time`, `duration_s`, `exit_code`, `status`, `attempt`, `pid`, `stdout_tail`, `stderr_tail`, `trigger`.

3. **Tabla `retry_queue`**: Columnas: `job_id` (PK), `attempt`, `next_retry_at` (ISO8601), `reason`.

4. **Clase `TaskExecution`**: Dataclass con todos los campos de la tabla `executions`.

5. **Métodos de `StateStore`**:
   - `record_start(job_id, job_name, pid, trigger, attempt)` → registrar inicio.
   - `record_end(execution_id, exit_code, status, stdout_tail, stderr_tail)` → registrar fin.
   - `get_history(job_id=None, limit=10)` → historial con filtros.
   - `get_running_jobs()` → ejecuciones con status RUNNING.
   - `add_retry(job_id, attempt, next_retry_at, reason)` → agregar a retry queue.
   - `remove_retry(job_id)` → remover de retry queue.
   - `get_retry_queue()` → listar retries pendientes.
   - `cleanup_old_records(days)` → purgar registros viejos.
   - `close()` → cerrar conexión.

6. **Thread Safety**: Usar `threading.Lock` para serializar escrituras. Las lecturas pueden ser concurrentes gracias a WAL mode.

---

## 2. Dependencias

| Milestone | Estado | Tipo |
|-----------|--------|------|
| MS-01 — Fundación del Proyecto | ⚪ | Obligatoria — Estructura de paquetes |

---

## 3. Plan de Unit Tests

### Estrategia

Usar una base de datos SQLite en memoria (`:memory:`) para tests rápidos y aislados.

### Tests a Implementar

| Test | Archivo | Descripción | Cobertura |
|------|---------|-------------|-----------|
| `test_create_tables` | `tests/test_state.py` | Verificar que las tablas se crean correctamente | Init DB |
| `test_record_start` | `tests/test_state.py` | Registrar inicio de ejecución y verificar campos | Write |
| `test_record_end` | `tests/test_state.py` | Registrar fin de ejecución con exit code y output | Write |
| `test_record_full_lifecycle` | `tests/test_state.py` | Start → End con cálculo automático de duration_s | Lifecycle |
| `test_get_history_all` | `tests/test_state.py` | Recuperar historial completo | Read |
| `test_get_history_by_job` | `tests/test_state.py` | Historial filtrado por job_id | Read + filtro |
| `test_get_history_limit` | `tests/test_state.py` | Historial con límite de registros | Read + limit |
| `test_get_running_jobs` | `tests/test_state.py` | Obtener solo ejecuciones con status RUNNING | Query |
| `test_add_retry` | `tests/test_state.py` | Agregar entry a retry queue | Retry queue |
| `test_remove_retry` | `tests/test_state.py` | Remover entry de retry queue | Retry queue |
| `test_get_retry_queue` | `tests/test_state.py` | Listar todos los retries pendientes | Retry queue |
| `test_cleanup_old_records` | `tests/test_state.py` | Purgar registros más viejos que N días | Cleanup |
| `test_thread_safety` | `tests/test_state.py` | Operaciones concurrentes desde múltiples threads | Concurrencia |
| `test_status_values` | `tests/test_state.py` | Verificar status válidos: SUCCESS, FAILED, TIMEOUT, KILLED, RUNNING | Validación |

### Cobertura Esperada

- **Objetivo:** ≥ 90% en `state.py`
- **Comando:** `pytest tests/test_state.py -v --cov=wcrond.state`

---

## 4. Plan de Pruebas Automatizadas

### Integración SQLite

1. **Test con archivo real**: Crear DB en directorio temporal, verificar persistencia tras close/reopen.
2. **Test de WAL mode**: Verificar que `PRAGMA journal_mode=WAL` está activo.
3. **Test de concurrencia**: 10 threads escribiendo simultáneamente, verificar integridad.

### Criterios de Éxito

- Todas las operaciones CRUD funcionan correctamente.
- No hay data corruption con acceso concurrente.
- La limpieza automática respeta el retention period.
- La DB se puede cerrar y reabrir sin pérdida de datos.

---

## 5. Control de Estado (Semáforos)

| # | Tarea | Estado | Razón/Descripción |
|---|-------|--------|-------------------|
| 1 | Implementar modelo `TaskExecution` | 🟢 | Implementado como dataclass |
| 2 | Implementar creación de tablas (schema SQL) | 🟢 | Tablas executions y retry_queue creadas |
| 3 | Implementar métodos CRUD de `StateStore` | 🟢 | Métodos CRUD completados |
| 4 | Implementar retry queue (add/remove/get) | 🟢 | Métodos implementados usando SQLite |
| 5 | Ejecutar y pasar todos los unit tests | 🟢 | Todos los tests pasaron exitosamente |

---

## 6. Archivos a Crear/Modificar

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `src/wcrond/state.py` | IMPLEMENTAR | Clase StateStore y TaskExecution |
| `tests/test_state.py` | CREAR | Unit tests del state store |

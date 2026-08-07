# MS-04: Motor Cron y Scheduler

> **Estado General:** 🟢 Completado  
> **Última Actualización:** 2026-08-07  
> **Razón/Descripción:** Requiere MS-02 y MS-03 completados

---

## 1. Objetivo y Alcance

Implementar el motor central del scheduler que evalúa las expresiones cron y despacha tareas:

- **`scheduler.py`** — Clase `Scheduler`: main loop, evaluación de jobs, despacho al thread pool.
- **Integración con `croniter`**: Evaluación de expresiones cron de 5 campos y shortcuts.
- **Lógica de tick**: Detección de cambio de minuto, evaluación de todos los jobs.
- **Overlap policies**: Implementar `skip`, `allow`, `kill_previous`.
- **Soporte `@reboot`**: Ejecutar jobs marcados con `@reboot` al iniciar.

### Enfoque Técnico

1. **Main Loop (`tick()`)**: Ejecutar cada `tick_interval` (1s por defecto). Detectar boundary de minuto. Al detectar nuevo minuto, llamar a `evaluate_jobs(now)`.

2. **`evaluate_jobs(now)`**: Iterar sobre todos los jobs habilitados. Usar `croniter` para verificar si el job coincide con el minuto actual. Aplicar overlap policy.

3. **Overlap Policies**:
   - `skip`: Verificar en `StateStore` si el job tiene status `RUNNING`. Si sí, loggear y saltar.
   - `allow`: Despachar siempre, sin verificar.
   - `kill_previous`: Buscar instancia corriendo, enviar kill, esperar terminación, luego despachar.

4. **Despacho**: Llamar al `Executor` (MS-05) para enviar al thread pool. En esta etapa, el Scheduler solo prepara la invocación; la ejecución real la maneja el Executor.

5. **`@reboot` jobs**: Mantener lista separada. Ejecutar una vez al inicio del daemon, antes de entrar al main loop.

6. **Métodos expuestos para IPC**:
   - `force_run(job_id)`: Enviar un job al executor inmediatamente.
   - `disable_job(job_id)`: Marcar job como disabled.
   - `enable_job(job_id)`: Marcar job como enabled.
   - `get_next_runs(job_id, n)`: Calcular las próximas N ejecuciones con croniter.

---

## 2. Dependencias

| Milestone | Estado | Tipo |
|-----------|--------|------|
| MS-02 — Modelos y Configuración | ⚪ | Obligatoria — CronJob, WcrondConfig, Parser |
| MS-03 — State Store (SQLite) | ⚪ | Obligatoria — StateStore para verificar running jobs |

---

## 3. Plan de Unit Tests

### Estrategia

Mockear `croniter`, `StateStore` y `Executor` para testear la lógica del scheduler de forma aislada.

### Tests a Implementar

| Test | Archivo | Descripción | Cobertura |
|------|---------|-------------|-----------|
| `test_tick_detects_minute_boundary` | `tests/test_scheduler.py` | Verificar que tick detecta cambio de minuto | Tick logic |
| `test_tick_no_action_same_minute` | `tests/test_scheduler.py` | No re-evalúa jobs en el mismo minuto | Tick dedup |
| `test_evaluate_matching_job` | `tests/test_scheduler.py` | Job con cron que coincide es despachado | Cron eval |
| `test_evaluate_non_matching_job` | `tests/test_scheduler.py` | Job con cron que no coincide es ignorado | Cron eval |
| `test_evaluate_disabled_job` | `tests/test_scheduler.py` | Jobs disabled se saltan | Disabled |
| `test_overlap_skip` | `tests/test_scheduler.py` | overlap_policy=skip no lanza si ya corriendo | Overlap |
| `test_overlap_allow` | `tests/test_scheduler.py` | overlap_policy=allow lanza aunque esté corriendo | Overlap |
| `test_overlap_kill_previous` | `tests/test_scheduler.py` | overlap_policy=kill_previous mata y relanza | Overlap |
| `test_reboot_jobs_at_startup` | `tests/test_scheduler.py` | Jobs @reboot se ejecutan al iniciar | @reboot |
| `test_force_run` | `tests/test_scheduler.py` | force_run() despacha un job inmediatamente | CLI action |
| `test_disable_enable_job` | `tests/test_scheduler.py` | disable/enable cambia estado del job | CLI action |
| `test_get_next_runs` | `tests/test_scheduler.py` | Calcular próximas N ejecuciones | Croniter |
| `test_multiple_jobs_same_minute` | `tests/test_scheduler.py` | Varios jobs coinciden en el mismo minuto | Multi-job |

### Cobertura Esperada

- **Objetivo:** ≥ 85% en `scheduler.py`
- **Comando:** `pytest tests/test_scheduler.py -v --cov=wcrond.scheduler`

---

## 4. Plan de Pruebas Automatizadas

### Integración Scheduler → StateStore

1. Crear scheduler con StateStore real (in-memory SQLite).
2. Registrar un job RUNNING en el StateStore.
3. Verificar que overlap_policy=skip funciona correctamente con estado real.
4. Verificar que force_run registra la ejecución.

### Criterios de Éxito

- El scheduler evalúa correctamente todas las expresiones cron del PRD.
- Los overlap policies funcionan según especificación.
- `@reboot` jobs se ejecutan solo una vez al inicio.
- `force_run` funciona independientemente del schedule y estado disabled.

---

## 5. Control de Estado (Semáforos)

| # | Tarea | Estado | Razón/Descripción |
|---|-------|--------|-------------------|
| 1 | Implementar tick loop con detección de minuto | 🟢 | Implementado en scheduler.py |
| 2 | Implementar evaluate_jobs con croniter | 🟢 | Implementado en scheduler.py |
| 3 | Implementar overlap policies (skip/allow/kill_previous) | 🟢 | Implementado en scheduler.py |
| 4 | Implementar soporte @reboot y force_run | 🟢 | Implementado en scheduler.py |
| 5 | Ejecutar y pasar todos los unit tests | 🟢 | 13 tests pasaron con éxito |

---

## 6. Archivos a Crear/Modificar

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `src/wcrond/scheduler.py` | IMPLEMENTAR | Clase Scheduler con main loop |
| `tests/test_scheduler.py` | CREAR | Unit tests del scheduler |

# MS-05: Executor y Concurrencia

> **Estado General:** 🟢 Completado  
> **Última Actualización:** 2026-08-07  
> **Razón/Descripción:** Tareas de executor, concurrencia, reintentos y watchdog completadas. Tests en verde.

---

## 1. Objetivo y Alcance

Implementar la ejecución de tareas con aislamiento de procesos, thread pool acotado, gestión de timeouts, y los subsistemas de retry y watchdog:

- **`executor.py`** — Ejecución de jobs como subprocesos en un ThreadPool.
- **`retry.py`** — `RetryManager`: backoff incremental y cancelación de reintentos.
- **`watchdog.py`** — `Watchdog`: detección y terminación de tareas zombie.

### Enfoque Técnico

#### executor.py

1. **`ThreadPoolExecutor(max_workers=N)`**: Pool acotado según `WcrondConfig.pool_size`.
2. **`execute_job(job: CronJob, trigger: str, attempt: int)`**:
   - Construir entorno: fusionar `os.environ` + `job.env`.
   - Determinar shell: `cmd`, `powershell`, `pwsh`, `bash` → construir command line.
   - Lanzar `subprocess.Popen` con `CREATE_NEW_PROCESS_GROUP`.
   - Registrar `record_start()` en StateStore.
   - Esperar con `process.communicate(timeout=job.timeout)`.
   - Capturar stdout/stderr (últimas `output_tail_lines` líneas).
   - Registrar `record_end()` en StateStore.
   - Si exit_code != 0 y retries disponibles → invocar RetryManager.
3. **Timeout handling**: `subprocess.TimeoutExpired` → `process.terminate()` → sleep(grace_period) → `process.kill()` si sigue vivo.
4. **Shell mapping**:
   - `cmd` → `["cmd.exe", "/c", command]`
   - `powershell` → `["powershell.exe", "-NoProfile", "-Command", command]`
   - `pwsh` → `["pwsh.exe", "-NoProfile", "-Command", command]`
   - `bash` → `["bash", "-c", command]`
   - Ruta absoluta → `[shell_path, command]`

#### retry.py

1. **`RetryManager`**: Mantiene un diccionario de retries pendientes con timers.
2. **`schedule_retry(job, attempt)`**: Calcula delay con fórmula `min(initial_delay * (multiplier ^ attempt), max_delay)`. Registra en StateStore retry_queue. Programa un `threading.Timer` para re-ejecutar.
3. **`cancel_retry(job_id)`**: Cancela el timer y elimina de StateStore retry_queue.
4. **`cancel_all()`**: Cancela todos los timers pendientes (para graceful shutdown).
5. **`get_pending_retries()`**: Devuelve lista de retries pendientes desde StateStore.

#### watchdog.py

1. **Thread dedicado** con loop cada `check_interval` segundos.
2. **`monitor_running_jobs()`**: Consultar StateStore por jobs con status RUNNING. Para cada uno, verificar si `duration > timeout`.
3. **`detect_zombies()`**: Retornar lista de jobs zombie.
4. **`kill_zombie(job_id)`**: `process.terminate()` → sleep(grace_period) → `process.kill()`. Actualizar StateStore con status TIMEOUT.
5. **Registro de PIDs activos**: El executor registra PIDs en un dict compartido para que el watchdog pueda enviar señales.

---

## 2. Dependencias

| Milestone | Estado | Tipo |
|-----------|--------|------|
| MS-02 — Modelos y Configuración | ⚪ | Obligatoria — CronJob, RetryConfig, WcrondConfig |
| MS-03 — State Store (SQLite) | ⚪ | Obligatoria — StateStore para registrar ejecuciones |

---

## 3. Plan de Unit Tests

### Estrategia

Usar subprocesos simples (`echo`, `exit 1`, `sleep`) para testear el executor. Mockear timers para el retry manager.

### Tests a Implementar

| Test | Archivo | Descripción | Cobertura |
|------|---------|-------------|-----------|
| `test_execute_success` | `tests/test_executor.py` | Ejecutar comando exitoso (exit 0) | Executor |
| `test_execute_failure` | `tests/test_executor.py` | Ejecutar comando que falla (exit 1) | Executor |
| `test_execute_timeout` | `tests/test_executor.py` | Comando excede timeout, se mata | Timeout |
| `test_execute_env_vars` | `tests/test_executor.py` | Variables de entorno se pasan al subproceso | Env |
| `test_execute_working_dir` | `tests/test_executor.py` | Working directory se aplica | Working dir |
| `test_shell_cmd` | `tests/test_executor.py` | Shell cmd.exe funciona | Shell mapping |
| `test_shell_powershell` | `tests/test_executor.py` | Shell powershell funciona | Shell mapping |
| `test_stdout_stderr_capture` | `tests/test_executor.py` | Captura de stdout y stderr con tail | Output capture |
| `test_thread_pool_bounded` | `tests/test_executor.py` | Pool no excede max_workers | Concurrencia |
| `test_create_new_process_group` | `tests/test_executor.py` | Subproceso usa CREATE_NEW_PROCESS_GROUP | Aislamiento |
| `test_retry_delay_calculation` | `tests/test_retry.py` | Fórmula de backoff incremental | Retry logic |
| `test_retry_max_delay` | `tests/test_retry.py` | Delay no excede max_delay_s | Retry cap |
| `test_retry_schedule_and_execute` | `tests/test_retry.py` | Retry se ejecuta tras el delay | Retry flow |
| `test_retry_cancel` | `tests/test_retry.py` | cancel_retry detiene el timer | Cancel |
| `test_retry_cancel_all` | `tests/test_retry.py` | cancel_all detiene todos los timers | Shutdown |
| `test_retry_max_retries` | `tests/test_retry.py` | No más retries que max_retries | Limit |
| `test_watchdog_detect_zombie` | `tests/test_watchdog.py` | Detectar job que excede timeout | Zombie detect |
| `test_watchdog_kill_zombie` | `tests/test_watchdog.py` | Terminar proceso zombie | Zombie kill |
| `test_watchdog_no_false_positives` | `tests/test_watchdog.py` | Jobs dentro de timeout no se marcan zombie | False positive |
| `test_watchdog_grace_period` | `tests/test_watchdog.py` | Esperar grace_period antes de kill | Grace period |

### Cobertura Esperada

- **Objetivo:** ≥ 85% en `executor.py`, `retry.py`, `watchdog.py`
- **Comando:** `pytest tests/test_executor.py tests/test_retry.py tests/test_watchdog.py -v --cov=wcrond.executor --cov=wcrond.retry --cov=wcrond.watchdog`

---

## 4. Plan de Pruebas Automatizadas

### Integración Executor → StateStore → RetryManager

1. Ejecutar un job que falla → verificar que se registra en StateStore → verificar que RetryManager programa reintento.
2. Ejecutar un job con timeout → verificar que el proceso se mata → verificar status TIMEOUT en DB.
3. Watchdog detecta zombie → mata proceso → verifica registro en DB.

### Test de Concurrencia

1. Lanzar `max_workers + 2` jobs simultáneos.
2. Verificar que solo `max_workers` corren en paralelo.
3. Los restantes esperan en la cola del ThreadPool.

### Criterios de Éxito

- Jobs exitosos registran SUCCESS.
- Jobs fallidos desencadenan retries.
- Timeouts matan procesos correctamente.
- El watchdog detecta y elimina zombies.
- No hay deadlocks con acceso concurrente a StateStore.

---

## 5. Control de Estado (Semáforos)

| # | Tarea | Estado | Razón/Descripción |
|---|-------|--------|-------------------|
| 1 | Implementar shell mapping y subprocess launch | 🟢 | Completado |
| 2 | Implementar execute_job con timeout y captura | 🟢 | Completado |
| 3 | Implementar RetryManager con backoff | 🟢 | Completado |
| 4 | Implementar Watchdog con detección de zombies | 🟢 | Completado |
| 5 | Implementar integración executor ↔ StateStore | 🟢 | Completado |
| 6 | Ejecutar y pasar todos los unit tests | 🟢 | 20/20 PASSED |

---

## 6. Archivos a Crear/Modificar

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `src/wcrond/executor.py` | IMPLEMENTAR | Ejecución de jobs con ThreadPool |
| `src/wcrond/retry.py` | IMPLEMENTAR | RetryManager con backoff incremental |
| `src/wcrond/watchdog.py` | IMPLEMENTAR | Watchdog para detección de zombies |
| `tests/test_executor.py` | CREAR | Unit tests del executor |
| `tests/test_retry.py` | CREAR | Unit tests del retry manager |
| `tests/test_watchdog.py` | CREAR | Unit tests del watchdog |

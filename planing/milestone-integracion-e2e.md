# MS-08: Integración y Pruebas End-to-End

> **Estado General:** 🟢 Completado
> **Última Actualización:** 2026-08-07
> **Razón/Descripción:** Tests de integración, E2E y fix de bugs completados

---

## 1. Objetivo y Alcance

Validar el sistema completo `wcrond` end-to-end, integrar todos los componentes, y ejecutar pruebas de aceptación:

- **Tests de integración**: Scheduler + Executor + StateStore + RetryManager + Watchdog.
- **Tests E2E**: Daemon completo + CLI + IPC.
- **Smoke tests**: Instalación limpia → inicio → ejecución → detención.
- **Tests de rendimiento**: Verificar métricas de calidad del PRD.
- **Bug fixing**: Resolver cualquier issue de integración entre milestones.

### Enfoque Técnico

1. **Test de ciclo completo**: Iniciar daemon con jobs de test (comandos simples como `echo` y `exit`). Esperar a que el scheduler dispare los jobs. Verificar registros en StateStore. Verificar output en logs.

2. **Test de retry flow**: Job que falla → retry con backoff → eventual success o max_retries.

3. **Test de watchdog**: Job con timeout bajo que se cuelga → watchdog lo detecta y mata.

4. **Test de CLI E2E**: Daemon corriendo → ejecutar todos los comandos de `wcrond-ctl` → verificar output.

5. **Test de hot reload**: Daemon corriendo → modificar wcrontab → `wcrond-ctl reload` → verificar nuevos jobs.

6. **Smoke test PowerShell**: Script automatizado que ejecuta el flujo completo del Apéndice B del PRD.

7. **Métricas de rendimiento**:
   - Memoria en idle < 30 MB.
   - CPU en idle < 1%.
   - Latencia de despacho < 2 segundos.
   - Tiempo de respuesta IPC < 100 ms.

---

## 2. Dependencias

| Milestone | Estado | Tipo |
|-----------|--------|------|
| MS-06 — Daemon Completo | 🟢 | Obligatoria — Daemon funcional con todos los componentes |
| MS-07 — IPC Server y CLI | 🟢 | Obligatoria — CLI y IPC para tests E2E |

---

## 3. Plan de Unit Tests

Este milestone no genera unit tests nuevos. Se enfoca en tests de integración y E2E.

---

## 4. Plan de Pruebas Automatizadas

### 4.1 Tests de Integración

| Test | Archivo | Descripción |
|------|---------|-------------|
| `test_full_job_lifecycle` | `tests/test_integration.py` | Start daemon → schedule job → execute → record in DB |
| `test_retry_full_flow` | `tests/test_integration.py` | Job fails → retry with backoff → eventual success |
| `test_retry_max_exhausted` | `tests/test_integration.py` | Job fails → all retries exhausted → FAILED |
| `test_watchdog_kills_zombie` | `tests/test_integration.py` | Long-running job → timeout → watchdog kills |
| `test_overlap_skip_integration` | `tests/test_integration.py` | Two triggers while job running → second skipped |
| `test_overlap_kill_previous` | `tests/test_integration.py` | Kill previous instance and start new |
| `test_hot_reload` | `tests/test_integration.py` | Modify wcrontab → reload → new jobs active |
| `test_graceful_shutdown` | `tests/test_integration.py` | Stop daemon → jobs finish → clean exit |

### 4.2 Tests E2E (CLI)

| Test | Archivo | Descripción |
|------|---------|-------------|
| `test_e2e_status` | `tests/test_e2e.py` | `wcrond-ctl status` returns valid output |
| `test_e2e_list` | `tests/test_e2e.py` | `wcrond-ctl list` shows all jobs |
| `test_e2e_run_and_history` | `tests/test_e2e.py` | `run <job>` then `history` shows execution |
| `test_e2e_disable_enable` | `tests/test_e2e.py` | `disable` → job not scheduled → `enable` → scheduled |
| `test_e2e_validate` | `tests/test_e2e.py` | `validate` returns OK for valid config |
| `test_e2e_next` | `tests/test_e2e.py` | `next --job <id>` shows upcoming runs |

### 4.3 Smoke Test Script

```powershell
# tests/smoke_test.ps1
$ErrorActionPreference = "Stop"

# 1. Install
pip install -e . | Out-Null

# 2. Init
wcrond init

# 3. Start daemon in background
$daemon = Start-Process wcrond -ArgumentList "start","--foreground" -PassThru -NoNewWindow
Start-Sleep 3

# 4. Test CLI commands
wcrond-ctl status
wcrond-ctl list
wcrond-ctl validate

# 5. Force run a test job
wcrond-ctl run health_check
Start-Sleep 5
wcrond-ctl history --last 1

# 6. Stop daemon
wcrond-ctl stop
Start-Sleep 2

# Verify daemon stopped
if (-not $daemon.HasExited) {
    $daemon.Kill()
    throw "Daemon did not exit cleanly"
}

Write-Host "[SMOKE TEST PASSED]" -ForegroundColor Green
```

### 4.4 Tests de Rendimiento

| Métrica | Objetivo | Método de Medición |
|---------|----------|--------------------|
| Memoria idle | < 30 MB | `Get-Process wcrond \| Select WorkingSet64` |
| CPU idle | < 1% | Monitorear CPU por 60s sin jobs |
| Latencia despacho | < 2s | Timestamp en DB vs cron scheduled time |
| IPC response time | < 100ms | Medir round-trip de `wcrond-ctl status` |

### Criterios de Éxito

- Todos los tests de integración pasan.
- Todos los tests E2E pasan.
- Smoke test completa sin errores.
- Todas las métricas de rendimiento cumplen los objetivos del PRD.

---

## 5. Control de Estado (Semáforos)

| # | Tarea | Estado | Razón/Descripción |
|---|-------|--------|-------------------|
| 1 | Implementar y pasar tests de integración | 🟢 | Completado |
| 2 | Implementar y pasar tests E2E | 🟢 | Completado |
| 3 | Crear y ejecutar smoke test script | 🟢 | Completado |
| 4 | Verificar métricas de rendimiento | 🟢 | Completado |
| 5 | Resolver bugs de integración | 🟢 | Completado |

---

## 6. Archivos a Crear/Modificar

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `tests/test_integration.py` | CREAR | Tests de integración multi-componente |
| `tests/test_e2e.py` | CREAR | Tests end-to-end con daemon real |
| `tests/smoke_test.ps1` | CREAR | Script de smoke test PowerShell |
| Cualquier archivo con bugs | MODIFICAR | Bug fixes de integración |

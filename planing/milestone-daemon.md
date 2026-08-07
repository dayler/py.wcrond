# MS-06: Daemon Completo

> **Estado General:** 🟢 Completado  
> **Última Actualización:** 2026-08-07  
> **Razón/Descripción:** Implementado el orquestador del daemon y CLI, tests pasando al 100%

---

## 1. Objetivo y Alcance

Integrar todos los componentes del daemon en la clase orquestadora `WcrondDaemon` y el entry point `__main__.py`:

- **`daemon.py`** — Clase `WcrondDaemon`: orquesta el ciclo de vida completo.
- **`__main__.py`** — Entry point con subcomandos: `start`, `stop`, `init`.
- **PID file management**: Prevención de instancias duplicadas.
- **Graceful shutdown**: Captura de SIGINT/SIGTERM, finalización ordenada.
- **Hot reload**: Recargar configuración y jobs sin reiniciar.
- **Startup sequence**: Inicializar todos los componentes en orden.

### Enfoque Técnico

1. **`WcrondDaemon`**:
   - Constructor: recibe path a config, inicializa todos los componentes.
   - `start()`: Secuencia de arranque:
     1. Cargar `WcrondConfig`.
     2. Verificar/crear PID file.
     3. Parsear wcrontab files.
     4. Inicializar StateStore.
     5. Inicializar ThreadPool/Executor.
     6. Inicializar RetryManager.
     7. Inicializar Watchdog.
     8. Inicializar IPC Server (si disponible, sino stub).
     9. Ejecutar `@reboot` jobs.
     10. Entrar al main loop del Scheduler.
   - `stop()`: Graceful shutdown:
     1. Señalizar al scheduler que detenga el loop.
     2. Cancelar todos los retries pendientes.
     3. Esperar a que jobs en ejecución terminen (con timeout).
     4. Detener watchdog.
     5. Cerrar IPC server.
     6. Cerrar StateStore.
     7. Eliminar PID file.
   - `reload()`: Recargar wcrontab sin reiniciar.

2. **PID File**:
   - Escribir PID al iniciar.
   - Al arrancar, verificar si el PID existente está vivo (`os.kill(pid, 0)`).
   - Manejar stale PID files (proceso muerto con PID file huérfano).

3. **Signal Handling**:
   - `signal.signal(signal.SIGINT, handler)` y `signal.SIGTERM`.
   - En Windows, también `signal.SIGBREAK` (Ctrl+Break).
   - Handler llama a `daemon.stop()`.

4. **`__main__.py`**:
   - `wcrond start [--foreground] [--config PATH]`: Iniciar daemon.
   - `wcrond stop`: Enviar señal de parada via IPC.
   - `wcrond init`: Crear estructura `~/.wcrond/` con configs por defecto.
   - Foreground mode: ejecutar en la terminal actual (para debug).
   - Background mode: `subprocess.Popen` lanzando una nueva instancia detached.

---

## 2. Dependencias

| Milestone | Estado | Tipo |
|-----------|--------|------|
| MS-04 — Motor Cron y Scheduler | ⚪ | Obligatoria — Scheduler para el main loop |
| MS-05 — Executor y Concurrencia | ⚪ | Obligatoria — Executor, RetryManager, Watchdog |

---

## 3. Plan de Unit Tests

### Estrategia

Mockear componentes internos para testear el flujo de orquestación del daemon.

### Tests a Implementar

| Test | Archivo | Descripción | Cobertura |
|------|---------|-------------|-----------|
| `test_daemon_start_sequence` | `tests/test_daemon.py` | Verificar que todos los componentes se inicializan en orden | Start |
| `test_daemon_stop_graceful` | `tests/test_daemon.py` | Verificar secuencia de shutdown | Stop |
| `test_pid_file_creation` | `tests/test_daemon.py` | PID file se crea con el PID correcto | PID mgmt |
| `test_pid_file_duplicate_detection` | `tests/test_daemon.py` | Detectar instancia duplicada via PID file | PID guard |
| `test_pid_file_stale_cleanup` | `tests/test_daemon.py` | Limpiar PID file huérfano | PID stale |
| `test_signal_handler_sigint` | `tests/test_daemon.py` | SIGINT dispara graceful shutdown | Signal |
| `test_reload_config` | `tests/test_daemon.py` | Reload recarga jobs sin reiniciar | Hot reload |
| `test_init_command` | `tests/test_daemon.py` | `wcrond init` crea la estructura de directorios | Init |
| `test_main_entry_point` | `tests/test_daemon.py` | __main__.py parsea correctamente los subcomandos | Entry point |

### Cobertura Esperada

- **Objetivo:** ≥ 80% en `daemon.py` y `__main__.py`
- **Comando:** `pytest tests/test_daemon.py -v --cov=wcrond.daemon --cov=wcrond.__main__`

---

## 4. Plan de Pruebas Automatizadas

### Integración Full Stack

1. Iniciar daemon en foreground mode con configuración de prueba.
2. Verificar que los componentes se inicializan correctamente.
3. Enviar SIGINT y verificar graceful shutdown.
4. Verificar que el PID file se elimina tras shutdown.

### Test de Init

1. Ejecutar `wcrond init` en directorio temporal.
2. Verificar que se crea la estructura `~/.wcrond/` completa.
3. Verificar que los archivos de config por defecto son válidos.

### Criterios de Éxito

- El daemon arranca y se detiene correctamente.
- No hay procesos huérfanos tras shutdown.
- PID file previene instancias duplicadas.
- Hot reload funciona sin interrumpir jobs en ejecución.

---

## 5. Control de Estado (Semáforos)

| # | Tarea | Estado | Razón/Descripción |
|---|-------|--------|-------------------|
| 1 | Implementar WcrondDaemon.start() con secuencia completa | 🟢 | Implementado |
| 2 | Implementar WcrondDaemon.stop() con graceful shutdown | 🟢 | Implementado |
| 3 | Implementar PID file management | 🟢 | Implementado |
| 4 | Implementar __main__.py con subcomandos | 🟢 | Implementado |
| 5 | Ejecutar y pasar todos los unit tests | 🟢 | Cobertura validada |

---

## 6. Archivos a Crear/Modificar

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `src/wcrond/daemon.py` | IMPLEMENTAR | Clase WcrondDaemon orquestadora |
| `src/wcrond/__main__.py` | MODIFICAR | Entry point con start/stop/init |
| `tests/test_daemon.py` | CREAR | Unit tests del daemon |

# MS-07: IPC Server y CLI (wcrond-ctl)

> **Estado General:** 🟢 Completado  
> **Última Actualización:** 2026-08-07  
> **Razón/Descripción:** Todas las tareas del MS-07 han sido implementadas y testeadas.

---

## 1. Objetivo y Alcance

Implementar la comunicación IPC entre el daemon y la herramienta CLI `wcrond-ctl`:

- **`ipc.py`** — Clase `IPCServer`: servidor Named Pipe en el daemon.
- **`wcrond_ctl/client.py`** — Clase `IPCClient`: cliente Named Pipe para el CLI.
- **`wcrond_ctl/cli.py`** — CLI con `argparse`: todos los comandos del PRD sección 4.6.
- **`wcrond_ctl/formatters.py`** — Formateo de tablas y output colorizado.

### Enfoque Técnico

#### ipc.py (Servidor)

1. **Named Pipe server** usando `win32pipe` y `win32file` de `pywin32`.
2. **Thread dedicado**: El IPC server corre en su propio thread.
3. **Protocolo**: JSON sobre pipe. Request: `{"cmd": "...", ...params}`. Response: `{"status": "ok/error", "data": ...}`.
4. **Handlers registrados**: Mapa `cmd → handler_function`.
5. **Handlers implementados**:
   - `status` → Uptime, jobs cargados, threads activos, cola de retries.
   - `list` → Lista de todos los jobs con schedule, enabled, última ejecución.
   - `history` → Historial de ejecuciones con filtros (job, limit, since).
   - `retries` → Lista de retries pendientes.
   - `run` → Force run de un job.
   - `kill` → Matar instancia de un job.
   - `cancel-retry` → Cancelar retries de un job.
   - `disable` → Deshabilitar un job.
   - `enable` → Habilitar un job.
   - `zombies` → Listar tareas zombie.
   - `reload` → Recargar configuración.
   - `logs` → Últimas líneas de log (filtrable por job).
   - `validate` → Validar configuración.
   - `next` → Próximas ejecuciones programadas.
   - `stop` → Señalizar shutdown del daemon.

#### wcrond_ctl/client.py (Cliente)

1. **`IPCClient`**: Conectar al Named Pipe, enviar JSON, recibir respuesta.
2. **Timeout de conexión**: Configurable (default 5s). Error claro si el daemon no responde.
3. **Manejo de errores**: "Daemon no está corriendo" si pipe no existe.

#### wcrond_ctl/cli.py

1. **`argparse`** con subcomandos para todos los comandos del PRD.
2. **Flags**: `--job`, `--last`, `--since`, `--tail`, `--help`.
3. **Parseo de argumentos** → construir request JSON → enviar via IPCClient → formatear respuesta.

#### wcrond_ctl/formatters.py

1. **Tablas**: Formateo tipo box-drawing para `list`, `history`, `retries`.
2. **Colores**: SUCCESS=verde, FAILED=rojo, RUNNING=azul, TIMEOUT=amarillo (usando ANSI escapes).
3. **Duración**: Formatear segundos como "5m 31s", "1h 23m", etc.

---

## 2. Dependencias

| Milestone | Estado | Tipo |
|-----------|--------|------|
| MS-01 — Fundación del Proyecto | ⚪ | Obligatoria — Estructura del paquete wcrond_ctl |
| MS-03 — State Store (SQLite) | ⚪ | Obligatoria — StateStore para queries de historial/status |

**Nota:** Este milestone NO depende de MS-02 (modelos) ni MS-04/MS-05 (scheduler/executor). Los handlers del IPC server que requieran el Scheduler se implementan como interfaces/stubs que se conectarán en MS-06 (Daemon). El IPC server y CLI pueden desarrollarse y testearse de forma independiente con un StateStore mock.

---

## 3. Plan de Unit Tests

### Estrategia

Testear el IPC server/client con pipes locales. Testear el CLI con mocks del cliente.

### Tests a Implementar

| Test | Archivo | Descripción | Cobertura |
|------|---------|-------------|-----------|
| `test_ipc_server_start_stop` | `tests/test_ipc.py` | Servidor inicia y se detiene correctamente | IPC lifecycle |
| `test_ipc_send_receive` | `tests/test_ipc.py` | Enviar request, recibir response JSON | IPC comms |
| `test_ipc_invalid_command` | `tests/test_ipc.py` | Comando desconocido retorna error | Error handling |
| `test_ipc_timeout` | `tests/test_ipc.py` | Client timeout cuando daemon no responde | Timeout |
| `test_ipc_daemon_not_running` | `tests/test_ipc.py` | Error claro cuando pipe no existe | Connection |
| `test_ipc_handler_status` | `tests/test_ipc.py` | Handler de status retorna estructura correcta | Handler |
| `test_ipc_handler_list` | `tests/test_ipc.py` | Handler de list retorna jobs | Handler |
| `test_ipc_handler_history` | `tests/test_ipc.py` | Handler de history con filtros | Handler |
| `test_cli_status_command` | `tests/test_cli.py` | `wcrond-ctl status` parsea y ejecuta | CLI parsing |
| `test_cli_list_command` | `tests/test_cli.py` | `wcrond-ctl list` parsea y ejecuta | CLI parsing |
| `test_cli_history_flags` | `tests/test_cli.py` | `--job`, `--last`, `--since` se parsean | CLI flags |
| `test_cli_run_command` | `tests/test_cli.py` | `wcrond-ctl run <job_id>` | CLI action |
| `test_cli_help` | `tests/test_cli.py` | `--help` muestra ayuda correcta | CLI help |
| `test_formatter_table` | `tests/test_cli.py` | Formateo de tabla con box-drawing | Formatter |
| `test_formatter_duration` | `tests/test_cli.py` | Formateo de duración (5m 31s, etc.) | Formatter |
| `test_formatter_colors` | `tests/test_cli.py` | Colores ANSI para status | Formatter |

### Cobertura Esperada

- **Objetivo:** ≥ 85% en `ipc.py`, `cli.py`, `client.py`, `formatters.py`
- **Comando:** `pytest tests/test_ipc.py tests/test_cli.py -v --cov=wcrond.ipc --cov=wcrond_ctl`

---

## 4. Plan de Pruebas Automatizadas

### Integración IPC Server ↔ Client

1. Iniciar IPC server en thread.
2. Conectar con IPCClient.
3. Enviar `status`, `list`, `history` y verificar respuestas.
4. Enviar `run <job_id>` y verificar que el handler se invoca.
5. Detener servidor y verificar que client recibe error.

### Test CLI E2E

1. Iniciar daemon mock con IPC server.
2. Ejecutar `wcrond-ctl status` como subproceso.
3. Verificar output en stdout.

### Criterios de Éxito

- Comunicación bidireccional funcional via Named Pipe.
- Todos los 14 comandos del CLI parsean y envían correctamente.
- Output formateado es legible y consistente con el PRD.
- Errores claros cuando el daemon no está disponible.

---

## 5. Control de Estado (Semáforos)

| # | Tarea | Estado | Razón/Descripción |
|---|-------|--------|-------------------|
| 1 | Implementar IPCServer con Named Pipe (ipc.py) | 🟢 | Implementado |
| 2 | Implementar IPCClient (client.py) | 🟢 | Implementado |
| 3 | Implementar CLI con argparse (cli.py) | 🟢 | Implementado |
| 4 | Implementar formatters (formatters.py) | 🟢 | Implementado |
| 5 | Implementar todos los IPC handlers | 🟢 | Stub handlers listos |
| 6 | Ejecutar y pasar todos los unit tests | 🟢 | Pasados con exito |

---

## 6. Archivos a Crear/Modificar

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `src/wcrond/ipc.py` | IMPLEMENTAR | Servidor IPC con Named Pipe |
| `src/wcrond_ctl/client.py` | IMPLEMENTAR | Cliente IPC para Named Pipe |
| `src/wcrond_ctl/cli.py` | IMPLEMENTAR | CLI con argparse y subcomandos |
| `src/wcrond_ctl/formatters.py` | IMPLEMENTAR | Formateo de tablas y colores |
| `src/wcrond_ctl/__main__.py` | MODIFICAR | Entry point invoca cli.main() |
| `tests/test_ipc.py` | CREAR | Unit tests del IPC |
| `tests/test_cli.py` | CREAR | Unit tests del CLI |

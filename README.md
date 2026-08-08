# wcrond (Windows Cron Daemon)

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

**wcrond** es un servicio ligero de planificación de tareas para escritorio Windows que emula el comportamiento de `crond` de Linux. Se ejecuta como un proceso residente sin depender del Windows Task Scheduler, ofreciendo programación basada en expresiones cron estándar, aislamiento de tareas, reintentos con backoff incremental, monitoreo detallado y herramientas de control en línea de comandos.

## 🚀 Características Principales

- **Sintaxis Cron Estándar**: Soporte completo de 5 campos y shortcuts (`@daily`, `@hourly`, etc.).
- **Aislamiento Seguro**: Thread pool acotado para ejecutar subprocesos sin bloquear el scheduler.
- **Resiliencia**: Reintentos automáticos con backoff incremental configurable por tarea.
- **Monitoreo y Control**: Herramienta CLI (`wcrond-ctl`) para listar estado, historial y controlar jobs en tiempo real.
- **Ligero**: Consumo mínimo de recursos (< 30 MB RAM en idle, < 1% CPU).
- **Protección Zombie**: Detección y terminación automática de tareas colgadas.

## ⚡ Quickstart

### Instalación

Clona el repositorio e instala usando pip:

```powershell
git clone https://github.com/tu-org/wcrond.git
cd wcrond
pip install .
```

Durante la instalación, `wcrond` inicializará automáticamente su configuración por defecto en `%USERPROFILE%\.wcrond`. Si por alguna razón los archivos no se generan (por ejemplo, instalando desde un _wheel_ distribuido), puedes forzar la inicialización en cualquier momento ejecutando:

```powershell
wcrond init
```

### Configura tu primer Job

Edita el archivo `%USERPROFILE%\.wcrond\wcrontab.toml` generado automáticamente:

```toml
[jobs.hello_world]
schedule = "* * * * *"
command = "echo Hello World"
shell = "cmd"
enabled = true
```

### Inicia el Daemon

Ejecuta el daemon en background o en una terminal separada:

```powershell
wcrond start
```

### Verifica el Estado

Usa la herramienta de línea de comandos para ver el estado:

```powershell
wcrond-ctl status
wcrond-ctl list
wcrond-ctl logs --job hello_world
```

## 🛠️ Referencia Rápida de Comandos

### Daemon (`wcrond`)
El binario principal controla el ciclo de vida del servicio en segundo plano.

| Comando | Flags | Descripción y Ejemplo |
|---------|-------|------------------------|
| `init`  | `--config <ruta>` | Crea la estructura inicial en `~/.wcrond`.<br>Ej: `wcrond init` |
| `start` | `--foreground`, `--config <ruta>` | Inicia el demonio. Usa `--foreground` para bloquear la terminal.<br>Ej: `wcrond start --foreground` |
| `status`| `--config <ruta>` | Comprueba rápidamente si el demonio está activo. Retorna código 0 si corre.<br>Ej: `wcrond status` |
| `stop`  | `--config <ruta>` | Envía una señal IPC para apagar el demonio en ejecución.<br>Ej: `wcrond stop` |

### Control CLI (`wcrond-ctl`)
Permite interactuar con el demonio en tiempo real.

| Comando | Flags/Argumentos | Descripción y Ejemplo |
|---------|------------------|------------------------|
| `status` | N/A | Muestra tiempo de actividad y estado de hilos/jobs.<br>Ej: `wcrond-ctl status` |
| `list` | N/A | Enumera todos los jobs configurados y su estado.<br>Ej: `wcrond-ctl list` |
| `history` | `--job <id>`, `--last <N>`, `--since <ISO>` | Muestra historial de ejecuciones.<br>Ej: `wcrond-ctl history --last 10` |
| `retries` | N/A | Muestra trabajos encolados para reintento tras fallar.<br>Ej: `wcrond-ctl retries` |
| `next` | `--job <id>` | Lista cuándo será la próxima ejecución esperada.<br>Ej: `wcrond-ctl next` |
| `run` | `<job_id>` | Dispara la ejecución inmediata de un trabajo.<br>Ej: `wcrond-ctl run hello_world` |
| `kill` | `<job_id>` | Fuerza la terminación (SIGKILL) de un trabajo activo.<br>Ej: `wcrond-ctl kill hello_world` |
| `disable` | `<job_id>` | Pausa futuras ejecuciones programadas del trabajo.<br>Ej: `wcrond-ctl disable hello_world` |
| `enable` | `<job_id>` | Reanuda las ejecuciones de un trabajo pausado.<br>Ej: `wcrond-ctl enable hello_world` |
| `cancel-retry`| `<job_id>` | Elimina un job específico de la cola de reintentos.<br>Ej: `wcrond-ctl cancel-retry hello_world` |
| `logs` | `--job <id>`, `--tail <N>` | Muestra la salida (stdout/stderr) capturada.<br>Ej: `wcrond-ctl logs --job hello_world --tail 20` |
| `zombies`| N/A | Detecta procesos huérfanos que excedieron su timeout.<br>Ej: `wcrond-ctl zombies` |
| `reload` | N/A | Recarga la configuración y jobs sin apagar el demonio.<br>Ej: `wcrond-ctl reload` |
| `validate`| N/A | Valida la sintaxis del cron en tus archivos `.toml`.<br>Ej: `wcrond-ctl validate` |
| `stop` | N/A | Apaga el demonio de wcrond.<br>Ej: `wcrond-ctl stop` |

Para más detalles exhaustivos, consulta el [Manual de Usuario](docs/user-guide.md).

## 📚 Documentación

Para información detallada, consulta los siguientes documentos:

- [Manual de Usuario](docs/user-guide.md): Instalación, configuración, formato de jobs y sintaxis cron.
- [Arquitectura As-Built](docs/architecture.md): Diagramas de componentes, flujo del scheduler y diseño interno.
- [Referencia del CLI](docs/cli-reference.md): Guía completa de comandos de `wcrond-ctl`.
- [Guía de Desarrollo](docs/development.md): Setup de desarrollo, testing y contribución.

## 📝 Licencia

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo LICENSE para más detalles.

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

## 🛠️ Comandos CLI

El comando `wcrond-ctl` permite interactuar con el daemon:

| Comando | Descripción |
|---------|-------------|
| `status` | Muestra el estado general del daemon |
| `list` | Lista todos los jobs programados |
| `history` | Muestra el historial de ejecuciones |
| `run <job>` | Fuerza la ejecución inmediata de un job |
| `kill <job>` | Fuerza la terminación de un job en ejecución |
| `logs` | Muestra los logs del sistema o de un job |

Para más detalles, consulta la [Referencia del CLI](docs/cli-reference.md).

## 📚 Documentación

Para información detallada, consulta los siguientes documentos:

- [Manual de Usuario](docs/user-guide.md): Instalación, configuración, formato de jobs y sintaxis cron.
- [Arquitectura As-Built](docs/architecture.md): Diagramas de componentes, flujo del scheduler y diseño interno.
- [Referencia del CLI](docs/cli-reference.md): Guía completa de comandos de `wcrond-ctl`.
- [Guía de Desarrollo](docs/development.md): Setup de desarrollo, testing y contribución.

## 📝 Licencia

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo LICENSE para más detalles.

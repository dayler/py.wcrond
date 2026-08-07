# Referencia del CLI (wcrond-ctl)

La herramienta `wcrond-ctl` permite a los usuarios interactuar con el daemon de `wcrond` utilizando Named Pipes (IPC) en Windows.

## Comandos Generales

### `wcrond-ctl --help`
Muestra una lista de todos los comandos disponibles y opciones globales.

### `wcrond-ctl status`
Muestra el estado general del daemon.
- **Salida:** Uptime, cantidad de jobs cargados, tamaño del thread pool, threads activos, y tamaño de la cola de reintentos.

### `wcrond-ctl list`
Lista todos los jobs configurados.
- **Salida:** Tabla con columnas: `ID`, `Schedule`, `Enabled/Disabled`, y `Next Run`.

### `wcrond-ctl history`
Muestra el historial de ejecuciones.
- **Opciones:**
  - `--job <job_id>`: Filtra por un job específico.
  - `--last <N>`: Muestra los últimos N registros.
  - `--since <ISO_DATE>`: Muestra ejecuciones desde una fecha.
- **Salida:** Tabla con `Job`, `Started`, `Ended`, `Duration`, `Status`, `Attempt`, `Trigger`.

### `wcrond-ctl next`
Muestra las próximas ejecuciones programadas.
- **Opciones:**
  - `--job <job_id>`: Filtra por un job específico.
  - `-n, --count <N>`: Cantidad de próximas ejecuciones a mostrar.

### `wcrond-ctl logs`
Visualiza los logs del sistema wcrond o de un job en particular.
- **Opciones:**
  - `--job <job_id>`: Muestra los logs de salida (stdout/stderr) de un job.
  - `--tail <N>`: Muestra las últimas N líneas.

## Control de Jobs

### `wcrond-ctl run <job_id>`
Fuerza la ejecución inmediata de un job específico.
- *Nota:* Ignora el schedule actual y el estado de habilitación (incluso si está disabled, se forzará la ejecución si es posible, según las políticas de overlap).

### `wcrond-ctl kill <job_id>`
Envía una señal para terminar la ejecución actual de un job que está corriendo.

### `wcrond-ctl disable <job_id>`
Deshabilita un job. El job no se ejecutará según su schedule hasta que sea rehabilitado. También cancela los reintentos pendientes.

### `wcrond-ctl enable <job_id>`
Habilita un job previamente deshabilitado.

## Resiliencia y Mantenimiento

### `wcrond-ctl retries`
Muestra una lista de todos los reintentos pendientes debido a fallos.
- **Salida:** Tabla con `Job`, `Attempt`, `Next Retry At`, y `Reason`.

### `wcrond-ctl cancel-retry <job_id>`
Cancela todos los reintentos que están encolados para un job.

### `wcrond-ctl zombies`
Lista las tareas "zombie" (tareas cuyo tiempo de ejecución ha superado el timeout configurado, pero el proceso subyacente sigue activo).

### `wcrond-ctl reload`
Recarga los archivos de configuración (`wcrond.toml`, `wcrontab.toml` y `jobs.d/`) en el daemon sin necesidad de reiniciarlo.

### `wcrond-ctl validate`
Analiza y valida localmente la sintaxis de los archivos TOML de configuración y jobs, informando de posibles errores sin afectar al daemon en ejecución.

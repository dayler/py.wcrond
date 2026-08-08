# Manual de Usuario

Bienvenido al manual de usuario de **wcrond** (Windows Cron Daemon).

## 1. Instalación

1.  **Requisitos**: Python 3.10 o superior y Windows (10/11/Server).
2.  **Vía PIP**:
    ```powershell
    git clone https://github.com/tu-org/wcrond.git
    cd wcrond
    pip install .
    ```

Esto instalará los comandos `wcrond` (para el daemon) y `wcrond-ctl` (el CLI de control) en tu entorno. Al ejecutar `pip install .` desde el código fuente, el proceso de instalación inicializará automáticamente la configuración por defecto. Si necesitas inicializar la configuración manualmente, puedes usar el comando:

```powershell
wcrond init
```

## 2. Configuración del Sistema (`wcrond.toml`)

La configuración principal del daemon se almacena en `%USERPROFILE%\.wcrond\wcrond.toml`. Si no existe al iniciar, puedes generarlo desde las plantillas incluidas en el código fuente usando `wcrond init`.

**Ejemplo de `wcrond.toml`:**

```toml
[daemon]
tick_interval = 1.0
default_shell = "powershell"
default_working_dir = "%USERPROFILE%"

[pool]
max_workers = 4
default_timeout = 3600
grace_period = 16

[retry]
max_retries = 3
initial_delay_s = 30
backoff_multiplier = 2.0
max_delay_s = 300

[logging]
log_dir = "logs"
level = "INFO"

[database]
path = "data/wcrond.db"
history_retention_days = 30

[watchdog]
check_interval = 30
auto_kill_zombies = true
```

### Propiedades de `wcrond.toml`

**Sección `[daemon]`:**
- `tick_interval`: (float) Intervalo en segundos en que el scheduler verifica tareas pendientes.
- `default_shell`: (string) Shell por defecto para comandos (`powershell`, `cmd`, `bash`).
- `default_working_dir`: (string) Directorio de trabajo base si el job no especifica uno.
- `pid_file`: (string) Ruta del archivo PID relativo a `~/.wcrond/`.

**Sección `[pool]`:**
- `max_workers`: (int) Número máximo de hilos (threads) concurrentes para ejecutar trabajos.
- `default_timeout`: (int) Tiempo máximo de ejecución en segundos para trabajos si no lo sobreescriben.
- `grace_period`: (int) Segundos de gracia tras enviar una señal de terminación antes de forzar un kill.

**Sección `[retry]` (Global defaults):**
- `max_retries`: (int) Cantidad máxima de intentos ante un fallo.
- `initial_delay_s`: (int) Segundos a esperar antes del primer reintento.
- `backoff_multiplier`: (float) Factor multiplicador para el delay en cada reintento subsiguiente.
- `max_delay_s`: (int) Tope máximo de espera (en segundos) para cualquier reintento.

**Sección `[logging]`:**
- `log_dir`: (string) Directorio relativo donde se guardan los archivos de log.
- `level`: (string) Nivel de logs (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`).
- `max_bytes`: (int) Tamaño máximo en bytes antes de rotar logs (por defecto 10MB).
- `backup_count`: (int) Archivos rotados a conservar.
- `capture_job_output`: (bool) Captura y persiste stdout/stderr de cada job por separado.
- `output_tail_lines`: (int) Máximo de líneas a retener en la DB por cada stream (stdout/stderr).

**Sección `[database]`:**
- `path`: (string) Ruta relativa de la base de datos SQLite.
- `history_retention_days`: (int) Días que se conservan los registros de ejecuciones antiguas.
- `cleanup_interval_hours`: (int) Cada cuántas horas corre la tarea de purga automática.

> **Nota:** La purga automática elimina registros de ejecución más antiguos que `history_retention_days` días. Se ejecuta de forma periódica cada `cleanup_interval_hours` horas mientras el daemon esté corriendo.

**Sección `[ipc]`:**
- `pipe_name`: (string) Nombre del Named Pipe usado para IPC (`\\\\.\\pipe\\wcrond`).
- `client_timeout`: (int) Segundos que el cliente CLI espera respuesta antes de fallar.

**Sección `[watchdog]`:**
- `check_interval`: (int) Segundos entre evaluaciones para detectar y procesar trabajos zombis.
- `auto_kill_zombies`: (bool) Activa la terminación automática de procesos huérfanos/excedidos.

## 3. Configuración de Tareas (`wcrontab.toml`)

Los trabajos (jobs) se definen en `%USERPROFILE%\.wcrond\wcrontab.toml`. También puedes colocar archivos de jobs adicionales en el directorio `%USERPROFILE%\.wcrond\jobs.d/`.

**Estructura de un Job:**

```toml
[jobs.mi_tarea_diaria]
schedule = "0 3 * * *"
command = "C:\\scripts\\mantenimiento.ps1"
shell = "powershell"
working_dir = "C:\\scripts"
timeout = 1800
overlap_policy = "skip"
enabled = true
silent = false

[jobs.mi_tarea_diaria.env]
PATH = "C:\\Python310;C:\\Windows\\System32"
API_KEY = "secreto123"

[jobs.mi_tarea_diaria.retry]
max_retries = 3
initial_delay_s = 60
backoff_multiplier = 2.0
max_delay_s = 600

[jobs.respaldo_con_hooks]
schedule = "0 2 * * *"
command = "C:\\scripts\\backup.ps1"
on_success = "echo Backup OK >> C:\\logs\\hooks.log"
on_failure = "powershell Send-MailMessage -To admin@empresa.com -Subject 'Backup FALLÓ'"
```

### Propiedades de Job en `wcrontab.toml`

**Propiedades Base:**
- `schedule`: (string) Expresión CRON (5 campos o macro como `@daily`).
- `command`: (string) Comando a ejecutar.
- `shell`: (string, opcional) Shell específico, sobreescribe al global.
- `working_dir`: (string, opcional) Directorio de ejecución, sobreescribe al global.
- `timeout`: (int, opcional) Tiempo límite en segundos para la tarea.
- `overlap_policy`: (string, opcional) Comportamiento ante ejecuciones encimadas: `allow` (permitir), `skip` (omitir), o `kill_previous` (matar ejecución anterior).
- `enabled`: (bool) Habilita o deshabilita la tarea de forma individual.
- `silent`: (bool, opcional) Suprime la ventana de consola en Windows (`CREATE_NO_WINDOW`). Por defecto es `true`. Si tu tarea lanza una UI gráfica, colócalo en `false`.
- `on_success`: (string, opcional) Comando a ejecutar automáticamente cuando el job termina con éxito (exit code 0). Se ejecuta como subproceso independiente.
- `on_failure`: (string, opcional) Comando a ejecutar automáticamente cuando el job falla (exit code ≠ 0) o expira por timeout.

**Subsección `[...env]`:**
- Define pares clave-valor que se inyectan como variables de entorno directamente en el subproceso de la tarea.

**Subsección `[...retry]`:**
- Sobrescribe la política de reintentos global para esta tarea específica (`max_retries`, `initial_delay_s`, `backoff_multiplier`, `max_delay_s`).

### Expresiones Cron Soportadas

wcrond soporta el formato estándar de 5 campos y los siguientes atajos:

| Shortcut | Descripción |
|----------|-------------|
| `@yearly` / `@annually` | Una vez al año (1 de enero a medianoche) |
| `@monthly` | Primer día de cada mes |
| `@weekly` | Cada domingo a medianoche |
| `@daily` / `@midnight`| Cada día a medianoche |
| `@hourly` | Cada hora en punto |

## 4. Organización con `jobs.d/`

Puedes estructurar tus trabajos en múltiples archivos. Cualquier archivo con extensión `.toml` dentro del directorio `%USERPROFILE%\.wcrond\jobs.d/` será analizado automáticamente por wcrond.

## 5. Referencia de Comandos (CLI)

El sistema provee dos binarios principales: `wcrond` (para gestionar el servicio base) y `wcrond-ctl` (para monitorear e interactuar con los trabajos).

### 5.1 Comandos del Demonio (`wcrond`)

Estos comandos controlan el ciclo de vida del servicio en background.

*   `wcrond init [--config <ruta>]`
    *   **Descripción:** Genera la estructura de carpetas (`jobs.d/`, `logs/`) y los archivos de configuración por defecto (`wcrond.toml`, `wcrontab.toml`) en el directorio especificado. Por defecto utiliza `%USERPROFILE%\.wcrond`.
    *   **Ejemplo:** `wcrond init`

*   `wcrond start [--foreground] [--config <ruta>]`
    *   **Descripción:** Inicia el demonio. Sin banderas, el proceso se bifurca silenciosamente al fondo (background process).
    *   **Flags:**
        *   `--foreground`: Ejecuta el demonio anexado a la terminal actual (ideal para debugging o contenedores).
        *   `--config <ruta>`: Especifica un archivo de configuración base distinto.
    *   **Ejemplo:** `wcrond start --foreground`

*   `wcrond status [--config <ruta>]`
    *   **Descripción:** Comprueba si el demonio está activo intentando conectarse a su pipe IPC. Retorna silenciosamente un exit code `0` si está corriendo, o `1` en caso contrario. Útil para scripts de validación.
    *   **Ejemplo:** `wcrond status`

*   `wcrond stop [--config <ruta>]`
    *   **Descripción:** Envía de forma segura una señal de apagado al demonio en ejecución para que cierre su base de datos y detenga tareas planificadas.
    *   **Ejemplo:** `wcrond stop`

### 5.2 Comandos de Control (`wcrond-ctl`)

Herramienta diseñada para supervisar y operar sobre los trabajos programados en un demonio en ejecución.

**Flag global:**
- `--timeout <segundos>`: (float, opcional) Tiempo máximo de espera para la comunicación IPC con el daemon. Default: `5` segundos. Ejemplo: `wcrond-ctl --timeout 15 status`

*   `status`
    *   **Descripción:** Imprime el estado del demonio, su tiempo de actividad (uptime), total de jobs registrados, hilos de ejecución activos y trabajos encolados por reintento.
    *   **Ejemplo:** `wcrond-ctl status`

*   `list`
    *   **Descripción:** Muestra una tabla con todos los trabajos configurados, su expresión cron, si están habilitados, y la fecha de su última ejecución.
    *   **Ejemplo:** `wcrond-ctl list`

*   `history [--job <id>] [--last <N>] [--since <ISO>]`
    *   **Descripción:** Expone el registro de las ejecuciones previas (exitosas o fallidas), detallando los tiempos, duración, y el código de salida.
    *   **Flags:**
        *   `--job <id>`: Filtra el historial solo para el trabajo con este ID.
        *   `--last <N>`: Limita la salida a los últimos N registros.
        *   `--since <YYYY-MM-DD>`: Muestra solo registros desde esta fecha.
    *   **Ejemplo:** `wcrond-ctl history --job respaldo_diario --last 5`

*   `retries`
    *   **Descripción:** Imprime la cola interna de reintentos activos mostrando el job, número de intento y a qué hora será relanzado.
    *   **Ejemplo:** `wcrond-ctl retries`

*   `run <job_id>`
    *   **Descripción:** Pone un trabajo en ejecución de inmediato, sin importar su horario programado (`schedule`). 
    *   **Ejemplo:** `wcrond-ctl run limpieza_cache`

*   `kill <job_id>`
    *   **Descripción:** Si el trabajo está actualmente en ejecución, envía una señal para terminar (matar) el subproceso a nivel del sistema operativo.
    *   **Ejemplo:** `wcrond-ctl kill script_lento`

*   `cancel-retry <job_id>`
    *   **Descripción:** Si un trabajo falló y está esperando en la cola para su próximo reintento (backoff), esto purgará dicho trabajo de la cola evitando que se reintente.
    *   **Ejemplo:** `wcrond-ctl cancel-retry reporte_falla`

*   `disable <job_id>` / `enable <job_id>`
    *   **Descripción:** Pausa (disable) o reanuda (enable) dinámicamente un trabajo, afectando solo al estado en memoria del demonio.
    *   **Nota:** Al deshabilitar un trabajo, los reintentos pendientes de dicho trabajo también se cancelan automáticamente.
    *   **Ejemplo:** `wcrond-ctl disable notificaciones_email`

*   `logs [--job <id>] [--tail <N>]`
    *   **Descripción:** Muestra la salida estándar y error capturada de las tareas directamente en consola.
    *   **Flags:**
        *   `--job <id>`: Ve la salida de un solo trabajo.
        *   `--tail <N>`: Limita las líneas de log a leer.
    *   **Ejemplo:** `wcrond-ctl logs --job respaldo_diario --tail 50`

*   `zombies`
    *   **Descripción:** Lista posibles trabajos detectados como "zombis" (aquéllos en base de datos como RUNNING pero cuyo subproceso se extinguió sin notificar, o superaron drásticamente su `timeout`).
    *   **Ejemplo:** `wcrond-ctl zombies`

*   `next [--job <id>]`
    *   **Descripción:** Calcula y muestra exactamente a qué fecha y hora está programado que se ejecute la próxima vez un trabajo.
    *   **Ejemplo:** `wcrond-ctl next --job respaldo_diario`

*   `reload`
    *   **Descripción:** Refresca `wcrond.toml` y toda la carpeta `jobs.d/` para adoptar cambios sin reiniciar todo el demonio.
    *   **Ejemplo:** `wcrond-ctl reload`

*   `validate`
    *   **Descripción:** Verifica estáticamente los archivos `.toml` comprobando errores de formato cron y alertando de claves inválidas.
    *   **Ejemplo:** `wcrond-ctl validate`

## 6. Resolución de Problemas (Troubleshooting)

**Problema:** Mi tarea no se ejecuta.
*Solución:* Revisa si está habilitada (`enabled = true`). Usa `wcrond-ctl list` para confirmarlo. Revisa si la sintaxis cron es válida usando `wcrond-ctl validate`.

**Problema:** La tarea se queda "colgada".
*Solución:* Si la tarea excede su `timeout`, el watchdog de wcrond la terminará automáticamente. Puedes usar `wcrond-ctl zombies` para ver si hay procesos residuales y `wcrond-ctl kill <job>` para matarlos manualmente.

**Problema:** Quiero forzar una tarea para probarla.
*Solución:* Usa el comando `wcrond-ctl run <nombre_del_job>`.

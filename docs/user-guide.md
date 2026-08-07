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
max_bytes = 10485760
backup_count = 5
capture_job_output = true

[database]
path = "data/wcrond.db"
history_retention_days = 30

[watchdog]
check_interval = 30
auto_kill_zombies = true
```

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

[jobs.mi_tarea_diaria.env]
PATH = "C:\\Python310;C:\\Windows\\System32"
API_KEY = "secreto123"

[jobs.mi_tarea_diaria.retry]
max_retries = 3
initial_delay_s = 60
backoff_multiplier = 2.0
max_delay_s = 600
```

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

## 5. Monitoreo y Supervisión

Utiliza la herramienta `wcrond-ctl` para supervisar tu sistema.

- **Estado del daemon**: `wcrond-ctl status`
- **Lista de trabajos**: `wcrond-ctl list`
- **Historial**: `wcrond-ctl history`
- **Próximas ejecuciones**: `wcrond-ctl next`
- **Logs**: `wcrond-ctl logs` o `wcrond-ctl logs --job nombre_job`

## 6. Resolución de Problemas (Troubleshooting)

**Problema:** Mi tarea no se ejecuta.
*Solución:* Revisa si está habilitada (`enabled = true`). Usa `wcrond-ctl list` para confirmarlo. Revisa si la sintaxis cron es válida usando `wcrond-ctl validate`.

**Problema:** La tarea se queda "colgada".
*Solución:* Si la tarea excede su `timeout`, el watchdog de wcrond la terminará automáticamente. Puedes usar `wcrond-ctl zombies` para ver si hay procesos residuales y `wcrond-ctl kill <job>` para matarlos manualmente.

**Problema:** Quiero forzar una tarea para probarla.
*Solución:* Usa el comando `wcrond-ctl run <nombre_del_job>`.

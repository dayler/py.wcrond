# Guía de Desarrollo

Esta guía detalla cómo configurar un entorno de desarrollo para contribuir al proyecto **wcrond**.

## 1. Setup del Entorno

1.  Clona el repositorio:
    ```powershell
    git clone https://github.com/tu-org/wcrond.git
    cd wcrond
    ```
2.  Crea un entorno virtual:
    ```powershell
    python -m venv .venv
    .venv\Scripts\Activate.ps1
    ```
3.  Instala las dependencias en modo desarrollo (incluyendo dependencias de test):
    ```powershell
    pip install -e .[dev,test]
    ```

## 2. Estructura del Código

- `src/wcrond/`: Código fuente principal del daemon.
  - `daemon.py`: Orquestador, ciclo de vida del daemon.
  - `scheduler.py`: Loop principal que evalúa tareas y reintentos.
  - `executor.py`: Thread pool y ejecución de `subprocess`.
  - `ipc.py`: Servidor de Named Pipes.
- `src/wcrond_ctl/`: Código fuente de la herramienta CLI.
  - `cli.py`: Configuración de `argparse` y subcomandos.
  - `client.py`: Cliente de Named Pipes para enviar comandos al daemon.
- `tests/`: Pruebas unitarias y de integración.

## 3. Ejecución de Tests

Para ejecutar los tests de forma adecuada y segura, asegúrate de cumplir con los siguientes pasos:

1.  Activa tu entorno virtual (si estás usando uno).
2.  Instala el proyecto y sus dependencias de desarrollo/test (incluye `pytest`):
    ```powershell
    pip install -e .[dev,test]
    ```
3.  Instala el plugin para reportes de cobertura de código:
    ```powershell
    pip install pytest-cov
    ```

Una vez cumplidos los requisitos, usa `pytest` para la ejecución de pruebas:

```powershell
# Ejecutar todos los tests
pytest

# Ejecutar tests con reporte de cobertura en consola
pytest --cov=wcrond --cov=wcrond_ctl

# Ejecutar tests y generar un reporte HTML detallado
pytest --cov=wcrond --cov=wcrond_ctl --cov-report=html

# Ejecutar un archivo específico
pytest tests/test_scheduler.py
```

### Reporte de Cobertura (HTML)

Si ejecutas el comando con `--cov-report=html`, se generará una carpeta llamada `htmlcov/` en la raíz del proyecto. Para analizar la cobertura línea por línea:
1. Navega a la carpeta `htmlcov/`.
2. Abre el archivo `index.html` con cualquier navegador web.
3. Haz clic en los archivos listados para ver exactamente qué líneas de código no están siendo cubiertas por los tests (aparecerán resaltadas en rojo).

## 4. Agregar un Nuevo Comando CLI

Para añadir un nuevo comando a `wcrond-ctl`:

1.  **En el CLI (`src/wcrond_ctl/cli.py`)**:
    Agrega el subparser usando `argparse` y define la función que llamará a `client.send_request({"cmd": "tu_nuevo_comando", ...})`.
2.  **En el Cliente IPC (`src/wcrond_ctl/client.py`)** (opcional):
    Puedes crear una función envoltorio para el nuevo comando si requiere pre-procesamiento.
3.  **En el Servidor IPC (`src/wcrond/ipc.py`)**:
    Añade un manejador en el diccionario `handlers` (o en un `match`/`if-elif` interno).
4.  **En el Core (`src/wcrond/...`)**:
    Implementa la lógica del negocio necesaria en `scheduler.py`, `state.py`, o donde corresponda, para que el IPC pueda llamarla de forma segura.

## 5. Convenciones de Código

- Utiliza Type Hints (anotaciones de tipos) en todas las funciones nuevas.
- Mantén el código compatible con Python 3.10+.
- Asegúrate de que las operaciones de IPC hacia el Scheduler sean thread-safe, ya que el IPC y el Scheduler corren en threads diferentes (el uso de colas o el bloqueo del DB en `state.py` debe ser manejado adecuadamente).
- Todo PR debe pasar los formateadores (`black`, `isort`) y `flake8` o `pylint`.

# MS-01: Fundación del Proyecto

> **Estado General:** 🟢 Completado  
> **Última Actualización:** 2026-08-07  
> **Razón/Descripción:** Estructura creada, dependencias instaladas y tests exitosos

---

## 1. Objetivo y Alcance

Establecer la estructura base del proyecto `wcrond` incluyendo:

- Estructura de directorios del repositorio según el PRD (sección 5.1).
- Archivo `pyproject.toml` con metadatos, dependencias y entry points.
- Esqueleto inicial de todos los paquetes Python (`src/wcrond/`, `src/wcrond_ctl/`, `tests/`).
- Configuración de herramientas de desarrollo (pytest, linting).
- Archivos de ejemplo (`examples/wcrond.toml`, `examples/wcrontab.toml`).
- Scripts de instalación/desinstalación PowerShell.

### Enfoque Técnico

1. Crear la estructura de directorios completa.
2. Generar `pyproject.toml` según la especificación del PRD sección 8.
3. Crear archivos `__init__.py` con versión y metadatos.
4. Crear `__main__.py` con esqueleto de entry points (`main()` stub).
5. Copiar los archivos de ejemplo del PRD secciones 6.1 y 6.2.
6. Crear `scripts/install.ps1` y `scripts/uninstall.ps1` según PRD sección 7.
7. Verificar que `pip install -e .` funciona correctamente.

---

## 2. Dependencias

| Milestone | Estado | Tipo |
|-----------|--------|------|
| Ninguno | — | Este es el milestone raíz |

---

## 3. Plan de Unit Tests

### Estrategia

Validar que la estructura del proyecto es correcta y las dependencias se resuelven.

### Tests a Implementar

| Test | Archivo | Descripción | Cobertura |
|------|---------|-------------|-----------|
| `test_import_wcrond` | `tests/test_structure.py` | Verificar que `import wcrond` funciona | Estructura de paquetes |
| `test_import_wcrond_ctl` | `tests/test_structure.py` | Verificar que `import wcrond_ctl` funciona | Estructura de paquetes |
| `test_version` | `tests/test_structure.py` | Verificar que `wcrond.__version__` es "1.0.0" | Metadatos |
| `test_entry_points` | `tests/test_structure.py` | Verificar que los entry points son invocables | Entry points |

### Cobertura Esperada

- **Objetivo:** 100% de los módulos son importables.
- **Comando:** `pytest tests/test_structure.py -v`

---

## 4. Plan de Pruebas Automatizadas

### Validación de Instalación

```powershell
# Test automatizado de instalación
pip install -e . 2>&1 | Select-String "Successfully installed"
python -c "import wcrond; print(wcrond.__version__)"
python -c "import wcrond_ctl; print('OK')"
pytest tests/test_structure.py -v
```

### Criterios de Éxito

- `pip install -e .` completa sin errores.
- Todos los imports son exitosos.
- Los entry points `wcrond` y `wcrond-ctl` están registrados.

---

## 5. Control de Estado (Semáforos)

| # | Tarea | Estado | Razón/Descripción |
|---|-------|--------|-------------------|
| 1 | Crear estructura de directorios | 🟢 | Completado |
| 2 | Generar `pyproject.toml` | 🟢 | Completado |
| 3 | Crear esqueletos de paquetes (`__init__.py`, `__main__.py`) | 🟢 | Completado |
| 4 | Crear archivos de ejemplo y scripts PS1 | 🟢 | Completado |

---

## 6. Archivos a Crear/Modificar

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `pyproject.toml` | CREAR | Definición del paquete Python |
| `src/wcrond/__init__.py` | CREAR | `__version__ = "1.0.0"` |
| `src/wcrond/__main__.py` | CREAR | Entry point stub con `main()` |
| `src/wcrond/daemon.py` | CREAR | Stub vacío con docstring |
| `src/wcrond/scheduler.py` | CREAR | Stub vacío con docstring |
| `src/wcrond/job.py` | CREAR | Stub vacío con docstring |
| `src/wcrond/parser.py` | CREAR | Stub vacío con docstring |
| `src/wcrond/executor.py` | CREAR | Stub vacío con docstring |
| `src/wcrond/retry.py` | CREAR | Stub vacío con docstring |
| `src/wcrond/watchdog.py` | CREAR | Stub vacío con docstring |
| `src/wcrond/state.py` | CREAR | Stub vacío con docstring |
| `src/wcrond/ipc.py` | CREAR | Stub vacío con docstring |
| `src/wcrond/config.py` | CREAR | Stub vacío con docstring |
| `src/wcrond/logging_config.py` | CREAR | Stub vacío con docstring |
| `src/wcrond_ctl/__init__.py` | CREAR | Paquete CLI |
| `src/wcrond_ctl/__main__.py` | CREAR | Entry point stub CLI |
| `src/wcrond_ctl/cli.py` | CREAR | Stub vacío |
| `src/wcrond_ctl/client.py` | CREAR | Stub vacío |
| `src/wcrond_ctl/formatters.py` | CREAR | Stub vacío |
| `tests/__init__.py` | CREAR | Paquete de tests |
| `tests/test_structure.py` | CREAR | Tests de estructura |
| `examples/wcrond.toml` | CREAR | Ejemplo de configuración del PRD |
| `examples/wcrontab.toml` | CREAR | Ejemplo de jobs del PRD |
| `scripts/install.ps1` | CREAR | Script de instalación |
| `scripts/uninstall.ps1` | CREAR | Script de desinstalación |
| `README.md` | CREAR | Placeholder README |
| `LICENSE` | CREAR | Licencia MIT |

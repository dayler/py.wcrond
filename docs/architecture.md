# Arquitectura As-Built

Este documento describe la arquitectura final implementada de **wcrond** (Windows Cron Daemon).

## 1. Stack Tecnológico

- **Lenguaje**: Python 3.10+
- **Cron Parsing**: `croniter`
- **Concurrencia**: `concurrent.futures.ThreadPoolExecutor`
- **Subprocesos**: `subprocess.Popen`
- **IPC**: Named Pipes (Win32) vía `pywin32`
- **Configuración**: TOML (`tomllib` o `tomli`)
- **Estado/Historial**: SQLite 3

## 2. Diagrama de Componentes

```mermaid
graph TB
    subgraph "wcrond Process (Daemon)"
        direction TB
        ML["Main Loop<br/>(Scheduler)"]
        CP["Config Parser<br/>(TOML)"]
        CE["Cron Engine<br/>(croniter)"]
        TP["Thread Pool<br/>(Bounded)"]
        RM["Retry Manager<br/>(Backoff)"]
        WD["Watchdog<br/>(Zombie Detector)"]
        DB["State Store<br/>(SQLite)"]
        LG["Logger<br/>(Rotating Files)"]
        IPC["IPC Server<br/>(Named Pipe)"]

        ML --> CP
        ML --> CE
        ML --> TP
        ML --> RM
        ML --> WD
        ML --> DB
        ML --> LG
        ML --> IPC
        TP --> DB
        TP --> LG
        RM --> TP
        WD --> TP
    end

    subgraph "CLI (wcrond-ctl)"
        CTL["wcrond-ctl<br/>Command Line Tool"]
    end

    subgraph "User Files"
        CF["wcrontab<br/>(Job Definitions)"]
        SC["wcrond.toml<br/>(System Config)"]
    end

    subgraph "Runtime Data"
        SDB["wcrond.db<br/>(SQLite)"]
        LOG["logs/<br/>(Rotating Logs)"]
        PID["wcrond.pid<br/>(PID File)"]
    end

    CTL -- "Named Pipe" --> IPC
    CP -- "reads" --> CF
    CP -- "reads" --> SC
    DB -- "reads/writes" --> SDB
    LG -- "writes" --> LOG
    ML -- "writes" --> PID

    style ML fill:#4A90D9,color:#fff
    style TP fill:#7B68EE,color:#fff
    style RM fill:#E67E22,color:#fff
    style WD fill:#E74C3C,color:#fff
    style DB fill:#27AE60,color:#fff
    style IPC fill:#16A085,color:#fff
    style CTL fill:#8E44AD,color:#fff
```

## 3. Flujo del Scheduler

El Scheduler es el núcleo de wcrond, ejecutándose en el hilo principal y comprobando las tareas cada segundo.

```mermaid
flowchart TD
    A["Daemon Start"] --> B["Load wcrond.toml"]
    B --> C["Parse wcrontab files"]
    C --> D["Initialize Thread Pool"]
    D --> E["Initialize SQLite DB"]
    E --> F["Start IPC Server Thread"]
    F --> G["Start Watchdog Thread"]
    G --> H{"Tick: Check Clock<br/>(every 1s)"}

    H --> I{"¿New Minute<br/>Boundary?"}
    I -- No --> H
    I -- Yes --> J["Evaluate all jobs<br/>against current time"]

    J --> K{"¿Job matches<br/>current time?"}
    K -- No --> J
    K -- Yes --> L{"¿Job disabled?"}

    L -- Yes --> M["Skip, log 'skipped'"]
    M --> J
    L -- No --> N{"¿Job already<br/>running?"}

    N -- Yes --> O{"¿overlap_policy?"}
    O -- "skip" --> P["Skip, log 'overlap'"]
    O -- "allow" --> Q["Submit to Thread Pool"]
    O -- "kill_previous" --> R["Kill running instance<br/>then submit new"]
    N -- No --> Q

    P --> J
    R --> Q
    Q --> S["Worker Thread Executes Job"]

    S --> T{"¿Exit Code == 0?"}
    T -- Yes --> U["Record SUCCESS in DB"]
    T -- No --> V{"¿Retries remaining?"}

    V -- Yes --> W["Schedule Retry<br/>(incremental backoff)"]
    V -- No --> X["Record FAILED in DB"]

    W --> S
    U --> H
    X --> H

    style A fill:#2ECC71,color:#fff
    style H fill:#4A90D9,color:#fff
    style Q fill:#7B68EE,color:#fff
    style W fill:#E67E22,color:#fff
    style U fill:#27AE60,color:#fff
    style X fill:#E74C3C,color:#fff
```

## 4. Comunicación IPC

wcrond utiliza Named Pipes de Windows para permitir la comunicación bidireccional entre el daemon y la utilidad CLI.

```mermaid
sequenceDiagram
    participant User as Usuario (Terminal)
    participant CTL as wcrond-ctl
    participant IPC as IPC Server (Named Pipe)
    participant Sched as Scheduler
    participant DB as SQLite

    User->>CTL: wcrond-ctl status
    CTL->>IPC: {"cmd": "status"}
    IPC->>Sched: query_status()
    Sched->>DB: SELECT running jobs
    DB-->>Sched: results
    Sched-->>IPC: {jobs: [...], uptime: ...}
    IPC-->>CTL: JSON response
    CTL-->>User: Formatted table
```

## 5. Estados de Ejecución (Jobs)

El ciclo de vida de un Job está claramente definido e incluye transiciones para timeouts, cancelaciones y reintentos.

```mermaid
stateDiagram-v2
    [*] --> IDLE : Job definido
    IDLE --> QUEUED : Cron match / Force run
    QUEUED --> RUNNING : Thread disponible
    RUNNING --> SUCCESS : exit_code == 0
    RUNNING --> FAILED : exit_code != 0
    RUNNING --> TIMEOUT : Excede timeout
    RUNNING --> KILLED : Terminación forzada (CLI)
    TIMEOUT --> FAILED : Registrar como fallo
    FAILED --> RETRY_PENDING : Retries disponibles
    RETRY_PENDING --> QUEUED : Backoff timer expira
    RETRY_PENDING --> CANCELLED : Retry cancelado (CLI)
    SUCCESS --> IDLE : Espera siguiente schedule
    FAILED --> IDLE : Sin retries restantes
    KILLED --> IDLE : Registrar como killed
    CANCELLED --> IDLE : Registrar como cancelled

    state RUNNING {
        [*] --> Executing
        Executing --> WaitingResult : subprocess started
        WaitingResult --> [*] : subprocess finished
    }
```

## 6. Decisiones de Diseño Clave

1.  **Named Pipes en lugar de Sockets TCP**: Mejora la seguridad (ACLs de Windows nativas) y evita conflictos de red/firewalls.
2.  **ThreadPoolExecutor en lugar de asyncio para subprocesos**: La naturaleza bloqueante del sistema operativo al esperar subprocesos encaja mejor con un modelo de Thread Pool para las ejecuciones concurrentes, manteniendo libre el loop principal del scheduler.
3.  **Configuración TOML**: Moderno, legible y seguro. Con soporte nativo en Python 3.11+.
4.  **SQLite como State Store**: Proporciona almacenamiento robusto, consultable y persistente sin requerir un servidor de base de datos externo.

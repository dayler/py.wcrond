import sqlite3
import threading
import uuid
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta

@dataclass
class TaskExecution:
    execution_id: str
    job_id: str
    job_name: str
    start_time: str
    end_time: Optional[str]
    duration_s: Optional[float]
    exit_code: Optional[int]
    status: str
    attempt: int
    pid: Optional[int]
    stdout_tail: Optional[str]
    stderr_tail: Optional[str]
    trigger: str

class StateStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            isolation_level=None
        )
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        with self._lock:
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS executions (
                    execution_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    job_name TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    duration_s REAL,
                    exit_code INTEGER,
                    status TEXT NOT NULL,
                    attempt INTEGER NOT NULL,
                    pid INTEGER,
                    stdout_tail TEXT,
                    stderr_tail TEXT,
                    trigger TEXT NOT NULL
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS retry_queue (
                    job_id TEXT PRIMARY KEY,
                    attempt INTEGER NOT NULL,
                    next_retry_at TEXT NOT NULL,
                    reason TEXT
                )
            """)

    def record_start(self, job_id: str, job_name: str, pid: Optional[int], trigger: str, attempt: int) -> str:
        execution_id = str(uuid.uuid4())
        start_time = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self.conn.execute("""
                INSERT INTO executions (
                    execution_id, job_id, job_name, start_time,
                    status, attempt, pid, trigger
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                execution_id, job_id, job_name, start_time,
                "RUNNING", attempt, pid, trigger
            ))
        return execution_id

    def record_end(self, execution_id: str, exit_code: Optional[int], status: str, stdout_tail: Optional[str], stderr_tail: Optional[str]):
        end_time = datetime.now(timezone.utc).isoformat()
        
        with self._lock:
            cursor = self.conn.execute(
                "SELECT start_time FROM executions WHERE execution_id = ?",
                (execution_id,)
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Execution {execution_id} not found")
            
            start_time = datetime.fromisoformat(row["start_time"])
            end_dt = datetime.fromisoformat(end_time)
            duration_s = (end_dt - start_time).total_seconds()
            
            self.conn.execute("""
                UPDATE executions
                SET end_time = ?, duration_s = ?, exit_code = ?, status = ?, stdout_tail = ?, stderr_tail = ?
                WHERE execution_id = ?
            """, (end_time, duration_s, exit_code, status, stdout_tail, stderr_tail, execution_id))

    def _row_to_execution(self, row: sqlite3.Row) -> TaskExecution:
        return TaskExecution(
            execution_id=row["execution_id"],
            job_id=row["job_id"],
            job_name=row["job_name"],
            start_time=row["start_time"],
            end_time=row["end_time"],
            duration_s=row["duration_s"],
            exit_code=row["exit_code"],
            status=row["status"],
            attempt=row["attempt"],
            pid=row["pid"],
            stdout_tail=row["stdout_tail"],
            stderr_tail=row["stderr_tail"],
            trigger=row["trigger"]
        )

    def get_history(self, job_id: Optional[str] = None, limit: int = 10) -> List[TaskExecution]:
        query = "SELECT * FROM executions"
        params = []
        if job_id:
            query += " WHERE job_id = ?"
            params.append(job_id)
        query += " ORDER BY start_time DESC LIMIT ?"
        params.append(limit)
        
        cursor = self.conn.execute(query, params)
        return [self._row_to_execution(row) for row in cursor.fetchall()]

    def get_running_jobs(self) -> List[TaskExecution]:
        cursor = self.conn.execute(
            "SELECT * FROM executions WHERE status = 'RUNNING' ORDER BY start_time DESC"
        )
        return [self._row_to_execution(row) for row in cursor.fetchall()]

    def add_retry(self, job_id: str, attempt: int, next_retry_at: str, reason: str):
        with self._lock:
            self.conn.execute("""
                INSERT OR REPLACE INTO retry_queue (job_id, attempt, next_retry_at, reason)
                VALUES (?, ?, ?, ?)
            """, (job_id, attempt, next_retry_at, reason))

    def remove_retry(self, job_id: str):
        with self._lock:
            self.conn.execute("DELETE FROM retry_queue WHERE job_id = ?", (job_id,))

    def get_retry_queue(self) -> List[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM retry_queue ORDER BY next_retry_at ASC")
        return [dict(row) for row in cursor.fetchall()]

    def cleanup_old_records(self, days: int):
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        with self._lock:
            self.conn.execute("DELETE FROM executions WHERE start_time < ?", (cutoff,))

    def close(self):
        self.conn.close()

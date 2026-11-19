"""Testlerin gerçek analiz geçmişini kirletmemesi için izole SQLite dosyası."""

import os
import tempfile
from pathlib import Path

_TEST_DB = Path(tempfile.gettempdir()) / f"pcb-inspection-tests-{os.getpid()}.db"
os.environ["HISTORY_DB_PATH"] = str(_TEST_DB)

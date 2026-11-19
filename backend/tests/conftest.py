"""Testlerin gerçek analiz geçmişini kirletmemesi için izole SQLite dosyası."""

import os
import tempfile
from pathlib import Path

_TEST_DB = Path(tempfile.gettempdir()) / f"pcb-inspection-tests-{os.getpid()}.db"
os.environ["HISTORY_DB_PATH"] = str(_TEST_DB)

# Yerel ölçüm JSON'u varsa testlerin "ölçülmedi" varsayımını bozmasın.
_TEST_EVAL_DIR = Path(tempfile.gettempdir()) / f"pcb-inspection-eval-tests-{os.getpid()}"
_TEST_EVAL_DIR.mkdir(parents=True, exist_ok=True)
os.environ["EVALUATION_OUTPUT_DIR"] = str(_TEST_EVAL_DIR)

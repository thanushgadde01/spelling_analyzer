"""storage.py - master.csv persistence (thread-safe)."""
import threading
from pathlib import Path

import pandas as pd

_lock = threading.Lock()

COLUMNS = [
    "Name", "Age", "Study", "Graduated", "Occupation", "Hobbies", "Goal", "Self_Intro",
    "Original_Input", "Corrected_Input", "Total_Words", "Mistakes", "Mistake_Percentage",
    "Grammar_Issues", "Level", "Feedback",
]


def load_or_create_master_csv(path):
    path = Path(path)
    if path.exists() and path.stat().st_size > 0:
        return pd.read_csv(path)
    return pd.DataFrame(columns=COLUMNS)


def append_entry_to_master(entry: dict, path):
    """Append one row. Old CSVs without the Grammar_Issues column keep working."""
    with _lock:
        df = load_or_create_master_csv(path)
        df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
        df.to_csv(path, index=False)
        return df

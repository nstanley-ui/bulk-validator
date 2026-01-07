import pandas as pd
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class Issue(BaseModel):
    row_idx: int
    column: str
    severity: str  # BLOCKER, WARNING, PASS
    message: str
    suggested_fix: Optional[str] = None
    original_value: Any = None

class SummaryStats(BaseModel):
    total_rows: int
    clean_rows: int
    rows_with_issues: int
    total_issues: int
    severity_counts: Dict[str, int]

class ValidationResult(BaseModel):
    platform: str
    issues: List[Issue]
    summary: SummaryStats
    # The dataframes are handled outside pydantic for performance
    # But we define the contract for the engine output here

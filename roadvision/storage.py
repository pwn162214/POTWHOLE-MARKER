"""CSV persistence for citizen pothole reports."""

import csv
import threading
from pathlib import Path
from typing import Dict, List


REPORT_FIELDS = (
    "Citizen Name",
    "Location",
    "Description",
    "Image Path",
    "AI Verification Result",
    "Report Status",
    "Credit Points",
)
LEGACY_REPORT_FIELDS = REPORT_FIELDS[:-1]
CREDIT_POINTS_PER_REPORT = 10


class ReportStorageError(Exception):
    """Raised when the report CSV cannot be read or written."""


class CsvReportStore:
    """Read and append report rows in a local CSV file."""

    def __init__(self, csv_path: Path) -> None:
        self.csv_path = Path(csv_path)
        self._lock = threading.Lock()

    def load_reports(self) -> List[Dict[str, str]]:
        """Load all saved reports, creating an empty CSV when needed."""
        with self._lock:
            try:
                return self._load_unlocked()
            except ReportStorageError:
                raise
            except (OSError, csv.Error) as error:
                raise ReportStorageError(f"Could not read reports CSV: {error}") from error

    def append_report(self, report: Dict[str, str]) -> None:
        """Append a verified report and write the header for a new file."""
        with self._lock:
            try:
                self._load_unlocked()
                report_row = {field: report.get(field, "") or "" for field in REPORT_FIELDS}
                if report_row["AI Verification Result"] == "Pothole Detected":
                    report_row["Credit Points"] = str(CREDIT_POINTS_PER_REPORT)
                else:
                    report_row["Credit Points"] = "0"
                with self.csv_path.open("a", newline="", encoding="utf-8") as file:
                    writer = csv.DictWriter(file, fieldnames=REPORT_FIELDS)
                    writer.writerow(report_row)
            except ReportStorageError:
                raise
            except (OSError, csv.Error) as error:
                raise ReportStorageError(f"Could not save report: {error}") from error

    def _load_unlocked(self) -> List[Dict[str, str]]:
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.csv_path.exists() or self.csv_path.stat().st_size == 0:
            self._write_header()
            return []

        with self.csv_path.open("r", newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            fields = reader.fieldnames
            if fields not in (list(REPORT_FIELDS), list(LEGACY_REPORT_FIELDS)):
                raise ReportStorageError(
                    "The reports CSV has unexpected columns. Move or rename it, then restart RoadVision."
                )
            is_legacy = fields == list(LEGACY_REPORT_FIELDS)
            reports = []
            for row in reader:
                normalized = {field: row.get(field, "") or "" for field in LEGACY_REPORT_FIELDS}
                if is_legacy:
                    normalized["Credit Points"] = str(
                        CREDIT_POINTS_PER_REPORT
                        if normalized["AI Verification Result"] == "Pothole Detected"
                        else 0
                    )
                else:
                    try:
                        points = int(row.get("Credit Points", "0") or 0)
                    except ValueError as error:
                        raise ReportStorageError("A report has an invalid Credit Points value.") from error
                    if points < 0:
                        raise ReportStorageError("Credit Points cannot be negative.")
                    normalized["Credit Points"] = str(points)
                reports.append(normalized)

        if is_legacy:
            self._write_reports(reports)
        return reports

    def _write_reports(self, reports: List[Dict[str, str]]) -> None:
        temporary_path = self.csv_path.with_suffix(self.csv_path.suffix + ".tmp")
        with temporary_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=REPORT_FIELDS)
            writer.writeheader()
            writer.writerows(reports)
        temporary_path.replace(self.csv_path)

    def _write_header(self) -> None:
        with self.csv_path.open("w", newline="", encoding="utf-8") as file:
            csv.DictWriter(file, fieldnames=REPORT_FIELDS).writeheader()
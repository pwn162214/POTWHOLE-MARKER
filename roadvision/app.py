"""Tkinter user interface for RoadVision AI."""

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional

from PIL import Image, ImageTk, UnidentifiedImageError

from roadvision.storage import CREDIT_POINTS_PER_REPORT, CsvReportStore, ReportStorageError
from roadvision.verifier import ImageVerificationError, PotholeVerifier, VerificationResult


APP_TITLE = "RoadVision AI - Smart Pothole Verification and Reporting System"
APP_DIR = Path(__file__).resolve().parent.parent
REPORTS_FILE = APP_DIR / "data" / "reports.csv"
IMAGE_TYPES = [("Image files", "*.png *.jpg *.jpeg *.bmp *.webp"), ("All files", "*.*")]


class RoadVisionApp:
    """Build and manage the report form, verification flow, and report table."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.store = CsvReportStore(REPORTS_FILE)
        self.verifier = PotholeVerifier()
        self.image_path: Optional[Path] = None
        self.verified_path: Optional[Path] = None
        self.verification: Optional[VerificationResult] = None
        self.preview_image: Optional[ImageTk.PhotoImage] = None
        self.name_var = tk.StringVar()
        self.location_var = tk.StringVar()
        self.image_label_var = tk.StringVar(value="No image selected")
        self.status_var = tk.StringVar(value="Choose an image to begin verification.")
        self.reports: List[Dict[str, str]] = []

        self._configure_window()
        self._configure_style()
        self._build_interface()
        self._refresh_reports()

    def _configure_window(self) -> None:
        self.root.title(APP_TITLE)
        self.root.geometry("1320x850")
        self.root.minsize(1040, 700)
        self.root.configure(background="#f2f5f3")

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background="#f2f5f3")
        style.configure("Surface.TFrame", background="#ffffff")
        style.configure("TLabel", background="#f2f5f3", foreground="#20312d", font=("Segoe UI", 10))
        style.configure("Muted.TLabel", foreground="#65736e", font=("Segoe UI", 9))
        style.configure("Title.TLabel", font=("Segoe UI Semibold", 22), foreground="#14231f")
        style.configure("Section.TLabel", background="#ffffff", font=("Segoe UI Semibold", 12), foreground="#20312d")
        style.configure("Metric.TLabel", background="#ffffff", font=("Segoe UI Semibold", 22), foreground="#176b55")
        style.configure("MetricName.TLabel", background="#ffffff", foreground="#65736e", font=("Segoe UI", 9))
        style.configure("TEntry", padding=8, fieldbackground="#ffffff")
        style.configure("TButton", padding=(12, 8), font=("Segoe UI Semibold", 9))
        style.configure("Accent.TButton", background="#176b55", foreground="#ffffff")
        style.map("Accent.TButton", background=[("active", "#115641"), ("disabled", "#a8b7b1")])
        style.configure("Treeview", rowheight=34, background="#ffffff", fieldbackground="#ffffff", font=("Segoe UI", 9))
        style.configure("Treeview.Heading", background="#e8efeb", foreground="#344740", font=("Segoe UI Semibold", 9), padding=8)
        style.map("Treeview", background=[("selected", "#d5e9e0")], foreground=[("selected", "#14231f")])

    def _build_interface(self) -> None:
        shell = ttk.Frame(self.root, padding=(26, 20, 26, 22))
        shell.pack(fill="both", expand=True)

        header = ttk.Frame(shell)
        header.pack(fill="x", pady=(0, 18))
        ttk.Label(header, text="RoadVision AI", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Smart Pothole Verification and Reporting System",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(2, 0))

        self.metrics = {}
        metric_row = ttk.Frame(shell)
        metric_row.pack(fill="x", pady=(0, 18))
        for index, (key, title) in enumerate(
            (
                ("total", "TOTAL REPORTS"),
                ("verified", "VERIFIED REPORTS"),
                ("pending", "PENDING REPORTS"),
                ("credits", "CREDIT POINTS"),
            )
        ):
            metric_row.columnconfigure(index, weight=1, uniform="metrics")
            block = ttk.Frame(metric_row, style="Surface.TFrame", padding=(16, 11))
            block.grid(row=0, column=index, sticky="ew", padx=(0 if index == 0 else 8, 0 if index == 3 else 8))
            value = ttk.Label(block, text="0", style="Metric.TLabel")
            value.pack(anchor="w")
            ttk.Label(block, text=title, style="MetricName.TLabel").pack(anchor="w", pady=(1, 0))
            self.metrics[key] = value

        content = ttk.Frame(shell)
        content.pack(fill="both", expand=True)
        content.columnconfigure(0, weight=0, minsize=350)
        content.columnconfigure(1, weight=1)
        content.rowconfigure(0, weight=1)

        form = ttk.Frame(content, style="Surface.TFrame", padding=18)
        form.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self._build_form(form)

        table_panel = ttk.Frame(content, style="Surface.TFrame", padding=18)
        table_panel.grid(row=0, column=1, sticky="nsew")
        self._build_table(table_panel)

    def _build_form(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="New road report", style="Section.TLabel").pack(anchor="w")
        ttk.Label(parent, text="Details are saved only after AI verification.", style="Muted.TLabel").pack(anchor="w", pady=(4, 15))

        ttk.Label(parent, text="Citizen name").pack(anchor="w", pady=(0, 5))
        ttk.Entry(parent, textvariable=self.name_var).pack(fill="x", pady=(0, 12))

        ttk.Label(parent, text="Road / location").pack(anchor="w", pady=(0, 5))
        ttk.Entry(parent, textvariable=self.location_var).pack(fill="x", pady=(0, 12))

        ttk.Label(parent, text="Description").pack(anchor="w", pady=(0, 5))
        self.description_text = tk.Text(
            parent, height=4, wrap="word", relief="solid", borderwidth=1,
            font=("Segoe UI", 10), padx=8, pady=7, background="#ffffff", foreground="#20312d",
        )
        self.description_text.pack(fill="x", pady=(0, 12))

        ttk.Label(parent, text="Evidence image").pack(anchor="w", pady=(0, 5))
        image_row = ttk.Frame(parent, style="Surface.TFrame")
        image_row.pack(fill="x")
        ttk.Button(image_row, text="Browse...", command=self._choose_image).pack(side="left")
        ttk.Label(image_row, textvariable=self.image_label_var, style="Muted.TLabel").pack(side="left", padx=(9, 0))

        preview_wrap = ttk.Frame(parent, style="Surface.TFrame", height=116)
        preview_wrap.pack(fill="x", pady=(10, 10))
        preview_wrap.pack_propagate(False)
        self.preview_label = ttk.Label(preview_wrap, text="Image preview", style="Muted.TLabel", anchor="center")
        self.preview_label.pack(fill="both", expand=True)

        self.verify_button = ttk.Button(parent, text="Verify image with AI", command=self._verify_image, style="Accent.TButton")
        self.verify_button.pack(fill="x", pady=(0, 9))
        self.result_label = ttk.Label(parent, textvariable=self.status_var, style="Muted.TLabel", wraplength=300)
        self.result_label.pack(anchor="w", pady=(0, 14))

        self.submit_button = ttk.Button(parent, text="Submit verified report", command=self._submit_report, state="disabled")
        self.submit_button.pack(fill="x")

    def _build_table(self, parent: ttk.Frame) -> None:
        title_row = ttk.Frame(parent, style="Surface.TFrame")
        title_row.pack(fill="x", pady=(0, 13))
        ttk.Label(title_row, text="Submitted reports", style="Section.TLabel").pack(side="left")
        ttk.Label(title_row, text="Newest reports appear first", style="Muted.TLabel").pack(side="right")

        columns = ("name", "location", "description", "image_path", "verification", "status", "credits")
        self.report_table = ttk.Treeview(parent, columns=columns, show="headings", selectmode="browse")
        headings = {
            "name": ("Citizen", 110),
            "location": ("Location", 145),
            "description": ("Description", 210),
            "image_path": ("Image path", 190),
            "verification": ("AI result", 145),
            "status": ("Status", 105),
            "credits": ("Credits", 75),
        }
        for column, (heading, width) in headings.items():
            self.report_table.heading(column, text=heading)
            self.report_table.column(column, width=width, minwidth=80, anchor="w", stretch=column in ("location", "description"))

        vertical = ttk.Scrollbar(parent, orient="vertical", command=self.report_table.yview)
        horizontal = ttk.Scrollbar(parent, orient="horizontal", command=self.report_table.xview)
        self.report_table.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.report_table.pack(fill="both", expand=True, side="top")
        vertical.pack(fill="y", side="right", in_=self.report_table.master)
        horizontal.pack(fill="x", side="bottom", in_=self.report_table.master)

    def _choose_image(self) -> None:
        selected = filedialog.askopenfilename(title="Choose pothole image", filetypes=IMAGE_TYPES)
        if not selected:
            return
        path = Path(selected)
        try:
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                image.thumbnail((300, 110))
                self.preview_image = ImageTk.PhotoImage(image.copy())
        except (OSError, UnidentifiedImageError, ValueError) as error:
            messagebox.showerror("Invalid image", f"The selected file cannot be opened as an image.\n\n{error}", parent=self.root)
            return

        self.image_path = path
        self.verified_path = None
        self.verification = None
        self.image_label_var.set(path.name)
        self.preview_label.configure(image=self.preview_image, text="")
        self.status_var.set("Image selected. Run AI verification before submitting.")
        self.result_label.configure(foreground="#65736e")
        self.submit_button.configure(state="disabled")

    def _verify_image(self) -> None:
        if self.image_path is None:
            messagebox.showwarning("Image required", "Choose a pothole image before verification.", parent=self.root)
            return
        image_path = self.image_path
        self.verify_button.configure(state="disabled")
        self.submit_button.configure(state="disabled")
        self.status_var.set("Loading AI model and analyzing image. First run may take a few minutes...")
        self.result_label.configure(foreground="#65736e")
        threading.Thread(target=self._verification_worker, args=(image_path,), daemon=True).start()

    def _verification_worker(self, image_path: Path) -> None:
        try:
            result = self.verifier.verify(image_path)
            self.root.after(0, self._show_verification, image_path, result, None)
        except ImageVerificationError as error:
            self.root.after(0, self._show_verification, image_path, None, str(error))

    def _show_verification(
        self,
        image_path: Path,
        result: Optional[VerificationResult],
        error: Optional[str],
    ) -> None:
        self.verify_button.configure(state="normal")
        if error:
            self.verified_path = None
            self.verification = None
            self.status_var.set(error)
            self.result_label.configure(foreground="#a33a32")
            messagebox.showerror("Verification failed", error, parent=self.root)
            return
        if image_path != self.image_path or result is None:
            return

        self.verification = result
        self.verified_path = image_path if result.detected else None
        self.status_var.set(f"{result.display_text}  |  Model score: {result.confidence:.0%}")
        self.result_label.configure(foreground="#176b55" if result.detected else "#a33a32")
        self.submit_button.configure(state="normal" if result.detected else "disabled")

    def _submit_report(self) -> None:
        name = self.name_var.get().strip()
        location = self.location_var.get().strip()
        description = self.description_text.get("1.0", "end-1c").strip()
        if not name or not location or not description:
            messagebox.showwarning("Missing information", "Enter your name, road/location, and a short description.", parent=self.root)
            return
        if self.image_path is None:
            messagebox.showwarning("Image required", "Choose an image before submitting.", parent=self.root)
            return
        if self.verified_path != self.image_path or self.verification is None or not self.verification.detected:
            messagebox.showwarning("Verification required", "Only an image verified as a pothole can be submitted.", parent=self.root)
            return

        report = {
            "Citizen Name": name,
            "Location": location,
            "Description": description,
            "Image Path": str(self.image_path),
            "AI Verification Result": self.verification.display_text,
            "Report Status": "Pending",
        }
        try:
            self.store.append_report(report)
        except ReportStorageError as error:
            messagebox.showerror("Save failed", str(error), parent=self.root)
            return

        self._refresh_reports()
        messagebox.showinfo(
            "Report submitted",
            f"Your verified report is Pending. You earned {CREDIT_POINTS_PER_REPORT} credit points.",
            parent=self.root,
        )
        self._clear_form()

    def _refresh_reports(self) -> None:
        try:
            self.reports = self.store.load_reports()
        except ReportStorageError as error:
            messagebox.showerror("Reports unavailable", str(error), parent=self.root)
            self.reports = []
        for item in self.report_table.get_children():
            self.report_table.delete(item)
        for report in reversed(self.reports):
            self.report_table.insert(
                "", "end",
                values=(
                    report["Citizen Name"],
                    report["Location"],
                    report["Description"],
                    report["Image Path"],
                    report["AI Verification Result"],
                    report["Report Status"],
                    report["Credit Points"],
                ),
            )

        verified = sum(row["AI Verification Result"] == "Pothole Detected" for row in self.reports)
        pending = sum(row["Report Status"].strip().lower() == "pending" for row in self.reports)
        credits = sum(int(row["Credit Points"]) for row in self.reports)
        self.metrics["total"].configure(text=str(len(self.reports)))
        self.metrics["verified"].configure(text=str(verified))
        self.metrics["pending"].configure(text=str(pending))
        self.metrics["credits"].configure(text=str(credits))

    def _clear_form(self) -> None:
        self.name_var.set("")
        self.location_var.set("")
        self.description_text.delete("1.0", "end")
        self.image_path = None
        self.verified_path = None
        self.verification = None
        self.preview_image = None
        self.image_label_var.set("No image selected")
        self.preview_label.configure(image="", text="Image preview")
        self.status_var.set("Choose an image to begin verification.")
        self.result_label.configure(foreground="#65736e")
        self.submit_button.configure(state="disabled")


def main() -> None:
    """Start the desktop application."""
    root = tk.Tk()
    RoadVisionApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
"""Browser-based RoadVision AI reporting application."""

import hashlib
from io import BytesIO
import tempfile
import uuid
from pathlib import Path
from typing import Dict, List

import streamlit as st
from PIL import Image, UnidentifiedImageError

from roadvision.storage import CREDIT_POINTS_PER_REPORT, CsvReportStore, ReportStorageError
from roadvision.verifier import ImageVerificationError, PotholeVerifier, VerificationResult


APP_DIR = Path(__file__).resolve().parent
REPORTS_FILE = APP_DIR / "data" / "reports.csv"
IMAGES_DIR = APP_DIR / "data" / "images"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


@st.cache_resource
def get_verifier() -> PotholeVerifier:
    """Share the lazily loaded model across Streamlit reruns."""
    return PotholeVerifier()


def configure_page() -> None:
    """Set page metadata and a restrained RoadVision visual style."""
    st.set_page_config(page_title="RoadVision AI", page_icon="🛣️", layout="wide")
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Lobster&display=swap');
        :root {
            --roadvision-green: #176b55;
            --roadvision-ink: #20352e;
            --roadvision-muted: #65736e;
            --roadvision-border: #d5e1da;
            --roadvision-surface: #ffffff;
            --roadvision-total: #237d65;
            --roadvision-verified: #287c58;
            --roadvision-pending: #d59020;
            --roadvision-credit: #267b9c;
        }
        [data-testid="stAppViewContainer"] {
            background: #f1f6f2; color: var(--roadvision-ink);
            font-family: "Aptos", "Segoe UI", sans-serif;
        }
        [data-testid="stHeader"] { background: rgba(241, 246, 242, 0.94); }
        .block-container { max-width: 1440px; padding-top: 1.6rem; padding-bottom: 3rem; }
        [data-testid="stMarkdownContainer"] h1,
        [data-testid="stMarkdownContainer"] h2,
        [data-testid="stMarkdownContainer"] h3,
        [data-testid="stWidgetLabel"] {
            color: #20352e !important; -webkit-text-fill-color: #20352e !important;
        }
        [data-testid="stMarkdownContainer"] h1 {
            font-family: "Lobster", cursive !important; font-weight: 400 !important;
        }
        .rv-brand {
            background: #155542; border-left: 7px solid #e7a83e; border-radius: 10px;
            padding: 17px 26px 19px; margin: 0 0 24px;
            box-shadow: 0 8px 22px rgba(21, 85, 66, 0.18);
        }
        .rv-brand h1 {
            color: #ffffff !important; -webkit-text-fill-color: #ffffff !important;
            font-family: "Lobster", cursive !important; font-size: 2.6rem !important;
            font-weight: 400 !important; margin: 0 0 2px !important;
        }
        .rv-brand p {
            color: #d5ebe1 !important; -webkit-text-fill-color: #d5ebe1 !important;
            font-size: 0.98rem; margin: 0 !important;
        }
        [data-testid="stCaptionContainer"],
        [data-testid="stCaptionContainer"] p,
        [data-testid="stMetricLabel"] {
            color: #65736e !important; -webkit-text-fill-color: #65736e !important;
        }
        [data-testid="stMetric"] {
            background: var(--roadvision-surface); border: 1px solid var(--roadvision-border);
            border-top: 4px solid var(--roadvision-total); border-radius: 8px;
            padding: 16px 18px; box-shadow: 0 3px 10px rgba(25, 55, 43, 0.07);
        }
        [data-testid="stMetricLabel"] p { font-size: 0.82rem !important; font-weight: 600 !important; }
        [data-testid="stMetricValue"] { font-size: 2rem !important; }
        [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) [data-testid="stColumn"]:nth-child(2) [data-testid="stMetric"] {
            border-top-color: var(--roadvision-verified); background: #eaf5eb;
        }
        [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) [data-testid="stColumn"]:nth-child(3) [data-testid="stMetric"] {
            border-top-color: var(--roadvision-pending); background: #fff4df;
        }
        [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) [data-testid="stColumn"]:nth-child(4) [data-testid="stMetric"] {
            border-top-color: var(--roadvision-credit); background: #e9f4f8;
        }
        [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) [data-testid="stColumn"]:nth-child(1) [data-testid="stMetric"] {
            background: #e8f4ee;
        }
        [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) [data-testid="stColumn"]:nth-child(1) [data-testid="stMetricValue"] p {
            color: var(--roadvision-total) !important;
            -webkit-text-fill-color: var(--roadvision-total) !important;
        }
        [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) [data-testid="stColumn"]:nth-child(2) [data-testid="stMetricValue"] p {
            color: var(--roadvision-verified) !important;
            -webkit-text-fill-color: var(--roadvision-verified) !important;
        }
        [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) [data-testid="stColumn"]:nth-child(3) [data-testid="stMetricValue"] p {
            color: var(--roadvision-pending) !important;
            -webkit-text-fill-color: var(--roadvision-pending) !important;
        }
        [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) [data-testid="stColumn"]:nth-child(4) [data-testid="stMetricValue"] p {
            color: var(--roadvision-credit) !important;
            -webkit-text-fill-color: var(--roadvision-credit) !important;
        }
        [data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--roadvision-surface); border-color: var(--roadvision-border) !important;
            border-radius: 8px; box-shadow: 0 3px 12px rgba(25, 55, 43, 0.05);
        }
        [data-testid="stMarkdownContainer"] h3 { font-size: 1.25rem; }
        [data-testid="stTextInputRootElement"],
        [data-testid="stTextAreaRootElement"] {
            background: #ffffff !important; border: 1px solid #c7d7ce !important;
            border-radius: 6px !important;
        }
        [data-testid="stTextInputField"],
        [data-testid="stTextArea"] textarea {
            background: transparent !important; color: var(--roadvision-ink) !important;
            -webkit-text-fill-color: var(--roadvision-ink) !important;
        }
        [data-testid="stTextInputField"]::placeholder,
        [data-testid="stTextArea"] textarea::placeholder {
            color: #7c8b84 !important; -webkit-text-fill-color: #7c8b84 !important;
        }
        [data-testid="stFileUploaderDropzone"] {
            background: #f3f9f5 !important; border: 1px dashed #85a996 !important;
            border-radius: 7px !important;
        }
        [data-testid="stFileUploaderDropzone"] p,
        [data-testid="stFileUploaderDropzone"] span,
        [data-testid="stFileUploaderDropzone"] small {
            color: var(--roadvision-ink) !important; -webkit-text-fill-color: var(--roadvision-ink) !important;
        }
        [data-testid="stFileUploaderDropzone"] button {
            background: #ffffff !important; color: var(--roadvision-green) !important;
            border-color: #9bb8a7 !important;
        }
        div.stButton > button[kind="primary"] {
            background: var(--roadvision-green); border-color: var(--roadvision-green); color: white;
            min-height: 2.8rem; font-weight: 650;
            transition: background-color 140ms ease, transform 140ms ease;
        }
        div.stButton > button[kind="primary"]:hover {
            background: #115641; border-color: #115641; color: white;
            transform: translateY(-1px);
        }
        div.stButton > button[kind="secondary"] {
            min-height: 2.65rem; border-color: #cbd8d0;
            background: #ffffff !important; color: var(--roadvision-ink) !important;
        }
        [data-testid="stDataFrame"] {
            border: 1px solid #dce5df; border-radius: 6px; overflow: hidden;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def image_digest(image_bytes: bytes) -> str:
    """Identify the exact uploaded bytes that were verified."""
    return hashlib.sha256(image_bytes).hexdigest()


def validate_uploaded_image(image_bytes: bytes) -> None:
    """Reject malformed images before previewing or sending them to the model."""
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            image.verify()
    except (OSError, UnidentifiedImageError, ValueError) as error:
        raise ImageVerificationError("The uploaded file is not a valid, readable image.") from error


def verify_upload(image_bytes: bytes, filename: str) -> VerificationResult:
    """Write an upload to a temporary file for the shared verifier."""
    suffix = Path(filename).suffix.lower()
    if suffix not in IMAGE_EXTENSIONS:
        raise ImageVerificationError("Choose a JPG, PNG, WEBP, or BMP image.")

    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temporary_file:
            temporary_file.write(image_bytes)
            temporary_path = Path(temporary_file.name)
        return get_verifier().verify(temporary_path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def get_reports() -> List[Dict[str, str]]:
    """Load saved reports and show CSV errors without crashing the page."""
    try:
        return CsvReportStore(REPORTS_FILE).load_reports()
    except ReportStorageError as error:
        st.error(str(error))
        return []


def render_dashboard(reports: List[Dict[str, str]]) -> None:
    """Show the report totals above the intake and review areas."""
    verified = sum(row["AI Verification Result"] == "Pothole Detected" for row in reports)
    pending = sum(row["Report Status"].strip().lower() == "pending" for row in reports)
    credits = sum(int(row["Credit Points"]) for row in reports)
    total_col, verified_col, pending_col, credits_col = st.columns(4, gap="medium")
    total_col.metric("Total Reports", len(reports))
    verified_col.metric("Verified Reports", verified)
    pending_col.metric("Pending Reports", pending)
    credits_col.metric("Credit Points", credits)


def render_report_form() -> None:
    """Collect report details, verify the evidence, and save approved reports."""
    st.subheader("Submit a road report")
    st.caption("Reports are saved only after AI verification detects a pothole.")

    form_version = st.session_state.get("form_version", 0)
    uploader_version = st.session_state.get("uploader_version", 0)
    name = st.text_input("Citizen name", key=f"citizen_name_{form_version}")
    location = st.text_input("Road / location", key=f"location_{form_version}")
    description = st.text_area("Description", height=100, key=f"description_{form_version}")
    upload = st.file_uploader(
        "Evidence image",
        type=["jpg", "jpeg", "png", "webp", "bmp"],
        key=f"evidence_{uploader_version}",
    )

    current_digest = None
    image_bytes = None
    if upload is not None:
        image_bytes = upload.getvalue()
        current_digest = image_digest(image_bytes)
        if st.session_state.get("verified_image_digest") != current_digest:
            st.session_state.pop("verification_result", None)
            st.session_state.pop("verified_image_digest", None)
        try:
            validate_uploaded_image(image_bytes)
            st.image(image_bytes, caption=upload.name, width=420)
        except ImageVerificationError as error:
            st.error(str(error))
            image_bytes = None
            current_digest = None

    existing_verification = st.session_state.get("verification_result")
    can_submit = bool(
        existing_verification
        and existing_verification["detected"]
        and st.session_state.get("verified_image_digest") == current_digest
    )
    verify_clicked = st.button(
        "Verify image with AI", type="primary", disabled=image_bytes is None,
        use_container_width=True, key="verify_upload",
    )
    submit_clicked = st.button(
        "Submit verified report", disabled=not can_submit,
        use_container_width=True, key="submit_report",
    )

    if verify_clicked and image_bytes is not None and current_digest is not None:
        try:
            with st.spinner("Loading the AI model and analyzing the image..."):
                result = verify_upload(image_bytes, upload.name)
            st.session_state["verification_result"] = {
                "detected": result.detected,
                "confidence": result.confidence,
                "display_text": result.display_text,
            }
            st.session_state["verified_image_digest"] = current_digest
        except ImageVerificationError as error:
            st.error(str(error))

    verification = st.session_state.get("verification_result")
    if verification and st.session_state.get("verified_image_digest") == current_digest:
        result_label = verification["display_text"]
        score = verification["confidence"]
        if verification["detected"]:
            st.success(f"{result_label} · model score {score:.0%}")
        else:
            st.warning(f"{result_label} · model score {score:.0%}")

    if not submit_clicked:
        return

    if not name.strip() or not location.strip() or not description.strip():
        st.warning("Enter your name, road/location, and a short description.")
        return
    if image_bytes is None or upload is None or current_digest is None:
        st.warning("Upload a valid image before submitting.")
        return
    if (
        not verification
        or st.session_state.get("verified_image_digest") != current_digest
        or not verification["detected"]
    ):
        st.warning("Verify this image and get Pothole Detected before submitting.")
        return

    suffix = Path(upload.name).suffix.lower()
    if suffix not in IMAGE_EXTENSIONS:
        st.error("Unsupported image extension.")
        return
    saved_image = IMAGES_DIR / f"{uuid.uuid4().hex}{suffix}"
    report = {
        "Citizen Name": name.strip(),
        "Location": location.strip(),
        "Description": description.strip(),
        "Image Path": str(saved_image),
        "AI Verification Result": verification["display_text"],
        "Report Status": "Pending",
        "Credit Points": str(CREDIT_POINTS_PER_REPORT),
    }
    try:
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        saved_image.write_bytes(image_bytes)
        CsvReportStore(REPORTS_FILE).append_report(report)
    except (OSError, ReportStorageError) as error:
        saved_image.unlink(missing_ok=True)
        st.error(f"Could not save the report: {error}")
        return

    st.session_state["form_version"] = form_version + 1
    st.session_state["uploader_version"] = uploader_version + 1
    st.session_state.pop("verification_result", None)
    st.session_state.pop("verified_image_digest", None)
    st.success(f"Verified report saved as Pending. You earned {CREDIT_POINTS_PER_REPORT} credit points.")
    st.rerun()


def render_reports_table(reports: List[Dict[str, str]]) -> None:
    """Show all submitted report fields in a browser data table."""
    st.subheader("Submitted reports")
    if not reports:
        st.info("No reports have been submitted yet.")
        return

    table_rows = [
        {
            "Citizen Name": row["Citizen Name"],
            "Location": row["Location"],
            "Description": row["Description"],
            "Image Path": row["Image Path"],
            "AI Verification Result": row["AI Verification Result"],
            "Report Status": row["Report Status"],
            "Credit Points": row["Credit Points"],
        }
        for row in reversed(reports)
    ]
    st.dataframe(table_rows, hide_index=True, use_container_width=True)


def main() -> None:
    """Render the browser-based RoadVision application."""
    configure_page()
    st.markdown(
        """
        <header class="rv-brand">
            <h1>RoadVision AI</h1>
            <p>Smart pothole verification and reporting system</p>
        </header>
        """,
        unsafe_allow_html=True,
    )

    reports = get_reports()
    render_dashboard(reports)
    st.divider()
    form_col, reports_col = st.columns([0.85, 1.5], gap="large")
    with form_col:
        with st.container(border=True):
            render_report_form()
    with reports_col:
        with st.container(border=True):
            render_reports_table(reports)


if __name__ == "__main__":
    main()
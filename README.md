# RoadVision AI

**Smart Pothole Verification and Reporting System** provides both a Tkinter desktop app and a Streamlit browser app for collecting road damage reports and checking evidence images with a zero-shot AI classifier before saving reports.

## Features

- Tkinter report form for citizen name, location, description, and image evidence.
- CLIP zero-shot image classification with the results **Pothole Detected** or **No Pothole Detected**.
- Submission is enabled only when the selected image is classified as a pothole; changing the image requires a fresh verification.
- Local CSV persistence at `data/reports.csv` with all requested report fields.
- Citizens earn 10 credit points for each AI-verified report; points are stored per report and totaled on the dashboard.
- Dashboard counts for total reports, AI-verified reports, and reports pending authority action.
- Submitted reports appear in a scrollable Tkinter `Treeview` table (newest first).
- Browser-based version with the same verification workflow, dashboard, and CSV-backed reports table.

## Requirements

- Python 3.10 or newer.
- Tkinter, included with most Windows Python installations. If your Python installation omitted Tcl/Tk, rerun the Python installer and add **tcl/tk and IDLE**.
- Internet access for the first AI model download. The model is cached locally for later runs. The initial download and PyTorch installation can be several hundred megabytes.

## Install and run

From the project directory in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python run.py
```

On macOS or Linux, activate the environment with `source .venv/bin/activate`, then use the same `pip install` and `python run.py` commands. On CPU-only Windows machines, if PyTorch installation fails, install its CPU wheel first with `pip install torch --index-url https://download.pytorch.org/whl/cpu`, then install the remaining packages from `requirements.txt`.

On the first verification, the Hugging Face model `openai/clip-vit-base-patch32` is downloaded automatically. To use another compatible model, set the `ROADVISION_MODEL` environment variable before launching. The report CSV is created automatically in the project's `data` folder.

If Windows reports that Application Control blocked `torch_python.dll` (for example, `WinError 4551`), PyTorch is being blocked by a device security policy. Do not disable that policy. Ask the device administrator to approve the dependency, or run/deploy the app on a machine where PyTorch is permitted.

## Run as a website

Install the requirements as above, then start the local web app:

```powershell
streamlit run streamlit_app.py
```

Streamlit prints a local URL (usually `http://localhost:8501`) to open in your browser. On first verification, the CLIP model downloads; keep an internet connection and allow time for the large model download.

To publish a demo, push the project to a GitHub repository and create a Streamlit Community Cloud app using `streamlit_app.py` as its entry point. The hosting environment needs enough memory for PyTorch and the CLIP model. The included CSV and uploaded images are local files; ephemeral hosts may discard them on restart, so use persistent storage or a database for a public or multi-user deployment.

## Using the desktop application

1. Enter the citizen name, road/location, and a short description.
2. Browse for a clear image of the suspected road damage.
3. Select **Verify image with AI** and wait for the result. First-time model setup needs internet access.
4. Submit only when the result says **Pothole Detected**. The new report is recorded as **Pending** until authority action is taken.

The verifier uses zero-shot CLIP scores and a conservative threshold; it is a hackathon prototype, not a substitute for a trained, locally validated road-inspection model or human review. Image classification can produce false positives and false negatives. The demo currently stores reports locally and does not transmit complaints to a government agency.

## Project structure

```text
roadvision-ai/
|-- data/                 # Created at runtime; reports.csv is stored here
|-- roadvision/
|   |-- __init__.py
|   |-- app.py             # Tkinter interface and report workflow
|   |-- storage.py         # CSV persistence and error handling
|   `-- verifier.py        # CLIP image verification
|-- README.md
|-- requirements.txt
|-- streamlit_app.py      # Browser-based interface
`-- run.py                 # Application entry point
```

## Future scope

- **GPS Integration:** Attach device coordinates to each verified report.
- **Government Dashboard:** Provide an authenticated portal for municipal staff to review and update report status.
- **Google Maps Integration:** Display reports by location and identify repair clusters.
- **Real-time Complaint Tracking:** Notify citizens as reports move from pending to assigned, in progress, and resolved.
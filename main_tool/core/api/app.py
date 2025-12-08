"""
Defined all api endpoints in 1 file, could be split further into different routes.
"""
import os
import io
from contextlib import asynccontextmanager
import tempfile
import shutil
import zipfile
import json
from pathlib import Path
import pandas as pd
from fastapi import (
    FastAPI,
    File,
    UploadFile,
    Depends,
)
from fastapi.responses import StreamingResponse
from fastapi import Form
from main_tool.core.evaluator.runner import EvaluationRunner
from main_tool.core.database.db_test import User, create_db_and_tables
from main_tool.core.api.schemas import UserCreate, UserRead, UserUpdate
from main_tool.core.api.users import auth_backend, current_active_user, fastapi_users
from main_tool.core.api.config_api import router as config_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # replace with a migration system like Alembic later
    await create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

# Include default fastapi users routers to handle account management

app.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"]
)

app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)

app.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)

app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

app.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)

# Custom config router we made

app.include_router(
    config_router,
    prefix="",
    tags=["config"],
                   )

# To test authentification, you can remove it
@app.get("/authenticated-route")
async def authenticated_route(user: User = Depends(current_active_user)):
    """
    Acts like a a heart beat route
    """
    return {"message": f"Hello {user.email}!"}


@app.post("/evaluate/")
async def evaluate(
    config: str = Form(...),
    ground_truth: UploadFile = File(..., description="Ground truth Excel or CSV or txt file"),
    predictions: UploadFile = File(...,
                                    description="Archive of JSON prediction files (.zip or .tar)")
) -> StreamingResponse:
    """
    Evaluate submitted predictions against ground truth using the user's
    configuration provided from front and return a detailed multi-sheet Excel report.

    Args:
        config (str, required via form): Configuration data as JSON string (provided by frontend).
        ground_truth (UploadFile, required): Uploaded Excel / csv / txt
        file containing ground truth data.
        predictions (UploadFile, required): Uploaded ZIP archive containing a
        folder of prediction JSON files.

    Security:
        - Zip extraction is performed with path traversal protection.
        - All file operations occur in an isolated temporary directory,
        which is cleaned up after use.

    Notes:
        - This endpoint expects the predictions archive to contain at least one subfolder,
          which will be used as the directory containing JSON output files.
        - The Excel report includes the sheets: 'details', 'field_summary', 'file_scores'.

    Raises:
        ValueError: If no subfolder is found in the extracted predictions archive, or if any other
        validation errors occur during file processing.
    """

    def safe_extract(zip_file, path):
        """
        Safely extract a zip archive, preventing path traversal attacks.
        """
        for member in zip_file.namelist():
            # Check for path traversal attempt
            member_path = os.path.join(path, member)
            abs_member_path = os.path.abspath(member_path)
            abs_target_dir = os.path.abspath(path)
            if not abs_member_path.startswith(abs_target_dir):
                raise Exception("Attempted Path Traversal in Zip File")
        zip_file.extractall(path)

    config = json.loads(config)

    # Create a temporary directory for input/output file handling.
    with tempfile.TemporaryDirectory() as temp_dir:
        # Save the uploaded predictions ZIP.
        predictions_zip_path = f"{temp_dir}/predictions_repo.zip"
        with open(predictions_zip_path, "wb") as buffer:
            shutil.copyfileobj(predictions.file, buffer)

        # Extract predictions, while protecting against path traversal.
        outputs_dir = f"{temp_dir}/outputs"
        with zipfile.ZipFile(predictions_zip_path, 'r') as zip_ref:
            safe_extract(zip_ref, outputs_dir)

        # Find the subfolder containing JSON prediction files.
        outputs_dir_path = Path(outputs_dir)
        subdirs = [f for f in outputs_dir_path.iterdir() if f.is_dir()]
        if not subdirs:
            raise ValueError("No subfolders found in the predictions archive.")
        json_folder = subdirs[0]  # Use the first subdirectory found

        # Determine the file extension and save the ground truth file accordingly
        gt_filename = ground_truth.filename
        gt_ext = os.path.splitext(gt_filename)[1].lower()
        if gt_ext not in [".xlsx", ".csv", ".txt"]:
            raise ValueError("Ground truth file must be .xlsx or .csv or .txt")

        # Save the uploaded ground truth Excel file.
        gt_path = f"{temp_dir}/gt{gt_ext}"
        with open(gt_path, "wb") as buffer:
            shutil.copyfileobj(ground_truth.file, buffer)

        # Run evaluation logic
        runner = EvaluationRunner(config)
        result = runner.run(str(json_folder), gt_path)

        # Compile results into a multi-sheet Excel workbook.
        df_list = [result["details"], result["field_summary"], result["file_scores"]]
        sheet_names = ["details", "field_summary", "file_scores"]
        result_xlsx_path = f"{temp_dir}/result.xlsx"
        with pd.ExcelWriter(result_xlsx_path, engine='xlsxwriter') as writer:
            for df, sheet in zip(df_list, sheet_names):
                df.to_excel(writer, sheet_name=sheet, index=False)
                worksheet = writer.sheets[sheet]
                # Set column widths
                for col_num in range(0, 2):
                    worksheet.set_column(col_num, col_num, 50)
                for col_num in range(2, 4):
                    worksheet.set_column(col_num, col_num, 40)
                for col_num in range(4, 6):
                    worksheet.set_column(col_num, col_num, 20)
                worksheet.set_column(6, 6, 40)

        # Return the Excel file as a streaming response for download.
        with open(result_xlsx_path, "rb") as result_file:
            result_bytes = result_file.read()

        return StreamingResponse(
            io.BytesIO(result_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=result.xlsx"}
        )

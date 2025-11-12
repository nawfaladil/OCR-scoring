"""
Defined all api endpoints in 1 file, could be split further into different routes.
"""
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
    # replace with a migration system like Alembic
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

# custom config router we made

app.include_router(
    config_router,
    prefix="",
    tags=["config"],
                   )

@app.get("/authenticated-route")
async def authenticated_route(user: User = Depends(current_active_user)):
    return {"message": f"Hello {user.email}!"}


@app.post("/evaluate/")
async def evaluate(
    config: str = Form(...),
    ground_truth: UploadFile = File(..., description="Ground truth CSV file"),
    predictions: UploadFile = File(...,
                                    description="Archive of JSON prediction files (.zip or .tar)")
):

    config = json.loads(config)

    with tempfile.TemporaryDirectory() as temp_dir:
        # Save the predictions zip file
        predictions_zip_path = f"{temp_dir}/predictions_repo.zip"
        with open(predictions_zip_path, "wb") as buffer:
            shutil.copyfileobj(predictions.file, buffer)

        # Extract JSONs from the zip
        outputs_dir = f"{temp_dir}/outputs"
        with zipfile.ZipFile(predictions_zip_path, 'r') as zip_ref:
            zip_ref.extractall(outputs_dir)


        # Find the subfolder (the first directory in outputs_dir)
        outputs_dir_path = Path(outputs_dir)
        subdirs = [f for f in outputs_dir_path.iterdir() if f.is_dir()]
        if not subdirs:
            raise ValueError("No subfolders found in the predictions archive.")
        json_folder = subdirs[0]  # Use the first subdirectory found

        # Save the ground truth CSV
        gt_path = f"{temp_dir}/gt.xlsx"
        with open(gt_path, "wb") as buffer:
            shutil.copyfileobj(ground_truth.file, buffer)

        # Run your tool
        runner = EvaluationRunner(config)
        result = runner.run(str(json_folder), gt_path)

        # Create Excel result
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

        # Return the Excel file as a stream
        with open(result_xlsx_path, "rb") as result_file:
            result_bytes = result_file.read()

        return StreamingResponse(
            io.BytesIO(result_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=result.xlsx"}
        )

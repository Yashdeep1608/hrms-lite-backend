import json
from typing import Optional
from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.params import Form
from app.core.dependencies import get_current_user
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from app.helpers.background import process_import_job
from app.helpers.response import ResponseHandler
from app.db.session import get_db
from app.helpers.s3 import upload_file_to_s3
from app.helpers.translator import Translator
from app.helpers.utils import get_lang_from_request
from app.schemas.importjob import *
from app.crud import importjob as crud_import_job
from fastapi import BackgroundTasks
router = APIRouter(
    prefix="/api/admin/v1/import",
    tags=["Import"],
    dependencies=[Depends(get_current_user)]
)
translator = Translator()

# 👉 Import File
@router.post("/create")
def create_import_job(import_job_in: str = Form(...),file: UploadFile = File(...),background_tasks: BackgroundTasks = None, request: Request = None, db: Session = Depends(get_db),current_user=Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        # Validate file type
        allowed_types = {
            "text/csv",
            "application/vnd.ms-excel",  # .xls
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
        }
        import_job_data = ImportJobBaseSchema(**json.loads(import_job_in))

        if file.content_type not in allowed_types:
            return ResponseHandler.validation_error(
                message=translator.t("invalid_file_type", lang)
            )

        file_url = upload_file_to_s3(
            file,
            folder=f"imports/{import_job_data.entity_type}"
        )

        job = crud_import_job.create_import_job(
            db=db,
            import_job=import_job_data,
            current_user=current_user,
            file_path=file_url
        )
        # Start background job
        background_tasks.add_task(
            process_import_job,
            job.id
        )
        
        return ResponseHandler.success(message=translator.t("import_process_started", lang), data=job.id)
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )
    
@router.get("/{import_job_id}")
def get_import_job(import_job_id: str, request: Request, db: Session = Depends  (get_db),current_user=Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        import_job = crud_import_job.get_import_job_by_id(db, import_job_id, current_user.business_id)
        if not import_job:
            return ResponseHandler.not_found(message=translator.t("import_job_not_found", lang))
        return ResponseHandler.success(data=jsonable_encoder(import_job))
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )
    
@router.get("/list/all")
def list_import_jobs(request: Request, db: Session = Depends(get_db),current_user=Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        import_jobs = crud_import_job.get_import_jobs_by_business(db, current_user.business_id)
        return ResponseHandler.success(data=jsonable_encoder(import_jobs))
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )




from requests import Session
from app.models.importjob import ImportJob
from app.models.user import User
from app.schemas.importjob import ImportJobBaseSchema


def create_import_job(db:Session, import_job:ImportJobBaseSchema, file_path:str,current_user:User):
    import_job = ImportJob(
        business_id=current_user.business_id,
        entity_type=import_job.entity_type,
        import_type=import_job.import_type,
        unique_field=import_job.unique_field or None,
        assign_group_ids=import_job.assign_group_ids or None,
        assign_tag_ids=import_job.assign_tag_ids or None,
        file_path=file_path,
        status="pending",
        total_rows=0,
        processed_rows=0,
        success_rows=0,
        failed_rows=0,
        error_file_path=None,
        created_by=current_user.id
    )
    db.add(import_job)
    db.commit()
    db.refresh(import_job)
    return import_job

def get_import_job_by_id(db:Session, import_job_id:str, business_id:int):
    return db.query(ImportJob).filter(ImportJob.id == import_job_id, ImportJob.business_id == business_id).first()

def get_import_jobs_by_business(db:Session, business_id:int):
    return db.query(ImportJob).filter(ImportJob.business_id == business_id).order_by(ImportJob.created_at.desc()).all()
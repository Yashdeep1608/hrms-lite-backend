from fastapi import APIRouter, Depends, Request, File, UploadFile
from psycopg2 import IntegrityError
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user
from app.helpers.response import ResponseHandler
from app.helpers.s3 import upload_file_to_s3
from app.helpers.utils import get_lang_from_request
from app.models import User
from app.db.session import get_db
from app.helpers.translator import Translator
from app.crud import user as crud_user
from fastapi.encoders import jsonable_encoder

from app.models.employee import Attendance, Employee
from app.schemas.employee import AttendanceCreate, EmployeeCreate

translator = Translator()

router = APIRouter(
    prefix="/api/admin/v1/hrms",
    tags=["User"],
    dependencies=[Depends(get_current_user)]
)
@router.post("/employees")
def create_employee(
    request: Request,
    data: EmployeeCreate,
    db: Session = Depends(get_db),
):
    lang = get_lang_from_request(request)

    try:
        employee = Employee(**data.model_dump())
        db.add(employee)
        db.commit()
        db.refresh(employee)

        return ResponseHandler.success(
            data=jsonable_encoder(employee),
            message="employee_created"
        )

    except IntegrityError:
        db.rollback()
        return ResponseHandler.bad_request(
            message="employee_exists"
        )

    except Exception as e:
        db.rollback()
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )
@router.get("/employees")
def list_employees(
    request: Request,
    db: Session = Depends(get_db),
):
    lang = get_lang_from_request(request)

    try:
        employees = db.query(Employee).all()

        return ResponseHandler.success(
            data=jsonable_encoder(employees)
        )

    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.delete("/employees/{employee_id}")
def delete_employee(
    request: Request,
    employee_id: int,
    db: Session = Depends(get_db),
):
    lang = get_lang_from_request(request)

    try:
        employee = db.query(Employee).filter(
            Employee.id == employee_id
        ).first()

        if not employee:
            return ResponseHandler.not_found(
                message="employee_not_found"
            )

        db.delete(employee)
        db.commit()

        return ResponseHandler.success(
            message="employee_deleted"
        )

    except Exception as e:
        db.rollback()
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.post("/attendance")
def mark_attendance(
    request: Request,
    data: AttendanceCreate,
    db: Session = Depends(get_db),
):
    lang = get_lang_from_request(request)

    try:
        employee = db.query(Employee).filter(
            Employee.id == data.employee_id
        ).first()

        if not employee:
            return ResponseHandler.not_found(
                message="employee_not_found"
            )

        attendance = Attendance(**data.model_dump())
        db.add(attendance)
        db.commit()
        db.refresh(attendance)

        return ResponseHandler.success(
            data=jsonable_encoder(attendance),
            message="attendance_marked"
        )

    except IntegrityError:
        db.rollback()
        return ResponseHandler.bad_request(
            message="attendance_already_marked"
        )

    except Exception as e:
        db.rollback()
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.get("/attendance/{employee_id}")
def get_attendance(
    request: Request,
    employee_id: int,
    db: Session = Depends(get_db),
):
    lang = get_lang_from_request(request)

    try:
        employee = db.query(Employee).filter(
            Employee.id == employee_id
        ).first()

        if not employee:
            return ResponseHandler.not_found(
                message="employee_not_found"
            )

        attendance = db.query(Attendance).filter(
            Attendance.employee_id == employee_id
        ).order_by(Attendance.date.desc()).all()

        return ResponseHandler.success(
            data=jsonable_encoder(attendance)
        )

    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

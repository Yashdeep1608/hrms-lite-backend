import codecs
from datetime import timezone
import uuid

from sqlalchemy import func
from app.db.session import SessionLocal
from app.models.contact import Lead
from app.models.importjob import ImportJob
import csv
import requests
from io import StringIO
from sqlalchemy.orm import Session

BATCH_SIZE = 500

def process_import_job(import_job_id: int):
    db = SessionLocal()
    try:
        job = db.query(ImportJob).filter(ImportJob.id == import_job_id).first()
        if not job:
            return

        job.status = "processing"
        db.commit()

        if job.entity_type == "lead":
            process_lead_import(db, job)
        else:
            job.status = "failed"
            job.error_message = "Entity not supported yet"
            db.commit()

    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        db.commit()

    finally:
        db.close()

from sqlalchemy.orm import Session
from sqlalchemy import func
import requests, csv, codecs, uuid

BATCH_SIZE = 500


def process_lead_import(db: Session, job: ImportJob):
    try:
        job.status = "processing"
        db.commit()

        # ----------------------------
        # Helpers
        # ----------------------------
        def norm_email(v):
            if not v:
                return None
            return v.strip().lower()

        def norm_phone(v):
            if not v:
                return None
            v = str(v).strip()
            if "E+" in v:
                try:
                    v = str(int(float(v)))
                except:
                    pass
            return v

        # ----------------------------
        # Download CSV
        # ----------------------------
        response = requests.get(job.file_path, stream=True)
        response.raise_for_status()

        reader = csv.DictReader(
            codecs.iterdecode(response.iter_lines(), "utf-8")
        )

        rows = list(reader)

        total = 0
        success = 0
        failed = 0
        skipped = 0
        duplicate = 0
        invalid = 0

        to_create = []
        to_update = []

        # ----------------------------
        # Load existing leads
        # ----------------------------
        existing = db.query(
            Lead.id,
            Lead.email,
            Lead.phone_number
        ).filter(
            Lead.business_id == job.business_id
        ).all()

        existing_email_map = {
            (e.email or "").lower(): e.id
            for e in existing if e.email
        }

        existing_phone_map = {
            e.phone_number: e.id
            for e in existing if e.phone_number
        }

        # ----------------------------
        # In-file duplicate tracking
        # ----------------------------
        seen_identifiers = set()

        # ----------------------------
        # Main Loop
        # ----------------------------
        for row in rows:
            total += 1

            try:
                phone = norm_phone(row.get("phone_number"))
                email = norm_email(row.get("email"))

                # Invalid if both missing
                if not phone and not email:
                    invalid += 1
                    continue

                # Unique field selection
                identifier = email if job.unique_field == "email" else phone

                # Missing unique field → skipped
                if not identifier:
                    skipped += 1
                    continue

                # Duplicate inside file
                if identifier in seen_identifiers:
                    duplicate += 1
                    continue
                seen_identifiers.add(identifier)

                # Existing detection (strict CRM mode)
                existing_id = None

                if email and email in existing_email_map:
                    existing_id = existing_email_map[email]
                elif phone and phone in existing_phone_map:
                    existing_id = existing_phone_map[phone]

                # ----------------------------
                # Decision Engine
                # ----------------------------
                if job.import_type == "create":
                    if existing_id:
                        skipped += 1
                        continue

                    to_create.append({
                        "id": uuid.uuid4(),
                        "business_id": job.business_id,
                        "phone_number": phone,
                        "email": email,
                        "first_name": row.get("first_name"),
                        "last_name": row.get("last_name"),
                        "source": "import",
                        "status": "imported",
                    })
                    success += 1

                elif job.import_type == "update":
                    if not existing_id:
                        skipped += 1
                        continue

                    to_update.append({
                        "id": existing_id,
                        "phone_number": phone,
                        "email": email,
                        "first_name": row.get("first_name"),
                        "last_name": row.get("last_name"),
                    })
                    success += 1

                elif job.import_type == "upsert":
                    if existing_id:
                        to_update.append({
                            "id": existing_id,
                            "phone_number": phone,
                            "email": email,
                            "first_name": row.get("first_name"),
                            "last_name": row.get("last_name"),
                        })
                    else:
                        to_create.append({
                            "id": uuid.uuid4(),
                            "business_id": job.business_id,
                            "phone_number": phone,
                            "email": email,
                            "first_name": row.get("first_name"),
                            "last_name": row.get("last_name"),
                            "source": "import",
                            "status": "imported",
                        })
                    success += 1

            except Exception:
                failed += 1

            # ----------------------------
            # Batch Writes
            # ----------------------------
            if len(to_create) >= BATCH_SIZE:
                db.bulk_insert_mappings(Lead, to_create)
                db.commit()
                to_create.clear()

            if len(to_update) >= BATCH_SIZE:
                db.bulk_update_mappings(Lead, to_update)
                db.commit()
                to_update.clear()

            # Progress Save
            if total % 200 == 0:
                job.processed_rows = total
                job.success_rows = success
                job.failed_rows = failed
                job.skipped_rows = skipped
                job.duplicate_rows = duplicate
                job.invalid_rows = invalid
                db.commit()

        # ----------------------------
        # Final Flush
        # ----------------------------
        if to_create:
            db.bulk_insert_mappings(Lead, to_create)
            db.commit()

        if to_update:
            db.bulk_update_mappings(Lead, to_update)
            db.commit()

        # ----------------------------
        # Final Counters
        # ----------------------------
        job.total_rows = total
        job.processed_rows = total
        job.success_rows = success
        job.failed_rows = failed
        job.skipped_rows = skipped
        job.duplicate_rows = duplicate
        job.invalid_rows = invalid

        job.meta = {
            "summary": {
                "created_or_updated": success,
                "skipped": skipped,
                "duplicate_in_file": duplicate,
                "invalid_rows": invalid
            }
        }

        job.status = "completed"
        db.commit()

    except Exception as e:
        job.status = "failed"
        job.meta = {"error": str(e)}
        db.commit()

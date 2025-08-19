from fastapi import APIRouter, Depends, HTTPException,Request
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user
from app.helpers.response import ResponseHandler
from app.helpers.translator import Translator
from app.helpers.utils import get_lang_from_request
from app.models.user import User
from app.schemas.contact import *
from app.crud import contact as crud_contact
from app.db.session import get_db
from uuid import UUID
from fastapi.encoders import jsonable_encoder # type: ignore


translator = Translator()
router = APIRouter(
    prefix="/api/admin/v1/contact",
    tags=["Contact"],
    dependencies=[Depends(get_current_user)]
)

# Contact APIs
@router.post("/create-contact")
def create_contact(payload:ContactCreate,request:Request,db:Session = Depends(get_db),current_user: User = Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        contact = crud_contact.create_contact(db,current_user.id,current_user.business_id,payload)
        return ResponseHandler.success(
            message=translator.t("contact_created",lang),
            data=str(contact.id)
        )
    except ValueError as ve:
        return ResponseHandler.bad_request(
            message=str(ve),  # Or translator.t("contact_already_exists", lang)
        )
    except Exception as e:
        return ResponseHandler.internal_error(message=translator.t("something_went_wrong", lang), error=str(e))
    
@router.put("/update-contact/{business_contact_id}")
def update_contact(business_contact_id:UUID,payload:ContactUpdate,request:Request,db:Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        contact = crud_contact.update_business_contact(db,business_contact_id,payload)
        return ResponseHandler.success(
            message=translator.t("contact_updated",lang),
            data=str(contact.id)
        )
    except Exception as e:
        return ResponseHandler.internal_error(message=translator.t("something_went_wrong", lang), error=str(e))
    
@router.delete("/delete-contact/{business_contact_id}",response_model = dict)
def delete_contact(business_contact_id:UUID,request:Request,db:Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        contact = crud_contact.delete_business_contact(db,business_contact_id)
        return ResponseHandler.success(
            message=translator.t("contact_deleted",lang),
            data=str(contact.id)
        )
    except Exception as e:
        return ResponseHandler.internal_error(message=translator.t("something_went_wrong", lang), error=str(e))

@router.get("/get-contact-details/{business_contact_id}",response_model = dict)
def get_contact_details(business_contact_id:UUID,request:Request,db:Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        contact = crud_contact.get_contact_by_business_contact_id(db,business_contact_id)
        return ResponseHandler.success(
            message=translator.t("contact_fetched",lang),
            data=jsonable_encoder(contact)
        )
    except Exception as e:
        return ResponseHandler.internal_error(message=translator.t("something_went_wrong", lang), error=str(e))
    
@router.get("/get-contact-dropdown",response_model = dict)
def get_contact_dropdown(request:Request,search: str = None,page: int = 1,page_size: int = 20,db:Session = Depends(get_db),current_user: User = Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        contacts = crud_contact.get_contacts_for_dropdown(db,current_user,current_user.business_id,search,page,page_size)
        return ResponseHandler.success(
            message=translator.t("contacts_fetched",lang),
            data=jsonable_encoder(contacts)
        )
    except Exception as e:
        return ResponseHandler.internal_error(message=translator.t("something_went_wrong", lang), error=str(e))
    
@router.post("/get-all-contacts",response_model = dict)
def get_all_contact(payload:ContactFilterRequest,request:Request,db:Session = Depends(get_db),current_user: User = Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        contacts = crud_contact.get_all_contacts(
            db,
            current_user,
            current_user.business_id,
            page_number=payload.page_number,
            page_size=payload.page_size,
            search=payload.search,
            sort_by=payload.sort_by,
            sort_dir=payload.sort_dir,
            group_id=payload.group_id,
            filters=payload.filters
        )
        return ResponseHandler.success(
            message=translator.t("contacts_fetched",lang),
            data=jsonable_encoder(contacts)
        )
    except Exception as e:
        return ResponseHandler.internal_error(message=translator.t("something_went_wrong", lang), error=str(e))

@router.post("/get-all-contacts-count",response_model = dict)
def get_all_contact_count(payload:ContactFilterRequest,request:Request,db:Session = Depends(get_db),current_user: User = Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        total = crud_contact.get_all_contacts_count(
            db,
            current_user,
            current_user.business_id,
            search=payload.search,
            group_id=payload.group_id,
            filters=payload.filters
        )
        return ResponseHandler.success(
            message=translator.t("contacts_fetched",lang),
            data=total
        )
    except Exception as e:
        return ResponseHandler.internal_error(message=translator.t("something_went_wrong", lang), error=str(e))

@router.post("/assign-groups", response_model=dict)
def assign_contacts_groups(
    payload: AssignContactsGroupsRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    lang = get_lang_from_request(request)
    try:
        crud_contact.assign_contacts_to_groups(
            db=db,
            contact_ids=payload.contact_ids,
            group_ids=payload.group_ids,
            assigned_by=payload.assigned_by
        )
        return ResponseHandler.success(
            message=translator.t("contacts_assigned_to_groups", lang),
            data={}
        )
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.post("/assign-tags", response_model=dict)
def assign_contacts_tags(
    payload: AssignContactsTagsRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    lang = get_lang_from_request(request)
    try:
        crud_contact.assign_contacts_to_tags(
            db=db,
            contact_ids=payload.contact_ids,
            tag_ids=payload.tag_ids,
            assigned_by=payload.assigned_by
        )
        return ResponseHandler.success(
            message=translator.t("contacts_assigned_to_tags", lang),
            data={}
        )
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.get("/get-contact-groups/{contact_id}", response_model=list)
def get_contact_groups(contact_id: UUID,request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        groups = crud_contact.get_contact_groups(db,contact_id)
        return ResponseHandler.success(message=translator.t("contact_groups_retrieved", lang), data=groups)
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.get("/get-contact-tags/{contact_id}", response_model=list)
def get_contact_tags(contact_id: UUID,request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        tags = crud_contact.get_contact_tags(db,contact_id)
        return ResponseHandler.success(message=translator.t("contact_tags_retrieved", lang), data=tags)
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )


# Create Custom Field
@router.post("/custom-field/create-field/{business_id}", response_model=dict)
def create_field(business_id: int, field: CustomFieldCreate, request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        data = crud_contact.create_custom_field(db, business_id, field)
        return ResponseHandler.success(
            message=translator.t("custom_field_created", lang),
            data={"id": str(data.id)}
        )
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.get("/custom-field/get-fields/{business_id}", response_model=dict)
def list_fields(business_id: int, request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        data = crud_contact.get_fields(db, business_id)
        return ResponseHandler.success(
            message=translator.t("custom_fields_fetched", lang),
            data=[{
                "id": str(field.id),
                "field_name": field.field_name,
                "field_type": field.field_type,
                "is_required": field.is_required,
                "options": field.options,
            } for field in data]  # ✅ list of dicts, not model objects
        )
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.put("/custom-field/update-field/{field_id}", response_model=dict)
def update_field(field_id: UUID, data: CustomFieldUpdate, request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        field = crud_contact.update_field(db, field_id, data)
        return ResponseHandler.success(
            message=translator.t("custom_field_updated", lang),
            data={"id": str(field.id)}
        )
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.delete("/custom-field/delete-field/{field_id}", response_model=dict)
def delete_field_api(field_id: UUID, request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        deleted = crud_contact.delete_field(db, field_id)
        if not deleted:
            raise ResponseHandler.internal_error(message=translator.t("field_not_found", lang))
        return ResponseHandler.success(
            message=translator.t("custom_field_deleted", lang)
        )
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

# Create Tag
@router.post("/tags/create-tag/{business_id}", response_model=dict)
def create_tag(business_id: int, payload: TagCreate, request: Request, db: Session = Depends(get_db),current_user: User = Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        tag = crud_contact.create_tag(db, business_id, payload.name, payload.color,current_user.id)
        return ResponseHandler.success(
            message=translator.t("tag_created", lang),
            data=str(tag.id)
        )
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.get("/tags/get-tags/{business_id}", response_model=dict)
def list_tags(business_id: int, request: Request, search: str = None,page: int = 1,page_size: int = 20,db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        tags = crud_contact.get_tags_for_business(db, business_id, search, page, page_size)
        if not tags or len(tags) == 0:
            return ResponseHandler.not_found(message=translator.t("no_tags_found", lang))
        return ResponseHandler.success(
            message=translator.t("tags_fetched", lang),
            data={
                "items": [
                    {
                        "id": str(tag.id),
                        "name": tag.name,
                        "color": tag.color
                    }
                    for tag in tags["items"]
                ],
                "total": tags["total"],
                "page": tags["page"],
                "page_size": tags["page_size"]
            }
        )
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.put("/tags/update-tag/{tag_id}", response_model=dict)
def edit_tag(tag_id: UUID, data: TagUpdate, request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        tag = crud_contact.update_tag(db, tag_id, data.name, data.color)
        if not tag:
            return ResponseHandler.internal_error(
                message=translator.t("tag_not_found", lang)
            )
        return ResponseHandler.success(
            message=translator.t("tag_updated", lang),
            data=str(tag.id)
        )
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.delete("/tags/delete-tag/{tag_id}", response_model=dict)
def delete_tag_api(tag_id: UUID, request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        tag = crud_contact.delete_tag(db, tag_id)
        if not tag:
            return ResponseHandler.internal_error(
                message=translator.t("tag_not_found", lang)
            )
        return ResponseHandler.success(
            message=translator.t("tag_deleted", lang)
        )
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )
    
@router.get("/tags/tag-dropdown")
def get_tag_dropdown(request: Request, db: Session = Depends(get_db),current_user: User = Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        tags = crud_contact.get_tag_dropdown(db,current_user)
        return ResponseHandler.success(
            data=jsonable_encoder(tags)
        )
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )
    
# Groups
@router.post("/groups/create-group/{business_id}", response_model=GroupOut)
def create_group_api(business_id: int, payload: GroupCreate, request: Request, db: Session = Depends(get_db),current_user: User = Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        group = crud_contact.create_group(db, business_id, payload, created_by=current_user.id)
        return ResponseHandler.success(message=translator.t("group_created", lang), data=str(group.id))
    except Exception as e:
        return ResponseHandler.internal_error(message=translator.t("something_went_wrong", lang), error=str(e))

@router.get("/groups/get-groups/{business_id}", response_model=dict)
def list_groups_api(business_id: int, request: Request, search: str = None, page: int = 1, page_size: int = 20, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)

    try:
        result = crud_contact.get_groups(db, business_id, search, page, page_size)
        return ResponseHandler.success(
            message=translator.t("groups_fetched", lang), 
            data={
                "items": [
                    {
                        "id": str(group.id),
                        "name": group.name,
                        "description": group.description,
                        "is_dynamic": group.is_dynamic,
                        "filters": None
                    }
                    for group in result["items"]
                ],
                "total": result["total"],
                "page": result["page"],
                "page_size": result["page_size"]
            }
            )
    except Exception as e:
        return ResponseHandler.internal_error(message=translator.t("something_went_wrong", lang), error=str(e))

@router.put("/groups/update-group/{group_id}", response_model=GroupOut)
def update_group_api(group_id: UUID, payload: GroupUpdate, request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        group = crud_contact.update_group(db, group_id, payload)
        if not group:
            raise HTTPException(status_code=404, detail=translator.t("group_not_found", lang))
        return ResponseHandler.success(message=translator.t("group_updated", lang), data=str(group.id))
    except Exception as e:
        return ResponseHandler.internal_error(message=translator.t("something_went_wrong", lang), error=str(e))

@router.delete("/groups/delete-group/{group_id}", response_model=dict)
def delete_group_api(group_id: UUID, request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        deleted = crud_contact.delete_group(db, group_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=translator.t("group_not_found", lang))
        return ResponseHandler.success(message=translator.t("group_deleted", lang))
    except Exception as e:
        return ResponseHandler.internal_error(message=translator.t("something_went_wrong", lang), error=str(e))

@router.get("/groups/get-group-data/{group_id}", response_model=dict)
def list_groups_api(group_id: UUID, request: Request,db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        result = crud_contact.get_group_data(db, group_id)
        return ResponseHandler.success(
            message=translator.t("groups_fetched", lang), 
            data= jsonable_encoder(result)
        )
    except Exception as e:
        return ResponseHandler.internal_error(message=translator.t("something_went_wrong", lang), error=str(e))

@router.get("/groups/group-dropdown")
def get_group_dropdown(request: Request, db: Session = Depends(get_db),current_user: User = Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        tags = crud_contact.get_group_dropdown(db,current_user)
        return ResponseHandler.success(
            data=jsonable_encoder(tags)
        )
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )
    
@router.get("/ledger/get-ledgers")
def get_ledgers(request: Request, search: str = None ,contact_id:UUID = None, type:str = None , page: int = 1, page_size: int = 20, db: Session = Depends(get_db),current_user: User = Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        result = crud_contact.get_ledgers(db, search,contact_id, type ,page, page_size, current_user)
        return ResponseHandler.success(
            message=translator.t("groups_fetched", lang), 
            data = jsonable_encoder(result)
            )
    except Exception as e:
        return ResponseHandler.internal_error(message=translator.t("something_went_wrong", lang), error=str(e))

@router.post("/ledger/create-ledger")
def create_ledger(payload: CreateLedger, request: Request, db: Session = Depends(get_db),current_user: User = Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        group = crud_contact.create_ledger(db,payload,current_user)
        return ResponseHandler.success(message=translator.t("group_created", lang), data=str(group.id))
    except Exception as e:
        return ResponseHandler.internal_error(message=translator.t("something_went_wrong", lang), error=str(e))

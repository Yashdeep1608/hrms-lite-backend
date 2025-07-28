from slugify import slugify
from sqlalchemy import distinct, func, or_
from sqlalchemy.orm import Session, joinedload
from app.models.banner import Banner
from app.models.combo import Combo, ComboItem
from app.models.offer import Offer, OfferCondition, OfferReward
from app.models.user import User
from app.schemas.banner import BannerCreate, BannerFilters, BannerUpdate
from app.schemas.combo import ComboCreate, ComboFilter, ComboUpdate
from app.schemas.offer import OfferCreate, OfferFilters, OfferUpdate

# Banner Methods
def create_banner(db: Session, banner_in: BannerCreate, current_user: User) -> Banner:
    banner_data = banner_in.model_dump(exclude_unset=True)
    banner_data["business_id"] = current_user.business_id
    banner_data["created_by_user_id"] = current_user.id

    banner = Banner(**banner_data)
    db.add(banner)
    db.commit()
    db.refresh(banner)
    return banner

def get_banner(db: Session, banner_id: int) -> Banner:
    return db.query(Banner).filter(Banner.id == banner_id).first()

def get_all_banners(db: Session, filters: BannerFilters, current_user: User):
    query = db.query(Banner).filter(Banner.business_id == current_user.business_id)

    # Filter: is_active
    if filters.is_active is not None:
        query = query.filter(Banner.is_active == filters.is_active)

    # Filter: type
    if filters.type:
        query = query.filter(Banner.type == filters.type)

    # Filter: search (title or link_text)
    if filters.search:
        search_term = f"%{filters.search}%"
        query = query.filter(or_(
            Banner.title.ilike(search_term),
            Banner.link_text.ilike(search_term)
        ))

    # Filter: date range
    if filters.from_date:
        query = query.filter(Banner.created_at >= filters.from_date)
    if filters.to_date:
        query = query.filter(Banner.created_at <= filters.to_date)

    # Sorting logic
    sort_column = getattr(Banner, filters.sort_by, Banner.created_at)
    if filters.sort_dir == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Pagination
    total = query.count()
    banners = (
        query
        .offset((filters.page - 1) * filters.page_size)
        .limit(filters.page_size)
        .all()
    )

    return {
        "total": total,
        "items": banners
    }

def update_banner(db: Session, banner_id: int, banner_in: BannerUpdate, current_user: User):
    banner = db.query(Banner).filter(
        Banner.id == banner_id,
        Banner.business_id == current_user.business_id  # Prevent unauthorized updates
    ).first()

    if not banner:
        return None

    banner_data = banner_in.model_dump(exclude_unset=True)
    for key, value in banner_data.items():
        setattr(banner, key, value)

    # Optional: track updated_by_user_id if needed
    # banner.updated_by_user_id = current_user.id

    db.commit()
    db.refresh(banner)
    return banner

def delete_banner(db: Session, banner_id: int):
    banner = db.query(Banner).filter(Banner.id == banner_id).first()
    if banner:
        db.delete(banner)
        db.commit()
    return banner


# Combo Methods 
def create_combo(db: Session, combo_in: ComboCreate, current_user: User):
    slug = slugify(combo_in.name.lower())
    combo = Combo(
        business_id=current_user.business_id,
        name=combo_in.name,
        slug=slug,
        description=combo_in.description,
        combo_price=combo_in.combo_price,
        discount_type=combo_in.discount_type,
        discount_value=combo_in.discount_value,
        max_discount=combo_in.max_discount,
        is_active=combo_in.is_active,
        is_online=combo_in.is_online,
        is_featured=combo_in.is_featured,
        image_url=combo_in.image_url,
        created_by_user_id=current_user.id,
    )
    db.add(combo)
    db.flush()  # So combo.id is available

    for item in combo_in.items:
        combo.items.append(ComboItem(
            combo_id=combo.id,
            item_type=item.item_type,
            item_id=item.item_id,
            quantity=item.quantity
        ))

    db.commit()
    db.refresh(combo)
    return combo

def update_combo(db: Session, combo_id: int, combo_in: ComboUpdate):
    combo = db.query(Combo).filter(Combo.id == combo_id).first()
    if not combo:
        return None

    update_data = combo_in.model_dump(exclude={"items"}, exclude_unset=True)
    for key, value in update_data.items():
        if key == "items":
            combo.items.clear()
            for item in value:
                combo.items.append(ComboItem(
                    combo_id=combo.id,
                    item_type=item.item_type,
                    item_id=item.item_id,
                    quantity=item.quantity
                ))
        else:
            setattr(combo, key, value)

    db.commit()
    db.refresh(combo)
    return combo

def delete_combo(db: Session, combo_id: int):
    combo = db.query(Combo).filter(Combo.id == combo_id).first()
    if not combo:
        return False
    db.delete(combo)
    db.commit()
    return True

def get_all_combos(db: Session, filters: ComboFilter, current_user: User):
    subq = (
        db.query(
            ComboItem.combo_id,
            func.array_agg(distinct(ComboItem.item_type)).label("item_types")
        )
        .group_by(ComboItem.combo_id)
        .subquery()
    )

    query = (
        db.query(
            Combo.id,
            Combo.image_url,
            Combo.name,
            Combo.combo_price,
            Combo.is_active,
            Combo.is_featured,
            Combo.is_online,
            Combo.created_at,
            subq.c.item_types
        )
        .join(subq, Combo.id == subq.c.combo_id)
        .filter(Combo.business_id == current_user.business_id)
    )

    # Filtering
    if filters.is_active is not None:
        query = query.filter(Combo.is_active == filters.is_active)
    if filters.is_online is not None:
        query = query.filter(Combo.is_online == filters.is_online)
    if filters.is_featured is not None:
        query = query.filter(Combo.is_featured == filters.is_featured)
    if filters.search:
        query = query.filter(Combo.name.ilike(f"%{filters.search}%"))

    if filters.item_type:
        item_type = filters.item_type.lower()
        if item_type in {"product", "service"}:
            query = query.filter(
                func.array_length(subq.c.item_types, 1) == 1,
                subq.c.item_types[1] == item_type
            )
        elif item_type == "hybrid":
            query = query.filter(func.array_length(subq.c.item_types, 1) > 1)

    total = query.count()

    # Sorting
    sort_field = getattr(Combo, filters.sort_by or "created_at", Combo.created_at)
    sort_order = sort_field.desc() if (filters.sort_dir or "desc").lower() == "desc" else sort_field.asc()
    query = query.order_by(sort_order)

    # Pagination
    page = filters.page or 1
    page_size = filters.page_size or 20
    offset = (page - 1) * page_size
    combos = query.offset(offset).limit(page_size).all()

    # Format result
    result = []
    for combo in combos:
        combo_type = "hybrid" if len(combo.item_types or []) > 1 else combo.item_types[0] if combo.item_types else None

        result.append({
            "id": combo.id,
            "name": combo.name,
            "image_url": combo.image_url,
            "combo_price": combo.combo_price,
            "is_active": combo.is_active,
            "is_featured": combo.is_featured,
            "is_online": combo.is_online,
            "created_at": combo.created_at,
            "type": combo_type,
        })

    return {
        "total": total,
        "items": result
    }

def get_combo(db:Session,combo_id:int):
    combo = (
        db.query(Combo)
        .options(
            joinedload(Combo.items),         # Load combo items
        )
        .filter(Combo.id == combo_id)
        .first()
    )
    return combo


# Offers Methods
def create_offer(db: Session, payload: OfferCreate, current_user: User):
    offer = Offer(
        name=payload.name,
        description=payload.description,
        offer_type=payload.offer_type,
        is_active=payload.is_active,
        valid_from=payload.start_datetime,
        valid_to=payload.end_datetime,
        auto_apply=payload.auto_apply,
        business_id=current_user.business_id,
        created_by_user_id=current_user.id,
    )

    db.add(offer)
    db.flush()  # Get offer.id

    for condition in payload.conditions:
        db.add(OfferCondition(
            offer_id=offer.id,
            condition_type=condition.condition_type,
            operator=condition.operator,
            value=condition.value,
            quantity=condition.quantity,
        ))

    db.add(OfferReward(
        offer_id=offer.id,
        reward_type=payload.reward_type,
        value=payload.reward_value
    ))

    db.commit()
    db.refresh(offer)
    return offer

def update_offer(db: Session, offer_id: int, payload: OfferUpdate):
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise Exception("Offer not found")
    update_data = payload.model_dump(exclude_unset=True)
    for attr, value in update_data:
        if attr in ['start_datetime', 'end_datetime']:
            setattr(offer, 'valid_from' if attr == 'start_datetime' else 'valid_to', value)
        elif attr not in ['conditions', 'reward_type', 'reward_value']:
            setattr(offer, attr, value)

    # Update reward
    if payload.reward_type or payload.reward_value is not None:
        reward = offer.rewards[0] if offer.rewards else None
        if reward:
            reward.reward_type = payload.reward_type or reward.reward_type
            reward.value = payload.reward_value or reward.value
        else:
            db.add(OfferReward(
                offer_id=offer.id,
                reward_type=payload.reward_type,
                value=payload.reward_value
            ))

    # Update conditions
    if payload.conditions is not None:
        db.query(OfferCondition).filter(OfferCondition.offer_id == offer.id).delete()
        for cond in payload.conditions:
            db.add(OfferCondition(
                offer_id=offer.id,
                condition_type=cond.condition_type,
                operator=cond.operator,
                value=cond.value,
                quantity=cond.quantity,
            ))

    db.commit()
    db.refresh(offer)
    return offer

def delete_offer(db: Session, offer_id: int):
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    db.delete(offer)
    db.commit()
    return True

def get_offer_by_id(db: Session, offer_id: int):
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    return offer

def get_all_offers(db: Session, filters:OfferFilters, current_user: User):
    query = db.query(Offer).filter(Offer.business_id == current_user.business_id)

    if filters.is_active is not None:
        query = query.filter(Offer.is_active == filters.is_active)
    if filters.search:
        query = query.filter(Offer.name.ilike(f"%{filters.search}%"))
    if filters.from_date:
        query = query.filter(Offer.valid_from >= filters.from_date)
    if filters.to_date:
        query = query.filter(Offer.valid_to <= filters.to_date)

    total = query.count()
    offers = query.order_by(
        getattr(getattr(Offer, filters.sort_by or "valid_from"), filters.sort_dir or "asc")()
    ).offset((filters.page - 1) * filters.page_size).limit(filters.page_size).all()

    return {
        "total": total,
        "items": offers
    }
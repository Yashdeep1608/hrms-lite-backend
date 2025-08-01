from datetime import datetime, time, timezone
from decimal import ROUND_HALF_UP, Decimal
from sqlalchemy import UUID, DateTime, func, or_
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload
from typing import List, Optional
from app.crud.contact import create_contact
from app.crud.product import add_product_stock_log
from app.models import Cart, CartItem
from app.models.combo import Combo
from app.models.contact import BusinessContact, BusinessContactLedger, Contact
from app.models.coupon import Coupon
from app.models.enums import CartOrderSource, CartOrderStatus, CartStatus, ConditionOperator, OfferConditionType, OfferType, OrderPaymentMethod, OrderPaymentStatus
from app.models.offer import Offer, OfferCondition
from app.models.order import Order, OrderActionLog, OrderDeliveryDetail, OrderPayment, OrderStatusLog
from app.models.product import Product
from app.models.service import Service, ServiceBookingLog
from app.models.user import User
from app.schemas.cart import AddToCart, AssignCartContact, CartEntities
from sqlalchemy import and_

from app.schemas.contact import ContactCreate
from app.schemas.order import OrderStatusUpdateRequest, PayNowRequest, PlaceOrderRequest

def calculate_cart_prices(item, quantity: int = 1, item_type: str = "product"):
    quantity = max(quantity, 1)

    # Helper function to calculate prices given base price and discount info
    def _calc_prices(
        base_price,
        discount_type=None,
        discount_value=None,
        max_discount=None,
        include_tax=False,
        tax_rate=None
    ):
        base_price = Decimal(base_price or 0).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        discount_amount = Decimal('0.00')

        if discount_type == "percentage" and discount_value:
            discount_amount = (base_price * Decimal(discount_value) / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        elif discount_type == "flat" and discount_value:
            discount_amount = Decimal(discount_value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        # Cap discount by max_discount
        if max_discount is not None:
            max_discount_d = Decimal(max_discount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            if discount_amount > max_discount_d:
                discount_amount = max_discount_d

        price_after_discount = base_price - discount_amount
        if price_after_discount < 0:
            price_after_discount = Decimal('0.00')

        tax_amount = Decimal('0.00')
        if include_tax and tax_rate:
            tax_amount = (price_after_discount * Decimal(tax_rate) / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        final_unit_price = price_after_discount + tax_amount

        return base_price, discount_amount, tax_amount, final_unit_price
    if item_type == "product":
        # Product fields expected:
        # selling_price, discount_type, discount_value, max_discount, include_tax, tax_rate
        selling_price = getattr(item, "selling_price", 0)
        discount_type = getattr(item, "discount_type", None)
        discount_value = getattr(item, "discount_value", None)
        max_discount = getattr(item, "max_discount", None)
        include_tax = getattr(item, "include_tax", False)
        tax_rate = getattr(item, "tax_rate", None)

        actual_price, discount_price, tax_amount, final_price = _calc_prices(
            selling_price, discount_type, discount_value, max_discount, include_tax, tax_rate
        )

    elif item_type == "service":
        # Service fields:
        # price, discount_type, discount_value, max_discount, include_tax, tax_rate
        base_price = getattr(item, "price", 0)
        discount_type = getattr(item, "discount_type", None)
        discount_value = getattr(item, "discount_value", None)
        max_discount = getattr(item, "max_discount", None)
        include_tax = getattr(item, "include_tax", False)
        tax_rate = getattr(item, "tax_rate", None)

        actual_price, discount_price, tax_amount, final_price = _calc_prices(
            base_price, discount_type, discount_value, max_discount, include_tax, tax_rate
        )

    elif item_type == "combo":
        # Combo fields:
        # combo_price, discount_type (default "none"), discount_value, max_discount
        # Tax and include_tax NOT mentioned for combo, so we assume no tax here.
        combo_price = getattr(item, "combo_price", 0)
        discount_type = getattr(item, "discount_type", None)
        discount_value = getattr(item, "discount_value", None)
        max_discount = getattr(item, "max_discount", None)

        # Tax fields are missing/not defined for combos; assuming no tax
        actual_price, discount_price, tax_amount, final_price = _calc_prices(
            combo_price, discount_type, discount_value, max_discount, include_tax=False, tax_rate=None
        )

    else:
        raise ValueError(f"Unknown item_type: {item_type}")

    # Multiply all prices by quantity
    actual_price_total = (actual_price * quantity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    discount_price_total = (discount_price * quantity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    tax_amount_total  = (tax_amount  * quantity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    final_price_total = (final_price * quantity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return actual_price_total, discount_price_total, tax_amount_total, final_price_total
def generate_order_number(business_id: int) -> str:
    timestamp_ms = int(time.time() * 1000)
    business_part = hex(business_id)[2:].upper()  # remove '0x' and uppercase
    return f"ORD-{business_part}-{timestamp_ms}"
def reduce_stock_for_order(db: Session, order_id: int, cart_id: int):
    cart = db.query(Cart).filter(Cart.id == cart_id).first()
    if not cart:
        raise ValueError(f"Cart {cart_id} not found")

    def get_effective_start_date(item):
        return item.start_date or datetime.now(timezone.utc)

    def reduce_product_stock(product_id: int, quantity: int):
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError(f"Product {product_id} not found")
        if product.stock_qty is None:
            return  # Untracked/digital product
        if product.stock_qty < quantity:
            raise ValueError(f"Insufficient stock for product: {product.name}")
        product.stock_qty -= quantity
        add_product_stock_log(
            db=db,
            product_id=product.id,
            quantity=quantity,
            is_stock_in=False,
            source="order",
            source_id=order_id,
            created_by=cart.created_by_user_id
        )

    def log_service_booking(service_id: int, quantity: int, start_date, in_combo=False):
        service = db.query(Service).filter(Service.id == service_id).first()
        if not service:
            raise ValueError(f"Service {service_id} {'in combo' if in_combo else ''} not found")

        if service.capacity is not None:
            total_booked = db.query(func.coalesce(func.sum(ServiceBookingLog.quantity), 0)).filter(
                ServiceBookingLog.service_id == service_id,
                ServiceBookingLog.start_date == start_date
            ).scalar()
            if total_booked + quantity > service.capacity:
                raise ValueError(
                    f"Insufficient capacity for service: {service.name} {'in combo' if in_combo else ''} on {start_date.date()}"
                )

        booking_log = ServiceBookingLog(
            service_id=service_id,
            order_id=order_id,
            business_contact_id=cart.business_contact_id,
            start_date=start_date,
            quantity=quantity
        )
        db.add(booking_log)

    for item in cart.items:
        start_date = get_effective_start_date(item)

        if item.item_type == "product":
            reduce_product_stock(item.item_id, item.quantity)

        elif item.item_type == "service":
            log_service_booking(item.item_id, item.quantity, start_date)

        elif item.item_type == "combo":
            combo = db.query(Combo).filter(Combo.id == item.item_id).first()
            if not combo:
                raise ValueError(f"Combo {item.item_id} not found")

            for combo_item in combo.items:
                combo_qty = combo_item.quantity * item.quantity

                if combo_item.item_type == "product":
                    reduce_product_stock(combo_item.item_id, combo_qty)

                elif combo_item.item_type == "service":
                    log_service_booking(combo_item.item_id, combo_qty, start_date, in_combo=True)

    # Handle coupon usage
    if cart.coupon_id:
        coupon = db.query(Coupon).filter(Coupon.id == cart.coupon_id).first()
        if coupon and coupon.is_active:
            coupon.applied_count = coupon.applied_count or 0
            if coupon.available_limit is not None:
                if coupon.applied_count >= coupon.available_limit:
                    raise ValueError("Coupon usage limit exceeded")
                coupon.applied_count += 1
                if coupon.applied_count >= coupon.available_limit:
                    coupon.is_active = False

    db.flush()

def get_entities(db: Session, payload: CartEntities, current_user: User):
    products, services, combos = [], [], []

    # Determine what needs to be fetched based on business_type and bools
    fetch_products = False
    fetch_services = False
    fetch_combos = False

    # If all bools are False, fetch all available per business type
    if not payload.is_products and not payload.is_services and not payload.is_combos:
        if payload.business_type == "product_based":
            fetch_products = True
            fetch_combos = True
            fetch_services = False
        elif payload.business_type == "service_based":
            fetch_services = True
            fetch_combos = True
            fetch_products = False
        elif payload.business_type == "hybrid":
            fetch_products = True
            fetch_services = True
            fetch_combos = True
        else:
            # If business_type not specified, assume fetch all
            fetch_products = True
            fetch_services = True
            fetch_combos = True
    else:
        # Use the bools to determine what to fetch
        fetch_products = payload.is_products
        fetch_services = payload.is_services
        fetch_combos = payload.is_combos

    # Always fetch combos if fetch_combos is True
    if fetch_products:
        query = db.query(Product).filter(
            Product.business_id == current_user.business_id,
            or_(
                Product.parent_product_id == None,
                and_(Product.parent_product_id != None, Product.is_product_variant == False)
            )
        )

        if payload.search:
            query = query.filter(Product.name.ilike(f"%{payload.search}%"))
        if payload.category_id:
            query = query.filter(Product.category_id == payload.category_id)

        # Apply sorting
        sort_column = getattr(Product, payload.sort_by, Product.name)
        if payload.sort_dir == "desc":
            sort_column = sort_column.desc()
        else:
            sort_column = sort_column.asc()
        query = query.order_by(sort_column)

        # Pagination
        products = query.offset((payload.page - 1) * payload.page_size).limit(payload.page_size).all()

        # Now attach variants for variantable base products, if any
        for product in products:
            if product.is_product_variant and product.parent_product_id is None:
                variants = db.query(Product).filter(
                    Product.parent_product_id == product.id,
                    Product.is_product_variant == True
                ).all()
                product.variants = variants

    if fetch_services:
        query = db.query(Service).filter(
            Service.is_active == True,
            Service.business_id == current_user.business_id,
            )
        if payload.search:
            query = query.filter(Service.name.ilike(f"%{payload.search}%"))
        if payload.category_id:
            query = query.filter(Service.category_id == payload.category_id)
        services = query.order_by(
            getattr(Service, payload.sort_by).desc() if payload.sort_dir == "desc" else getattr(Service, payload.sort_by)
        ).offset((payload.page-1)*payload.page_size).limit(payload.page_size).all()

    if fetch_combos:
        query = db.query(Combo).filter(
            Combo.is_active == True,
            Combo.business_id == current_user.business_id,
            )
        if payload.search:
            query = query.filter(Combo.name.ilike(f"%{payload.search}%"))
        if payload.category_id:
            query = query.filter(Combo.category_id == payload.category_id)
        combos = query.order_by(
            getattr(Combo, payload.sort_by).desc() if payload.sort_dir == "desc" else getattr(Combo, payload.sort_by)
        ).offset((payload.page-1)*payload.page_size).limit(payload.page_size).all()

    return {
        "products": products,
        "services": services,
        "combos": combos
    }

def add_to_cart(db: Session, payload: AddToCart, current_user: User = None):
    def get_or_create_cart():
        filters = []
        if payload.source == CartOrderSource.BACK_OFFICE:
            filters.append(Cart.created_by_user_id == current_user.id)
        if payload.business_contact_id:
            filters.append(Cart.business_contact_id == payload.business_contact_id)
        if payload.anonymous_id:
            filters.append(Cart.anonymous_id == payload.anonymous_id)
        filters.append(Cart.cart_status == CartStatus.ACTIVE)

        cart = db.query(Cart).filter(*filters).first()

        if not cart:
            cart = Cart(
                business_id=payload.business_id or None,
                business_contact_id=payload.business_contact_id or None,
                anonymous_id=payload.anonymous_id or None,
                created_by_user_id=current_user.id if current_user else None,
                source = payload.source
            )
            db.add(cart)
            db.commit()
            db.refresh(cart)
        return cart

    def add_cart_item(cart: Cart):
        item_type = payload.item_type
        item_id = payload.item_id
        quantity = payload.quantity or 1

        model_map = {
            'product': Product,
            'service': Service,
            'combo': Combo,
        }

        if item_type not in model_map:
            raise ValueError("Invalid item type")

        model = model_map[item_type]
        item = db.query(model).filter(model.id == item_id).first()
        if not item:
            raise ValueError(f"{item_type.capitalize()} not found")

        # Product Quantity Check
        if item_type == 'product':
            available_qty = item.stock_qty or 0
            quantity = min(quantity, available_qty)
            if quantity <= 0:
                raise ValueError("Requested quantity is not available in stock")
        else:
            quantity = 1  # Only 1 allowed for service/combo

        actual_price, discount_price, tax_amount, final_price = calculate_cart_prices(item, quantity, item_type=item_type)

        cart_item = CartItem(
            cart_id=cart.id,
            item_type=item_type,
            item_id=item_id,
            quantity=quantity,
            name=item.name,
            actual_price=actual_price,
            discount_price=discount_price,
            tax_amount = tax_amount,
            final_price=final_price,
            time_slot=payload.time_slot or None,
            start_date=payload.start_date or None,
            day=payload.day or None,
        )
        db.add(cart_item)
        db.commit()
        return cart.id

    # Validate basic ID presence
    if payload.source == CartOrderSource.BACK_OFFICE and not current_user:
        raise ValueError("Missing current user for back office")

    if not any([current_user, payload.business_contact_id, payload.anonymous_id]):
        raise ValueError("No business contact or anonymous user info provided")

    cart = get_or_create_cart()
    return add_cart_item(cart)

def update_cart_item(db: Session, cart_item_id: int, quantity: int):
    cart_item = db.query(CartItem).filter(CartItem.id == cart_item_id).first()
    if not cart_item:
        raise ValueError("Cart item not found")

    if quantity <= 0:
        # Optional: delete cart item if quantity is 0
        db.delete(cart_item)
        db.commit()
        return "removed"

    # Fetch item based on item_type
    model_map = {
        'product': Product,
        'service': Service,
        'combo': Combo,
    }

    item_model = model_map.get(cart_item.item_type)
    if not item_model:
        raise ValueError("Invalid item type")

    item = db.query(item_model).filter(item_model.id == cart_item.item_id).first()
    if not item:
        raise ValueError(f"{cart_item.item_type.capitalize()} not found")

    # Product stock check
    if cart_item.item_type == 'product':
        available_qty = item.stock_qty or 0
        if quantity > available_qty:
            quantity = available_qty
        if quantity <= 0:
            raise ValueError("Requested quantity exceeds available stock")

    # Always re-calculate prices
    actual_price, discount_price, tax_amount,final_price = calculate_cart_prices(item, quantity, item_type=cart_item.item_type)

    # Update cart item
    cart_item.quantity = quantity
    cart_item.actual_price = actual_price
    cart_item.discount_price = discount_price
    cart_item.tax_amount = tax_amount
    cart_item.final_price = final_price

    db.commit()
    db.refresh(cart_item)
    return True

def remove_cart_item(db: Session, cart_item_id:int):
    cart_item = db.get(CartItem, cart_item_id)
    if not cart_item:
        raise ValueError("Cart item not found")
    
    db.delete(cart_item)
    db.commit()
    return True

def delete_cart(db:Session, cart_id):
    cart = db.query(Cart).filter(Cart.id == cart_id).first()
    if not cart:
        raise ValueError("Cart not found")
    cart.cart_status = CartStatus.ABANDONED
    db.commit()
    return True

def get_cart(db: Session,business_id:int,business_contact_id:UUID = None,anonymous_id:UUID = None,user_id:int = None):
    filters = [Cart.cart_status == CartStatus.ACTIVE, Cart.business_id == business_id]
    if user_id:
        filters.append(Cart.created_by_user_id == user_id)
    if business_contact_id:
        filters.append(Cart.business_contact_id == business_contact_id)
    if anonymous_id:
        filters.append(Cart.anonymous_id == anonymous_id)

    cart = db.query(Cart).filter(*filters).first()
    if not cart:
        return None

    cart = db.query(Cart).options(selectinload(Cart.items)).filter(*filters).first()

    if cart.business_contact_id and cart.coupon_id is None and not cart.coupon_removed:
        total_cart_value = sum(item.final_price * item.quantity for item in cart.items)
        coupon = db.query(Coupon).filter(
            Coupon.is_auto_applied == True,
            Coupon.business_id == business_id,
            Coupon.min_cart_value <= total_cart_value,
            Coupon.is_active == True
        ).order_by(Coupon.created_at.desc).first()
        if coupon:
            try:
                result = apply_coupon(db, cart, coupon.code)
                if result.get("success"):
                    cart.coupon_id = result["coupon_id"]
                    cart.coupon_discount = result["discount"]
                    db.commit()
                    db.refresh(cart)
            except ValueError:
                pass
    # elif cart.offer_id is None and cart.coupon_id is None and cart.business_contact_id:
    #     result = apply_offer(db,cart,is_auto_apply=True)
    return cart
    
def apply_coupon(db: Session, cart_id:int, coupon_code: str = None):    
    # Fetch cart items
    cart = db.query(Cart).filter(Cart.id == cart_id).first()
    cart_items = db.query(CartItem).filter(CartItem.cart_id == cart.id).all()
    total_cart_value = sum(item.final_price * item.quantity for item in cart_items)
    
    # Get coupon
    coupon = db.query(Coupon).filter(Coupon.code == coupon_code).first()
    if not coupon or not coupon.is_active:
        raise ValueError("Invalid coupon code")

    now = datetime.now(timezone.utc)

    if coupon.valid_from and coupon.valid_from > now:
        raise ValueError("Invalid coupon code")
    if coupon.valid_to and coupon.valid_to < now:
        raise ValueError("Coupon Expired")
    if coupon.min_cart_value and total_cart_value < coupon.min_cart_value:
        raise ValueError("Coupon not applicable")

    # Check overall available limit
    if coupon.available_limit is not None:
        total_usage = db.query(func.count(Cart.id)).filter(
            Cart.coupon_id == coupon.id,
            Cart.cart_status == CartStatus.COMPLETED
            ).scalar()
        if total_usage >= coupon.available_limit:
            raise ValueError("Coupon limit exceed")

    # Check per-user/customer usage limit
    if coupon.usage_limit is not None and cart.business_contact_id:
        user_usage = db.query(func.count(Cart.id)).filter(
            Cart.business_contact_id == cart.business_contact_id,
            Cart.coupon_id == coupon.id,
            Cart.cart_status == CartStatus.COMPLETED
        ).scalar()
        if user_usage >= coupon.usage_limit:
            raise ValueError("You have used this coupon the maximum number of times")

    # Handle exclusions
    excluded_product_ids = coupon.exclude_product_ids or []
    excluded_service_ids = coupon.exclude_service_ids or []

    eligible_items = []
    for item in cart_items:
        if item.item_type == 'product':
            if item.item_id not in excluded_product_ids:
                eligible_items.append(item)
        if item.item_type == 'service':
            if item.item_id not in excluded_service_ids:
                eligible_items.append(item)
    eligible_total = sum(item.final_price * item.quantity for item in eligible_items)

    if eligible_total == 0:
        return {"success": False, "message": "No eligible items for this coupon"}

    # Apply discount
    if coupon.discount_type == "flat":
        discount = max(0, min(coupon.discount_value, eligible_total))
    else:
        discount = eligible_total * (coupon.discount_value / 100)
        if coupon.max_discount_amount:
            discount = max(0,min(discount, coupon.max_discount_amount))

    # Assign coupon to cart
    cart.coupon_id = coupon.id

    for item in eligible_items:
         item.applied_coupon_id = coupon.id

    db.commit()

    return {
        "success": True,
        "discount": discount,
        "coupon_id": coupon.id
    }

def remove_coupon(db: Session, cart_id:int):
    cart = db.query(Cart).filter(Cart.id == cart_id).first()
    if not cart.coupon_id:
        raise ValueError("No coupon to remove")

    # Reset coupon_id on cart
    cart.coupon_id = None
    cart.coupon_discount = 0
    cart.coupon_removed = True
    # Reset applied_coupon_id on cart items
    db.query(CartItem).filter(
        CartItem.cart_id == cart.id,
        CartItem.applied_coupon_id.is_not(None)
    ).update({CartItem.applied_coupon_id: None}, synchronize_session=False)

    db.commit()

    return True

def assign_cart_contact(db: Session, payload: AssignCartContact, current_user: User):
    business_id = current_user.business_id

    # If business_contact_id is provided, use it directly
    if payload.business_contact_id:
        business_contact = db.query(BusinessContact).filter_by(
            id=payload.business_contact_id,
            business_id=business_id
        ).first()
        if not business_contact:
            raise ValueError("Business contact not found")
    else:
        if not payload.phone_number or not payload.isd_code:
            raise ValueError("Either business_contact_id or phone_number and isd_code must be provided")

        contact_data = ContactCreate(
            phone_number=payload.phone_number,
            isd_code=payload.isd_code,
            country_code="IN"
        )

        try:
            # Try to create new
            business_contact = create_contact(
                db=db,
                user_id=current_user.id,
                business_id=business_id,
                contact_data=contact_data
            )
        except ValueError:
            # Fetch existing Contact
            contact = db.query(Contact).filter_by(
                phone_number=payload.phone_number,
                isd_code=payload.isd_code
            ).first()
            if not contact:
                raise ValueError("Existing contact not found after duplicate error")

            # Fetch BusinessContact
            business_contact = db.query(BusinessContact).filter_by(
                contact_id=contact.id,
                business_id=business_id
            ).first()
            if not business_contact:
                raise ValueError("Existing business contact not found")



    # Now assign the business_contact to the cart
    cart = db.query(Cart).filter_by(
        id=payload.cart_id,
        business_id=business_id
    ).first()

    if not cart:
        raise ValueError("Cart not found")

    cart.business_contact_id = business_contact.id
    db.commit()
    db.refresh(cart)

    return True

    
# def apply_offer(db:Session,cart:Cart,is_auto_apply:bool = False,offer_id:int = None):
#     cart_items = db.query(CartItem).filter(CartItem.cart_id == cart.id).all()
#     total_cart_value = sum(item.final_price * item.quantity for item in cart_items)
#     is_first_order = False
#     if is_auto_apply and cart.business_contact_id:
#         order = db.query(Order).filter(
#             Order.business_contact_id == cart.business_contact_id,
#             Order.status == CartOrderStatus.COMPLETED,
#         ).first()
#         if not order:
#             is_first_order = True

#     def get_applicable_offer(offer_type, condition_type, cart_items=None,cart_total = None):
#         query = db.query(Offer.id).join(OfferCondition).filter(
#             Offer.auto_apply.is_(True),
#             Offer.is_active.is_(True),
#             Offer.offer_type == offer_type,
#             OfferCondition.condition_type == condition_type,
#         )

#         if offer_type == OfferType.BUY_X_GET_Y and condition_type == OfferConditionType.PRODUCT and cart_items:
#             product_ids_in_cart = [item.item_id for item in cart_items if item.item_type == 'product']

#             # Match offer where item_ids overlap with cart product ids
#             query = query.filter(
#                 or_(
#                     OfferCondition.value["item_ids"].contains(product_ids_in_cart),  # Postgres JSONB contains operator
#                     OfferCondition.value["item_value"].in_(product_ids_in_cart)      # fallback if item_value is used instead
#                 )
#             )
        
#         if offer_type == OfferType.CART_VALUE_BASED and condition_type == OfferConditionType.CART_TOTAL and cart_total:
#             query = query.filter(
#                 or_(
#                     and_(
#                         OfferCondition.operator == "between",
#                         OfferCondition.value["min"].as_float() <= cart_total,
#                         OfferCondition.value["max"].as_float() >= cart_total,
#                     ),
#                     and_(
#                         OfferCondition.operator == "gte",
#                         OfferCondition.value["min"].as_float() <= cart_total,
#                     ),
#                     and_(
#                         OfferCondition.operator == "lte",
#                         OfferCondition.value["max"].as_float() >= cart_total,
#                     )
#                 )
#             )

#         if offer_type == OfferType.TIME_LIMITED and condition_type == OfferConditionType.TIME_WINDOW:
#             now = datetime.now(timezone.utc)

#             query = query.filter(
#                 and_(
#                     OfferCondition.value["start_datetime"].astext.cast(DateTime) <= now,
#                     OfferCondition.value["end_datetime"].astext.cast(DateTime) >= now,
#                 )
#             )
            
#         return query.order_by(Offer.created_at.desc()).scalar()
        
#     # Priority 1: First Order Offer
#     if is_first_order:
#         offer_id = get_applicable_offer(OfferType.CUSTOMER_BASED,OfferConditionType.FIRST_ORDER)

#     # Priority 2: Buy X Get Y on Product
#     if is_auto_apply and offer_id is None:
#         offer_id = get_applicable_offer(OfferType.BUY_X_GET_Y,OfferConditionType.PRODUCT,cart_items=cart_items)
    
#     # Priority 3: Cart Value Based
#     if is_auto_apply and offer_id is None:
#         offer_id = get_applicable_offer(OfferType.CART_VALUE_BASED,OfferConditionType.CART_TOTAL,cart_total=total_cart_value)

#     # Priority 4: Time Limited Offer
#     if is_auto_apply and offer_id is None:
#         offer_id = get_applicable_offer(OfferType.TIME_LIMITED,OfferConditionType.TIME_WINDOW)

#     if is_auto_apply and  offer_id is None:
#         raise ValueError("No applicable offer found")
    
#     if not is_auto_apply and offer_id is not None:
#         offer = db.query(Offer).filter(Offer.id == offer_id).first()
#         if not check_offer_applicable(offer, cart_items, total_cart_value, cart.business_contact_id, now=datetime.now(timezone.utc)):
#             raise ValueError("Selected offer is not applicable to this cart.")

# def check_offer_applicable(
#     offer: Offer,
#     cart_items: list,
#     cart_total: float,
#     business_contact_id: UUID,
#     now: datetime,
# ) -> bool:
#     if not offer.is_active:
#         return False

#     condition = offer.condition[0]
#     offer_type = OfferType(offer.offer_type)
#     condition_type = OfferConditionType(condition.condition_type)
#     value = condition.value or {}
#     operator = condition.operator

#     # === 1. Flat / Percentage Discount on Cart Total ===
#     if offer_type == OfferType.FLAT_DISCOUNT and condition_type == OfferConditionType.CART_TOTAL:
#         if not cart_total:
#             return False
#         return check_numeric_operator(operator, cart_total, value)

#     # === 2. Flat / Percentage Discount on Product ===
#     if offer_type == OfferType.PERCENTAGE_DISCOUNT and condition_type in [OfferConditionType.PRODUCT,OfferConditionType.SERVICE,OfferConditionType.CATEGORY,OfferConditionType.CART_TOTAL]:
#         value_data = value
#         target_type = value_data.get("item_type")
#         item_ids = value_data.get("item_ids", [])
#         item_value = value_data.get("item_value")

#         if condition_type == OfferConditionType.CART_TOTAL:
#             return check_numeric_operator(operator, cart_total, value)

#         if operator in ("in", "not_in"):
#             # Match any item in cart based on item_type and item_id
#             match_found = any(
#                 str(item.item_type) == target_type and str(item.item_id) in item_ids
#                 for item in cart_items
#             )
#             return match_found if operator == "in" else not match_found

#         elif operator == "equal":
#             # Check if any item in cart matches specific item_id
#             return any(
#                 str(item.item_type) == target_type and str(item.item_id) == str(item_value)
#                 for item in cart_items
#             )

#     # === 3. Cart Value Based: Cart Total ===
#     if offer_type == OfferType.CART_VALUE_BASED and condition_type == OfferConditionType.CART_TOTAL:
#         return check_numeric_operator(operator, cart_total, value)

#     # === 4. Cart Value Based: Product ===
#     if offer_type == OfferType.CART_VALUE_BASED and condition_type == OfferConditionType.PRODUCT:
#         product_ids = value.get("product_ids", [])
#         return any(str(item.product_id) in product_ids for item in cart_items)

#     # === 5. Cart Value Based: Payment Method ===
#     if offer_type == OfferType.CART_VALUE_BASED and condition_type == OfferConditionType.PAYMENT_METHOD:
#         return True  # Payment method to be validated later

#     # === 6. Buy X Get Y: Product ===
#     if offer_type == OfferType.BUY_X_GET_Y and condition_type == OfferConditionType.PRODUCT:
#         product_ids = value.get("product_ids", [])
#         min_qty = value.get("min_qty", 1)
#         for item in cart_items:
#             if str(item.product_id) in product_ids and item.quantity >= min_qty:
#                 return True
#         return False

#     # === 7. Bundle Pricing ===
#     if offer_type == OfferType.BUNDLE_PRICING and condition_type == OfferConditionType.PRODUCT:
#         bundle_products = value.get("product_ids", [])
#         bundle_set = set(bundle_products)
#         cart_set = set(str(item.product_id) for item in cart_items)
#         return bundle_set.issubset(cart_set)

#     # === 8. Time Limited: Product ===
#     if offer_type == OfferType.TIME_LIMITED and condition_type == OfferConditionType.PRODUCT:
#         product_ids = value.get("product_ids", [])
#         return any(str(item.product_id) in product_ids for item in cart_items)

#     # === 9. Time Limited: Time Window ===
#     if offer_type == OfferType.TIME_LIMITED and condition_type == OfferConditionType.TIME_WINDOW:
#         start = parse_datetime(value.get("start_datetime"))
#         end = parse_datetime(value.get("end_datetime"))
#         return start <= now <= end

#     # === 10. Customer Based: First Order ===
#     if offer_type == OfferType.CUSTOMER_BASED and condition_type == OfferConditionType.FIRST_ORDER:
#         return getattr(business_contact_id, "is_first_order", False)

#     # === 11. Customer Based: Contact Tag ===
#     if offer_type == OfferType.CUSTOMER_BASED and condition_type == OfferConditionType.CONTACT_TAG:
#         tag_ids = value.get("tag_ids", [])
#         return any(str(tag.id) in tag_ids for tag in getattr(user, "tags", []))

#     # === 12. Customer Based: Contact Group ===
#     if offer_type == OfferType.CUSTOMER_BASED and condition_type == OfferConditionType.CONTACT_GROUP:
#         group_ids = value.get("group_ids", [])
#         return any(str(group.id) in group_ids for group in getattr(user, "groups", []))

#     return False

# def check_numeric_operator(operator: str, cart_total: float, value: dict) -> bool:
#     if operator == "between":
#         return value.get("min", 0) <= cart_total <= value.get("max", float('inf'))
#     elif operator == "gte":
#         return cart_total >= value.get("min", 0)
#     elif operator == "lte":
#         return cart_total <= value.get("max", float('inf'))
#     return False

# def parse_datetime(dt_str):
#     if not dt_str:
#         return datetime.min.replace(tzinfo=timezone.utc)
#     return datetime.fromisoformat(dt_str)

def checkout_order(db: Session, cart_id:int,additional_discount:float = 0.0):
    try:
        # Step 1: Fetch the cart
        cart = db.query(Cart).filter(Cart.id == cart_id).first()
        if not cart:
            raise ValueError("Cart not found")

        # Step 2: Check for existing draft/pending order
        is_new_order = False
        existing_order = db.query(Order).filter(
            Order.cart_id == cart_id, Order.order_status == CartOrderStatus.PENDING
        ).first()

        if existing_order:
            order = existing_order
        else:
            order = Order(
                order_number=generate_order_number(cart.business_id),
                cart_id = cart_id,
                business_id=cart.business_id,
                business_contact_id=cart.business_contact_id,
                anonymous_id=cart.anonymous_id,
                source=cart.source,
                created_by_user_id=cart.created_by_user_id or None,
                order_status=CartOrderStatus.PENDING,
            )
            is_new_order = True
        # Step 3: Fetch cart items
        cart_items = db.query(CartItem).filter(CartItem.cart_id == cart.id).all()
        if not cart_items:
            raise ValueError("No items in cart to place order")

        # Step 4: Calculate amounts
        subtotal = sum(item.actual_price * item.quantity for item in cart_items)
        tax_total = sum((item.tax_amount or 0) * item.quantity for item in cart_items)

        delivery_fee = 0.0  # Placeholder for dynamic logic
        handling_fee = 0.0  # Placeholder for dynamic logic

        # Step 5: Assign pricing details
        order.subtotal = subtotal
        order.coupon_discount = cart.coupon_discount or 0.0
        order.offer_discount = cart.offer_discount or 0.0
        order.additional_discount = additional_discount or 0.0
        order.delivery_fee = delivery_fee
        order.handling_fee = handling_fee
        order.tax_total = tax_total

        order.total_amount = (
            subtotal
            - order.coupon_discount
            - order.offer_discount
            - order.additional_discount
            + tax_total
            + delivery_fee
            + handling_fee
        )

        # Step 6: Save the order
        if is_new_order:
            db.add(order)
        db.commit()
        db.refresh(order)

        return order
    except ValueError as ve:
        db.rollback()
        raise ValueError(str(ve))
    except Exception as e:
        db.rollback()
        raise Exception(str(e))  # Optional: convert to HTTPException if needed

def pay_now(db: Session, payload_list: List[PayNowRequest]):
    try:
        if not payload_list:
            raise ValueError("No payment data provided.")

        results = []
        # Validate order exists
        order = db.query(Order).filter(Order.id == payload_list[0].order_id).first()
        if not order:
            raise ValueError(f"Order ID {payload_list[0].order_id} not found.")
        for payload in payload_list:
            # Validate positive amount
            if payload.amount <= 0:
                raise ValueError(f"Amount must be greater than 0 for Order ID {payload.order_id}.")

            # Create payment entry
            payment = OrderPayment(
                order_id=payload.order_id,
                amount=payload.amount,
                payment_method=payload.payment_method,
                payment_gateway=payload.payment_gateway or None,
                payment_reference_id=payload.gateway_reference_id or None,
                gateway_status = payload.gateway_status or None,
                payment_status=payload.payment_status,
                is_manual_entry=payload.is_manual_entry or False,
                paid_at=datetime.now(timezone.utc),
                currency = 'INR'
            )
            if payload.payment_method == OrderPaymentMethod.CREDIT:
                # Create ledger DEBIT entry (i.e., customer paid amount)
                ledger_entry = BusinessContactLedger(
                    business_id=order.business_id,
                    business_contact_id=order.business_contact_id,
                    entry_type="debit",
                    amount=payload.amount,
                    payment_method=None,
                    notes= f"Credit entry from Order #{order.id}",
                )
                db.add(ledger_entry)
            db.add(payment)
            results.append(payment)

        order.order_status = CartOrderStatus.CONFIRMED
            
        # Commit all at once
        db.commit()

        return {
            "status": "success",
            "results": results,
            "message": "Payments recorded successfully."
        }
    except ValueError as ve:
        db.rollback()
        raise ValueError(str(ve))
    except Exception as e:
        db.rollback()
        raise Exception(str(e))  # Optional: convert to HTTPException if needed    

def place_order(db: Session,payload: PlaceOrderRequest):
    try:
        order = db.query(Order).filter(Order.id == payload.order_id).first()

        if not order:
            raise ValueError("Order not found")

        if order.order_status != CartOrderStatus.CONFIRMED:
            raise ValueError("Order is not in confirmed status")  # Pay-now must happen first

        # Step 1: If COD order, create OrderPayment entry
        if payload.is_cod_order:
            order.order_status = CartOrderStatus.PENDING
            cod_payment = OrderPayment(
                order_id=order.id,
                amount=order.total_payable_amount,
                payment_method=OrderPaymentMethod.COD,
                payment_status=OrderPaymentStatus.PENDING,
                is_manual_entry=False,
                currency="INR"
            )
            db.add(cod_payment)

            if payload.delivery_type and payload.address_line1:
                delivery = OrderDeliveryDetail(
                    order_id=order.id,
                    delivery_type=payload.delivery_type,
                    address_line1=payload.address_line1,
                    address_line2=payload.address_line2,
                    city=payload.city,
                    state=payload.state,
                    postal_code=payload.postal_code,
                    country=payload.country,
                    scheduled_date=payload.scheduled_date,
                    scheduled_time_slot=payload.scheduled_time_slot,
                    delivery_status="not_started",
                    delivery_notes=payload.delivery_notes,
                )
                db.add(delivery)

        # Step 2: Reduce stock (may raise ValueError)
        reduce_stock_for_order(db, order.id, order.cart_id)
        cart = db.query(Cart).filter(Cart.id == order.cart_id).first()
        if not cart:
            raise ValueError("Cart not found")
        # Step 4: Final order status update based on source & cod
        if order.source == CartOrderSource.BACK_OFFICE and not payload.is_cod_order:
            order.order_status = CartOrderStatus.COMPLETED
            cart.cart_status = CartStatus.COMPLETED
        elif order.source != CartOrderSource.BACK_OFFICE and not payload.is_cod_order:
            order.order_status = CartOrderStatus.PROCESSING
            cart.cart_status = CartOrderStatus.PROCESSING
        
        db.commit()
        db.refresh(order)

        return order

    except ValueError as ve:
        db.rollback()
        raise ValueError(str(ve))
    except Exception as e:
        db.rollback()
        raise Exception(str(e))  # Optional: convert to HTTPException if needed
    
def log_order_status_change(
    db: Session,
    order: Order,
    from_status: str,
    to_status: str,
    current_user: User,
    note_text: str
):
    status_log = OrderStatusLog(
        order_id=order.id,
        from_status=from_status,
        to_status=to_status,
        changed_by_user_id=current_user.id,
        changed_by_role=current_user.role,
        notes=note_text
    )
    db.add(status_log)

def log_order_action_if_terminal(
    db: Session,
    order: Order,
    status: str,
    reason: str,
    description: str,
    current_user: User
):
    if status not in [CartOrderStatus.CANCELLED, CartOrderStatus.COMPLETED]:
        return

    action_log = OrderActionLog(
        order_id=order.id,
        action_type=status,
        reason=reason,
        description=description,
        initiated_by_user_id=current_user.id,
        initiated_by_role=current_user.role,
        amount=order.total_amount,
        status="approved",
        approved_by_user_id=current_user.id
    )
    db.add(action_log)

def update_order_status_manually(db: Session,payload: OrderStatusUpdateRequest,current_user: User):
    order = db.query(Order).filter(Order.id == payload.order_id).first()
    if not order:
        raise ValueError("Order not found")

    if order.order_status == payload.new_status:
        raise ValueError(f"Order is already in '{payload.new_status}' status.")

    from_status = order.order_status
    order.order_status = payload.new_status

    # Fallbacks
    reason = payload.reason or "Manual status update"
    note_text = (
        payload.notes
        or f"{current_user.role.capitalize()} manually changed status from {from_status} to {payload.new_status}"
    )

    # Log status
    log_order_status_change(db, order, from_status, payload.new_status, current_user, note_text)

    # Log action if needed
    #log_order_action_if_terminal(db, order, payload.new_status, reason, note_text, current_user)

    db.commit()
    db.refresh(order)
    return order
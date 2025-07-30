"""Update Offer Module

Revision ID: d5891a077c70
Revises: 6d042b0bfccd
Create Date: 2025-07-29 18:54:52.471589

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5891a077c70'
down_revision: Union[str, None] = '6d042b0bfccd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # 1. Create ENUM types
    op.execute("CREATE TYPE offerconditiontype AS ENUM ('PRODUCT', 'SERVICE', 'CATEGORY', 'CART_TOTAL', 'CONTACT_TAG', 'FIRST_ORDER', 'CONTACT_GROUP', 'TIME_WINDOW', 'PAYMENT_METHOD')")
    op.execute("CREATE TYPE offertype AS ENUM ('FLAT_DISCOUNT', 'PERCENTAGE_DISCOUNT', 'BUY_X_GET_Y', 'BUNDLE_PRICING', 'CART_VALUE_BASED', 'CUSTOMER_BASED', 'TIME_LIMITED')")

    # 2. Add new columns using these ENUM types
    op.add_column('offer_conditions', sa.Column('condition_type', sa.Enum(name='offerconditiontype'), nullable=False))
    op.add_column('offers', sa.Column('offer_type', sa.Enum(name='offertype'), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_column('offers', 'offer_type')
    op.drop_column('offer_conditions', 'condition_type')

    # Drop the ENUM types
    op.execute("DROP TYPE offertype")
    op.execute("DROP TYPE offerconditiontype")

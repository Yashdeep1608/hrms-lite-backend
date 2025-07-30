"""Update Cart/Order Tables

Revision ID: 653dfe321252
Revises: 8df70738323c
Create Date: 2025-07-30 18:59:11.819415

"""
from typing import Sequence, Union
from sqlalchemy.dialects import postgresql
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '653dfe321252'
down_revision: Union[str, None] = '8df70738323c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Define the enum type with matching values (case-sensitive)
cartstatus_enum = postgresql.ENUM('ACTIVE', 'COMPLETED', 'ABANDONED', 'CANCELLED', name='cartstatus')

def upgrade() -> None:
    """Upgrade schema."""
    # Create the enum type in PostgreSQL
    cartstatus_enum.create(op.get_bind(), checkfirst=True)

    # Add the new column using the enum type
    op.add_column('carts', sa.Column('cart_status', cartstatus_enum, nullable=False, server_default='ACTIVE'))

    # Create index on the new column
    op.create_index(op.f('ix_carts_cart_status'), 'carts', ['cart_status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop the index
    op.drop_index(op.f('ix_carts_cart_status'), table_name='carts')

    # Drop the cart_status column
    op.drop_column('carts', 'cart_status')

    # Drop the enum type from PostgreSQL
    cartstatus_enum.drop(op.get_bind(), checkfirst=True)
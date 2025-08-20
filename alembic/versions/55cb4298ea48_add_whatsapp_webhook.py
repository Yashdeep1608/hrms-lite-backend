"""Add Whatsapp Webhook

Revision ID: 55cb4298ea48
Revises: c258004c1fe2
Create Date: 2025-08-20 18:26:44.455052

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '55cb4298ea48'
down_revision: Union[str, None] = 'c258004c1fe2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    # Use raw SQL with explicit cast to JSONB
    op.execute(
        """
        ALTER TABLE webhook_messages
        ALTER COLUMN payload TYPE JSONB USING payload::jsonb;
        """
    )

def downgrade() -> None:
    """Downgrade schema."""
    # Cast back from JSONB to TEXT with explicit cast
    op.execute(
        """
        ALTER TABLE webhook_messages
        ALTER COLUMN payload TYPE TEXT USING payload::text;
        """
    )
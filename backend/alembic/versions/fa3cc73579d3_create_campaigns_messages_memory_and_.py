"""create campaigns messages memory and srd chunks

Revision ID: fa3cc73579d3
Revises: 60153821f4ca
Create Date: 2026-11-16 16:44:50.288570

"""
from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'fa3cc73579d3'
down_revision: str | Sequence[str] | None = '60153821f4ca'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        'campaigns',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('character_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['character_id'], ['characters.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_campaigns_character_id'), 'campaigns', ['character_id'], unique=False)
    op.create_index(op.f('ix_campaigns_user_id'), 'campaigns', ['user_id'], unique=False)

    op.create_table(
        'campaign_memories',
        sa.Column('campaign_id', sa.UUID(), nullable=False),
        sa.Column(
            'summary',
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text(
                """'{"facts": [], "goals": [], "npcs": [], "locations": [], "open_threads": []}'::jsonb"""
            ),
            nullable=False,
        ),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('campaign_id'),
    )

    op.create_table(
        'campaign_messages',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('campaign_id', sa.UUID(), nullable=False),
        sa.Column('role', sa.String(length=16), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('client_message_id', sa.String(length=64), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("role IN ('user', 'assistant')", name='ck_campaign_messages_role'),
        sa.CheckConstraint('sequence > 0', name='ck_campaign_messages_sequence_positive'),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('campaign_id', 'client_message_id', name='uq_campaign_messages_campaign_client_message'),
        sa.UniqueConstraint('campaign_id', 'sequence', name='uq_campaign_messages_campaign_sequence'),
    )
    op.create_index(op.f('ix_campaign_messages_campaign_id'), 'campaign_messages', ['campaign_id'], unique=False)

    op.create_table(
        'srd_chunks',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('chunk_key', sa.String(length=64), nullable=False),
        sa.Column('source', sa.String(length=200), nullable=False),
        sa.Column('section', sa.String(length=200), nullable=False),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(1536), nullable=False),
        sa.Column('license', sa.String(length=50), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_srd_chunks_chunk_key'), 'srd_chunks', ['chunk_key'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_srd_chunks_chunk_key'), table_name='srd_chunks')
    op.drop_table('srd_chunks')
    op.drop_index(op.f('ix_campaign_messages_campaign_id'), table_name='campaign_messages')
    op.drop_table('campaign_messages')
    op.drop_table('campaign_memories')
    op.drop_index(op.f('ix_campaigns_user_id'), table_name='campaigns')
    op.drop_index(op.f('ix_campaigns_character_id'), table_name='campaigns')
    op.drop_table('campaigns')

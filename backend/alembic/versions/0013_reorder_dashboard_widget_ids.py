# backend/alembic/versions/0013_reorder_dashboard_widget_ids.py
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE reports
        SET widgets =
            (widgets - ARRAY[
                'w1', 'w2', 'w3', 'w4', 'w5', 'w6', 'w7',
                'w8', 'w9', 'w10', 'w11', 'w12', 'w13', 'w14'
            ]::text[])
            || COALESCE(
                (
                    SELECT jsonb_object_agg(new_key, widget_value)
                    FROM (
                        VALUES
                            ('w1', widgets->'w1'),
                            ('w2', widgets->'w2'),
                            ('w3', widgets->'w3'),
                            ('w4', widgets->'w4'),
                            ('w5', widgets->'w5'),
                            ('w6', widgets->'w6'),
                            ('w7', widgets->'w12'),
                            ('w8', widgets->'w13'),
                            ('w9', widgets->'w14'),
                            ('w10', widgets->'w7'),
                            ('w11', widgets->'w8'),
                            ('w12', widgets->'w9'),
                            ('w13', widgets->'w10'),
                            ('w14', widgets->'w11')
                    ) AS remapped(new_key, widget_value)
                    WHERE widget_value IS NOT NULL
                ),
                '{}'::jsonb
            )
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE reports
        SET widgets =
            (widgets - ARRAY[
                'w1', 'w2', 'w3', 'w4', 'w5', 'w6', 'w7',
                'w8', 'w9', 'w10', 'w11', 'w12', 'w13', 'w14'
            ]::text[])
            || COALESCE(
                (
                    SELECT jsonb_object_agg(old_key, widget_value)
                    FROM (
                        VALUES
                            ('w1', widgets->'w1'),
                            ('w2', widgets->'w2'),
                            ('w3', widgets->'w3'),
                            ('w4', widgets->'w4'),
                            ('w5', widgets->'w5'),
                            ('w6', widgets->'w6'),
                            ('w7', widgets->'w10'),
                            ('w8', widgets->'w11'),
                            ('w9', widgets->'w12'),
                            ('w10', widgets->'w13'),
                            ('w11', widgets->'w14'),
                            ('w12', widgets->'w7'),
                            ('w13', widgets->'w8'),
                            ('w14', widgets->'w9')
                    ) AS remapped(old_key, widget_value)
                    WHERE widget_value IS NOT NULL
                ),
                '{}'::jsonb
            )
        """
    )

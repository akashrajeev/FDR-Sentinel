from alembic import context
from sentinel import models  # noqa: F401
from sentinel.db import Base, engine

with engine().connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()

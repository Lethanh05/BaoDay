from sqlalchemy import MetaData, inspect, select
from sqlalchemy.engine import Connection
from sqlalchemy.schema import CreateIndex, CreateTable

from app.db.base import Base
from app.db.session import engine
from app.models.article import Article
from app.models.file import StoredFile
from app.models.user import User


def initialize_database() -> None:
    with engine.begin() as connection:
        if connection.dialect.name == "sqlite":
            # SQLite's legacy transaction mode does not begin on DDL.
            connection.exec_driver_sql("BEGIN IMMEDIATE")
        Base.metadata.create_all(connection)
        if connection.dialect.name == "sqlite":
            _add_cover_foreign_key(connection)


def _add_cover_foreign_key(connection: Connection) -> None:
    table = Article.__table__
    constraints = inspect(connection).get_foreign_keys(table.name)
    if any(
        item["constrained_columns"] == ["cover_file_id"] and item["referred_table"] == "files"
        for item in constraints
    ):
        return

    # Rebuild the schema from the article-only version without changing article IDs.
    metadata = MetaData()
    User.__table__.to_metadata(metadata)
    StoredFile.__table__.to_metadata(metadata)
    replacement = table.to_metadata(metadata, name="articles_with_cover_fk")
    connection.execute(CreateTable(replacement))
    valid_cover_id = (
        select(StoredFile.id).where(StoredFile.id == table.c.cover_file_id).scalar_subquery()
    )
    values = [valid_cover_id if column.name == "cover_file_id" else column for column in table.c]
    connection.execute(replacement.insert().from_select(table.c.keys(), select(*values)))
    connection.exec_driver_sql("DROP TABLE articles")
    connection.exec_driver_sql("ALTER TABLE articles_with_cover_fk RENAME TO articles")
    for index in table.indexes:
        connection.execute(CreateIndex(index))
    if connection.exec_driver_sql("PRAGMA foreign_key_check(articles)").first():
        raise RuntimeError("The article cover migration produced an invalid foreign key.")

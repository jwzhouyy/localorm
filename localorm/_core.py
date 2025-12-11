# coding: utf-8

import time
import logging

from typing import Any, Optional, TypeVar, Generic
from dataclasses import is_dataclass, asdict

from pydantic import BaseModel
from sqlmodel import Field, SQLModel, create_engine, Session, select
from sqlalchemy import func, inspect, text
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from sqlalchemy.types import TypeDecorator, JSON


class PydanticJSON(TypeDecorator):
    impl = JSON
    cache_ok = True

    def __init__(self, model: type[BaseModel], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = model

    def process_bind_param(self, value: BaseModel, dialect):
        if isinstance(value, BaseModel):
            return value.model_dump()
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return self.model(**value)


class DataClassJSON(TypeDecorator):
    impl = JSON
    cache_ok = True

    def __init__(self, model):
        super().__init__()
        self.model = model

    def process_bind_param(self, value, dialect):
        if is_dataclass(value):
            return asdict(value)
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return self.model(**value)


def PydanticField(model: type[BaseModel], default=None):
    return Field(default=default, sa_type=PydanticJSON(model))


def DataclassField(model, default=None):
    return Field(default=default, sa_type=DataClassJSON(model))


class ORMModel(SQLModel):
    id: int = Field(default=None, primary_key=True)
    create_time: int | None = None


ModelT = TypeVar('ModelT', bound=ORMModel)


class DataBase(Generic[ModelT]):
    ModelClass: ModelT

    def __init__(self, save_path: str):
        if not hasattr(self, 'ModelClass') or self.ModelClass is None:
            raise NotImplementedError(
                f'{self.__class__.__name__} must override `ModelClass` with a SQLModel subclass'
            )
        assert issubclass(self.ModelClass, SQLModel), 'ModelClass must be a SQLModel subclass'

        self.engine = create_engine(
            f'sqlite:///{save_path}',
            echo=False,
            connect_args={
                'check_same_thread': False,
                'timeout': 30,
            },
            pool_pre_ping=True,
        )
        # --- WAL 模式 ---
        # with self.engine.connect() as conn:
        #     conn.execute(text('PRAGMA journal_mode=WAL;'))
        #     conn.execute(text('PRAGMA synchronous=NORMAL;'))

        SQLModel.metadata.create_all(self.engine)
        self._sync_table()

    def _get_session(self) -> Session:
        return Session(self.engine)

    def _sync_table(self):
        table_name = self.ModelClass.__tablename__

        with self.engine.connect() as conn:
            inspector = inspect(conn)
            existing_tables = inspector.get_table_names()

            if table_name not in existing_tables:
                SQLModel.metadata.create_all(self.engine)
                return

            db_columns = {col['name'] for col in inspector.get_columns(table_name)}
            model_columns = set(self.ModelClass.model_fields.keys())

            added = model_columns - db_columns
            removed = db_columns - model_columns

            if not added and not removed:
                return

            # Add new fields
            for name in added:
                field = self.ModelClass.model_fields[name]
                sql_type = self._map_python_type_to_sql(field.annotation)
                sql = f'ALTER TABLE {table_name} ADD COLUMN {name} {sql_type}'
                conn.execute(text(sql))

            # Remove fields -> rebuild table
            if removed:
                logging.getLogger(__name__).info(
                    f'⚠️ Detected field deletion: %s, rebuilding table %s...', removed, table_name
                )
                self._rebuild_table(conn, table_name, model_columns)
            conn.commit()

    def _map_python_type_to_sql(self, py_type: Any) -> str:
        if isinstance(py_type, type) and issubclass(py_type, (dict, list)):
            return 'JSON'
        if py_type in (int, Optional[int]):
            return 'INTEGER'
        elif py_type in (float, Optional[float]):
            return 'REAL'
        elif py_type in (bool, Optional[bool]):
            return 'INTEGER'
        else:
            return 'TEXT'

    def _rebuild_table(self, conn, table_name: str, model_columns: set[str]):
        """
        Rebuild table structure: create new table structure, migrate data, swap tables through renaming
        """
        # Generate temporary table name with timestamp
        timestamp = int(time.time() * 1000)
        temp_table_name = f'{table_name}_{timestamp}'
        logging.getLogger(__name__).info('Temporary table name: %s', temp_table_name)
        try:
            # Start transaction
            conn.execute(text('BEGIN TRANSACTION'))

            # 1. Create new table structure using SQLModel (with temporary table name)
            # Temporarily modify table name to create new structure
            original_table_name = None
            for table in SQLModel.metadata.tables.values():
                if table.name == table_name:
                    original_table_name = table.name
                    table.name = temp_table_name
                    break

            # 创建新表结构
            SQLModel.metadata.create_all(self.engine)

            # Restore original table name (avoid affecting subsequent operations)
            if original_table_name:
                for table in SQLModel.metadata.tables.values():
                    if table.name == temp_table_name:
                        table.name = original_table_name
                        break

            # 2. Copy data from old table to new table
            # Build column name list (ensure consistent order)
            columns_str = ', '.join([col for col in model_columns])

            # Copy data to new table
            copy_sql = f"""
            INSERT INTO {temp_table_name} ({columns_str})
            SELECT {columns_str} FROM {table_name}
            """
            conn.execute(text(copy_sql))
            # 3. Atomic table name swap
            # First rename old table (backup)
            old_table_backup = f'{table_name}_old_{timestamp}'
            conn.execute(text(f'ALTER TABLE {table_name} RENAME TO {old_table_backup}'))

            # Then rename new table to target table name
            conn.execute(text(f'ALTER TABLE {temp_table_name} RENAME TO {table_name}'))

            # Commit transaction
            conn.commit()

            # 4. 清理旧表（在事务外执行，避免事务过大）
            try:
                conn.execute(text(f'DROP TABLE {old_table_backup}'))
                logging.getLogger(__name__).info(
                    '✅ Table %s successfully rebuilt, old table cleaned up', table_name
                )
            except Exception as cleanup_error:
                logging.getLogger(__name__).warning(
                    '⚠️ New table ready, but failed to clean up old table: %s', cleanup_error
                )
                # This doesn't affect main functionality, can be cleaned up manually later

            logging.getLogger(__name__).info(
                '✅ Table %s rebuild complete, data migrated to new structure', table_name
            )
        except Exception as e:
            # Rollback transaction
            conn.rollback()
            logging.getLogger(__name__).error(
                '❌ Table rebuild failed: %s, all changes rolled back', str(e)
            )
        finally:
            # 清理可能创建的临时表
            conn.execute(text(f'DROP TABLE IF EXISTS {temp_table_name}'))

    # ============================================================
    # CRUD
    # ============================================================

    def add_model(self, data: dict[str, Any]) -> ModelT:
        with self._get_session() as session:
            # ✅ Only keep fields defined in the model
            valid_keys = set(self.ModelClass.model_fields.keys())
            data = {k: v for k, v in data.items() if k in valid_keys}
            if 'create_time' not in data:
                data['create_time'] = int(time.time())
            obj = self.ModelClass(**data)
            session.add(obj)
            session.commit()
            session.refresh(obj)
            return obj

    def add_models(self, data_list: list[dict[str, Any]]) -> list[ModelT]:
        batch_size = 10000
        objects = []
        with self._get_session() as session:
            valid_keys = set(self.ModelClass.model_fields.keys())
            for i in range(0, len(data_list), batch_size):
                batch = data_list[i : i + batch_size]
                logging.getLogger(__name__).info(
                    'Batch Add [%s:%s] %s/%s, %.4g%%',
                    i,
                    i + batch_size - 1,
                    i,
                    len(data_list),
                    i / len(data_list),
                )
                batch_objects = []
                for data in batch:
                    data = {k: v for k, v in data.items() if k in valid_keys}
                    if 'create_time' not in data:
                        data['create_time'] = int(time.time())
                    obj = self.ModelClass(**data)
                    session.add(obj)
                    batch_objects.append(obj)
                session.commit()
                for obj in batch_objects:
                    session.refresh(obj)
                objects.extend(batch_objects)
            return objects

    def add_model_or_ignore(self, data: dict[str, Any]) -> ModelT | None:
        with self._get_session() as session:
            valid_keys = set(self.ModelClass.model_fields.keys())
            data = {k: v for k, v in data.items() if k in valid_keys}
            if 'create_time' not in data:
                data['create_time'] = int(time.time())
            stmt = sqlite_insert(self.ModelClass).values(**data)
            stmt = stmt.prefix_with('OR IGNORE')
            result = session.execute(stmt)
            session.commit()

            if result.rowcount == 0:
                return None

            pk_name = self.ModelClass.__mapper__.primary_key[0].name
            pk_value = data.get(pk_name)
            if pk_value is None:
                pk_value = session.execute(text('SELECT last_insert_rowid()')).scalar()

            return session.get(self.ModelClass, pk_value)

    def delete_model_by_ids(self, ids: list[int]) -> int:
        with self._get_session() as session:
            stmt = select(self.ModelClass).where(self.ModelClass.id.in_(ids))
            results = session.exec(stmt).all()
            count = len(results)
            for item in results:
                session.delete(item)
            session.commit()
            return count

    def delete_model_by_id(self, id: int) -> bool:
        return self.delete_model_by_ids([id]) > 0

    def update_model_by_id(self, id: int, data: dict[str, Any]) -> ModelT | None:
        with self._get_session() as session:
            obj = session.get(self.ModelClass, id)
            if not obj:
                return None
            for k, v in data.items():
                if hasattr(obj, k):
                    setattr(obj, k, v)
            session.add(obj)
            session.commit()
            session.refresh(obj)
            return obj

    def get_models_by_ids(self, ids: list[int]) -> dict[int, ModelT]:
        with self._get_session() as session:
            stmt = select(self.ModelClass).where(self.ModelClass.id.in_(ids))
            results = session.exec(stmt).all()
            return {obj.id: obj for obj in results}

    def get_model_by_id(self, id: int) -> ModelT | None:
        with self._get_session() as session:
            return session.get(self.ModelClass, id)

    def get_all_models(self, reverse: bool = False) -> list[ModelT]:
        with self._get_session() as session:
            stmt = select(self.ModelClass).order_by(
                self.ModelClass.id.desc() if reverse else self.ModelClass.id.asc()
            )
            results = session.exec(stmt).all()
            return results

    def iter_all_models(self, reverse: bool = False):
        yield from self.get_all_models(reverse=reverse)

    def get_count(self) -> int:
        with self._get_session() as session:
            stmt = select(func.count()).select_from(self.ModelClass)
            result = session.exec(stmt).one()
            return result

    def print_all(self, reverse=True):
        for u in self.get_all_models(reverse=reverse):
            print(u)

# coding: utf-8
import pytest
import tempfile
import os
from typing import Optional, List, Dict, Any
from pathlib import Path
from sqlmodel import SQLModel, Field
from sqlalchemy import UniqueConstraint

from localorm import DataBase


# ============================================================
# Test Models
# ============================================================

class BasicModel(SQLModel, table=True):
    __tablename__ = 'basic_model'

    id: int = Field(default=None, primary_key=True)
    name: str | None = None
    age: int | None = None


class ExtendedModel(SQLModel, table=True):
    __tablename__ = 'extended_model'

    id: int = Field(default=None, primary_key=True)
    name: str | None = None
    age: int | None = None
    email: str | None = None  # New field


class ReducedModel(SQLModel, table=True):
    __tablename__ = 'reduced_model'

    id: int = Field(default=None, primary_key=True)
    name: str | None = None
    # age field removed


class TypeTestModel(SQLModel, table=True):
    __tablename__ = 'type_test_model'

    id: int = Field(default=None, primary_key=True)
    int_field: int | None = None
    float_field: float | None = None
    bool_field: bool | None = None
    str_field: str | None = None


class UniqueModel(SQLModel, table=True):
    __tablename__ = 'unique_model'
    __table_args__ = (UniqueConstraint('key1', 'key2', name='uq_keys'),)

    id: int = Field(default=None, primary_key=True)
    key1: int | None = None
    key2: int | None = None
    value: str | None = None


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def temp_db():
    """Create a temporary database file"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    # Cleanup
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def basic_db(temp_db):
    """Create a basic DataBase instance"""
    return DataBase[BasicModel](BasicModel, temp_db)


@pytest.fixture
def populated_db(basic_db):
    """Create a database with some initial data"""
    basic_db.add_model({'name': 'Alice', 'age': 30})
    basic_db.add_model({'name': 'Bob', 'age': 25})
    basic_db.add_model({'name': 'Charlie', 'age': 35})
    return basic_db


# ============================================================
# 1. Initialization Tests
# ============================================================

class TestInitialization:
    def test_database_initialization_success(self, temp_db):
        """Test database initializes successfully"""
        db = DataBase[BasicModel](BasicModel, temp_db)
        assert db.model_class == BasicModel
        assert db.engine is not None
        assert os.path.exists(temp_db)

    def test_table_auto_creation(self, temp_db):
        """Test table is automatically created"""
        db = DataBase[BasicModel](BasicModel, temp_db)
        count = db.get_count()
        assert count == 0

    def test_multiple_initialization_same_db(self, temp_db):
        """Test multiple initializations of the same database"""
        db1 = DataBase[BasicModel](BasicModel, temp_db)
        db1.add_model({'name': 'Test', 'age': 20})

        db2 = DataBase[BasicModel](BasicModel, temp_db)
        count = db2.get_count()
        assert count == 1


# ============================================================
# 2. Table Sync Tests
# ============================================================

class TestTableSync:
    def test_add_new_field(self, temp_db):
        """Test new field is automatically added to table"""
        # First create with BasicModel
        db1 = DataBase[BasicModel](BasicModel, temp_db)
        db1.add_model({'name': 'Test', 'age': 20})

        # Then create with ExtendedModel (has email field)
        db2 = DataBase[ExtendedModel](ExtendedModel, temp_db)
        model = db2.add_model({'name': 'Test2', 'age': 25, 'email': 'test@test.com'})

        assert model.email == 'test@test.com'
        assert db2.get_count() == 2

    def test_remove_field_triggers_rebuild(self, temp_db):
        """Test field removal triggers table rebuild"""
        # First create with BasicModel
        db1 = DataBase[BasicModel](BasicModel, temp_db)
        db1.add_model({'name': 'Test', 'age': 20})

        # Then create with ReducedModel (age field removed)
        db2 = DataBase[ReducedModel](ReducedModel, temp_db)

        # Data should still be there
        assert db2.get_count() == 1
        model = db2.get_model_by_id(1)
        assert model.name == 'Test'

    def test_no_change_no_sync(self, temp_db):
        """Test no sync when no field changes"""
        db1 = DataBase[BasicModel](BasicModel, temp_db)
        db1.add_model({'name': 'Test', 'age': 20})

        # Create another instance with same model
        db2 = DataBase[BasicModel](BasicModel, temp_db)
        assert db2.get_count() == 1


# ============================================================
# 3. Type Mapping Tests
# ============================================================

class TestTypeMapping:
    def test_type_mapping(self, temp_db):
        """Test Python type to SQL type mapping"""
        db = DataBase[TypeTestModel](TypeTestModel, temp_db)

        model = db.add_model({
            'int_field': 42,
            'float_field': 3.14,
            'bool_field': True,
            'str_field': 'test'
        })

        retrieved = db.get_model_by_id(model.id)
        assert retrieved.int_field == 42
        assert abs(retrieved.float_field - 3.14) < 0.001
        assert retrieved.bool_field == True
        assert retrieved.str_field == 'test'


# ============================================================
# 4. Add Single Model Tests
# ============================================================

class TestAddModel:
    def test_add_model_success(self, basic_db):
        """Test normal model addition"""
        model = basic_db.add_model({'name': 'Test', 'age': 25})

        assert model.id is not None
        assert model.name == 'Test'
        assert model.age == 25

    def test_add_model_filters_invalid_fields(self, basic_db):
        """Test invalid fields are filtered out"""
        model = basic_db.add_model({
            'name': 'Test',
            'age': 25,
            'invalid_field': 'should be ignored'
        })

        assert model.name == 'Test'
        assert model.age == 25
        assert not hasattr(model, 'invalid_field')

    def test_add_model_auto_increment_id(self, basic_db):
        """Test auto-increment primary key"""
        model1 = basic_db.add_model({'name': 'Test1'})
        model2 = basic_db.add_model({'name': 'Test2'})

        assert model2.id == model1.id + 1

    def test_add_model_partial_fields(self, basic_db):
        """Test adding model with only some fields"""
        model = basic_db.add_model({'name': 'Test'})

        assert model.name == 'Test'
        assert model.age is None


# ============================================================
# 5. Add Multiple Models Tests
# ============================================================

class TestAddModels:
    def test_add_models_success(self, basic_db):
        """Test batch addition success"""
        data_list = [
            {'name': 'User1', 'age': 20},
            {'name': 'User2', 'age': 25},
            {'name': 'User3', 'age': 30}
        ]

        models = basic_db.add_models(data_list)

        assert len(models) == 3
        assert all(m.id is not None for m in models)

    def test_add_models_empty_list(self, basic_db):
        """Test adding empty list"""
        models = basic_db.add_models([])
        assert len(models) == 0

    def test_add_models_large_batch(self, basic_db):
        """Test large batch (>10000) triggers batching"""
        data_list = [{'name': f'User{i}', 'age': i % 100} for i in range(15000)]

        models = basic_db.add_models(data_list)

        assert len(models) == 15000
        assert basic_db.get_count() == 15000

    def test_add_models_filters_invalid_fields(self, basic_db):
        """Test invalid fields are filtered in batch add"""
        data_list = [
            {'name': 'User1', 'age': 20, 'invalid': 'field'},
            {'name': 'User2', 'age': 25, 'invalid': 'field'}
        ]

        models = basic_db.add_models(data_list)

        assert len(models) == 2
        assert all(not hasattr(m, 'invalid') for m in models)


# ============================================================
# 6. Add or Ignore Tests
# ============================================================

class TestAddOrIgnore:
    def test_add_or_ignore_new_record(self, temp_db):
        """Test new record is inserted"""
        db = DataBase[UniqueModel](UniqueModel, temp_db)

        model = db.add_model_or_ignore({'key1': 1, 'key2': 2, 'value': 'test'})

        assert model is not None
        assert model.value == 'test'

    def test_add_or_ignore_duplicate_returns_none(self, temp_db):
        """Test duplicate record returns None"""
        db = DataBase[UniqueModel](UniqueModel, temp_db)

        db.add_model_or_ignore({'key1': 1, 'key2': 2, 'value': 'test1'})
        result = db.add_model_or_ignore({'key1': 1, 'key2': 2, 'value': 'test2'})

        assert result is None
        assert db.get_count() == 1

    def test_add_or_ignore_filters_invalid_fields(self, temp_db):
        """Test invalid fields are filtered"""
        db = DataBase[UniqueModel](UniqueModel, temp_db)

        model = db.add_model_or_ignore({
            'key1': 1,
            'key2': 2,
            'value': 'test',
            'invalid': 'field'
        })

        assert model is not None
        assert not hasattr(model, 'invalid')


# ============================================================
# 7. Delete Tests
# ============================================================

class TestDelete:
    def test_delete_existing_model(self, populated_db):
        """Test deleting existing record"""
        result = populated_db.delete_model_by_id(1)

        assert result == True
        assert populated_db.get_count() == 2

    def test_delete_non_existing_model(self, populated_db):
        """Test deleting non-existing record returns False"""
        result = populated_db.delete_model_by_id(999)

        assert result == False
        assert populated_db.get_count() == 3

    def test_delete_multiple_models(self, populated_db):
        """Test batch deletion"""
        count = populated_db.delete_model_by_ids([1, 2])

        assert count == 2
        assert populated_db.get_count() == 1

    def test_delete_empty_list(self, populated_db):
        """Test deleting empty list"""
        count = populated_db.delete_model_by_ids([])

        assert count == 0
        assert populated_db.get_count() == 3

    def test_delete_partial_existing_ids(self, populated_db):
        """Test deleting mix of existing and non-existing IDs"""
        count = populated_db.delete_model_by_ids([1, 999, 2])

        assert count == 2
        assert populated_db.get_count() == 1


# ============================================================
# 8. Update Tests
# ============================================================

class TestUpdate:
    def test_update_existing_model(self, populated_db):
        """Test updating existing record"""
        updated = populated_db.update_model_by_id(1, {'name': 'Updated', 'age': 40})

        assert updated is not None
        assert updated.name == 'Updated'
        assert updated.age == 40

    def test_update_non_existing_model(self, populated_db):
        """Test updating non-existing record returns None"""
        result = populated_db.update_model_by_id(999, {'name': 'Test'})

        assert result is None

    def test_update_specific_fields_only(self, populated_db):
        """Test only specified fields are updated"""
        original = populated_db.get_model_by_id(1)
        updated = populated_db.update_model_by_id(1, {'name': 'Updated'})

        assert updated.name == 'Updated'
        assert updated.age == original.age

    def test_update_ignores_invalid_fields(self, populated_db):
        """Test invalid fields are ignored"""
        updated = populated_db.update_model_by_id(1, {
            'name': 'Updated',
            'invalid_field': 'should be ignored'
        })

        assert updated.name == 'Updated'
        assert not hasattr(updated, 'invalid_field')


# ============================================================
# 9. Get Model(s) Tests
# ============================================================

class TestGetModels:
    def test_get_existing_model_by_id(self, populated_db):
        """Test retrieving existing single record"""
        model = populated_db.get_model_by_id(1)

        assert model is not None
        assert model.name == 'Alice'

    def test_get_non_existing_model(self, populated_db):
        """Test retrieving non-existing record returns None"""
        model = populated_db.get_model_by_id(999)

        assert model is None

    def test_get_models_by_ids_returns_dict(self, populated_db):
        """Test batch retrieval returns dict"""
        models = populated_db.get_models_by_ids([1, 2])

        assert isinstance(models, dict)
        assert len(models) == 2
        assert 1 in models
        assert 2 in models

    def test_get_models_by_empty_list(self, populated_db):
        """Test batch retrieval with empty list"""
        models = populated_db.get_models_by_ids([])

        assert isinstance(models, dict)
        assert len(models) == 0

    def test_get_models_partial_existing_ids(self, populated_db):
        """Test batch retrieval with partial existing IDs"""
        models = populated_db.get_models_by_ids([1, 999, 2])

        assert len(models) == 2
        assert 1 in models
        assert 2 in models
        assert 999 not in models


# ============================================================
# 10. Get All Models Tests
# ============================================================

class TestGetAllModels:
    def test_get_all_from_empty_table(self, basic_db):
        """Test get all from empty table"""
        models = basic_db.get_all_models()

        assert isinstance(models, list)
        assert len(models) == 0

    def test_get_all_with_data(self, populated_db):
        """Test get all with data"""
        models = populated_db.get_all_models()

        assert len(models) == 3
        assert all(isinstance(m, BasicModel) for m in models)


# ============================================================
# 11. Count Tests
# ============================================================

class TestCount:
    def test_count_empty_table(self, basic_db):
        """Test count on empty table"""
        count = basic_db.get_count()
        assert count == 0

    def test_count_with_data(self, populated_db):
        """Test count with data"""
        count = populated_db.get_count()
        assert count == 3

    def test_count_after_operations(self, basic_db):
        """Test count after various operations"""
        basic_db.add_model({'name': 'Test1'})
        assert basic_db.get_count() == 1

        basic_db.add_models([{'name': 'Test2'}, {'name': 'Test3'}])
        assert basic_db.get_count() == 3

        basic_db.delete_model_by_id(1)
        assert basic_db.get_count() == 2


# ============================================================
# 12. Print All Tests
# ============================================================

class TestPrintAll:
    def test_print_all_no_error(self, populated_db, capsys):
        """Test print_all doesn't raise error"""
        populated_db.print_all()

        captured = capsys.readouterr()
        assert 'Alice' in captured.out
        assert 'Bob' in captured.out
        assert 'Charlie' in captured.out


# ============================================================
# 13. Edge Cases and Error Handling
# ============================================================

class TestEdgeCases:
    def test_database_path_with_tilde(self):
        """Test database path with ~ expansion"""
        temp_dir = tempfile.mkdtemp()
        db_name = 'test.db'

        # Create a path that will work
        db_path = os.path.join(temp_dir, db_name)

        db = DataBase[BasicModel](BasicModel, db_path)
        db.add_model({'name': 'Test'})

        assert db.get_count() == 1

        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
        os.rmdir(temp_dir)

    def test_session_closes_properly(self, basic_db):
        """Test session closes properly after operations"""
        # Perform multiple operations
        for i in range(10):
            basic_db.add_model({'name': f'Test{i}'})

        # Should not have leaked connections
        assert basic_db.get_count() == 10

    def test_none_values_handling(self, basic_db):
        """Test handling None values"""
        model = basic_db.add_model({'name': None, 'age': None})

        assert model.name is None
        assert model.age is None

    def test_empty_string_vs_none(self, basic_db):
        """Test empty string vs None"""
        model1 = basic_db.add_model({'name': '', 'age': 0})
        model2 = basic_db.add_model({'name': None, 'age': None})

        assert model1.name == ''
        assert model1.age == 0
        assert model2.name is None
        assert model2.age is None

    def test_concurrent_reads(self, populated_db):
        """Test concurrent read operations"""
        results = []
        for _ in range(100):
            model = populated_db.get_model_by_id(1)
            results.append(model)

        assert all(m.name == 'Alice' for m in results)

    def test_transaction_isolation(self, temp_db):
        """Test transaction isolation"""
        db1 = DataBase[BasicModel](BasicModel, temp_db)
        db2 = DataBase[BasicModel](BasicModel, temp_db)

        db1.add_model({'name': 'Test1'})

        # db2 should see the committed data
        assert db2.get_count() == 1

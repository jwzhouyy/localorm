# LocalORM

一个基于 SQLModel 的轻量级 SQLite ORM 库，提供类型安全的数据库操作和自动表结构同步功能。

## 特性

- 🚀 **简单易用**: 基于 SQLModel，API 简洁直观
- 🔄 **自动同步**: 自动检测模型变更并同步表结构
- 🛡️ **类型安全**: 完整的类型提示支持
- 📦 **批量操作**: 高效的批量插入和查询
- 🔍 **灵活查询**: 支持自定义查询扩展
- ⚡ **高性能**: 批量操作自动分批处理（10000条/批）

## 安装

```bash
pip install localorm
```

## 快速开始

### 1. 定义模型

```python
import time

from dataclasses import dataclass
from pydantic import BaseModel

from localorm import DataBase, UniqueConstraint, Field, select, ORMModel, PydanticField, JSON, DataclassField


@dataclass
class Property:
    a: int | None = None
    b: str | None = 'abc'


class Extra(BaseModel):
    a: int | None = None
    b: str | None = 'abc'


class UserRepository(DataBase['UserRepository.ModelClass']):
    class ModelClass(ORMModel, table=True):
        __tablename__ = 'users'  # 指定表名
        __table_args__ = (UniqueConstraint('s', 't', name='uq_user_s_t'),)  # 联合唯一索引

        name: str | None = None
        # age: int | None = None
        s: int | None = None
        t: int
        extra: Extra | None = PydanticField(Extra)

        property: Property | None = DataclassField(Property)

    def get_users_by_name(self, name: str) -> list[ModelClass]:
        with self._get_session() as session:
            stmt = select(self.ModelClass).where(self.ModelClass.name == name)
            results = session.exec(stmt).all()
            return results

    def gett(self, s, t):
        with self._get_session() as session:
            stmt = (
                select(self.ModelClass).where(self.ModelClass.s == s).where(self.ModelClass.t == t)
            )
            results = session.exec(stmt).all()
            return results

```

### 2. 创建数据库实例

```python
user_repo = UserRepository('sqlite///tt.db')
```

### 3. CRUD 操作

#### 添加数据

```python
# 添加单条
user = user_repo.add_model({
    # 'id': 12,
    'name': 'jwz',
    's': int(time.time() * 1000),
    't': int(time.time() * 1000),
    'age': 1,
    'extra': {
        'a': 1,
        'b': 'abc'
    },
    'property': {
        'a': 1,
        'b': 'abc'
    }
})
print(f"Added user ID: {user.id}")

# 批量添加
users_data = [
    {
        # 'id': 12,
        'name': 'jwz',
        's': int(time.time() * 1000),
        't': int(time.time() * 1000),
        'age': 1,
        'extra': {
            'a': 1,
            'b': 'abc'
        },
        'property': {
            'a': 1,
            'b': 'abc'
        }
    },
    {
        # 'id': 12,
        'name': 'jwz',
        's': int(time.time() * 1000),
        't': int(time.time() * 1000),
        'age': 1,
        'extra': {
            'a': 1,
            'b': 'abc'
        },
        'property': {
            'a': 1,
            'b': 'abc'
        }
    },
]
user_repo.add_models(users_data)
```

#### 查询数据

```python
# 通过 ID 查询单条
user = user_repo.get_model_by_id(1)

# 批量查询多个 ID
users_dict = user_repo.get_models_by_ids([1, 2, 3])  # 返回 {id: model} 字典

# 查询所有
all_users = user_repo.iter_all_models()

# 获取总数
count = user_repo.get_count()
```

#### 更新数据

```python
# 更新指定字段
updated_user = user_repo.update_model_by_id(1, {
    'age': 31,
    'email': 'newemail@example.com'
})

if updated_user:
    print(f"Updated: {updated_user.name}")
else:
    print("User not found")
```

#### 删除数据

```python
# 删除单条
success = user_repo.delete_model_by_id(1)

# 批量删除
deleted_count = user_repo.delete_model_by_ids([1, 2, 3])
print(f"Deleted {deleted_count} users")
```

## 高级功能

### 自动表结构同步

LocalORM 会自动检测模型变更并同步数据库表结构：

- **新增字段**: 自动添加新列到现有表
- **删除字段**: 自动重建表并迁移数据
- **无需手动迁移**: 启动时自动完成

```python
# 原始模型
class ModelClass(SQLModel, table=True):
    name: str | None = None


# 修改后的模型（添加了 email 字段）
class ModelClass(SQLModel, table=True):
    name: str | None = None
    email: str | None = None  # 新字段自动添加


# 重新初始化时自动同步
user_repo = UserRepository('tt.db')
```

### 自定义查询扩展

```python
from localorm import DataBase, select


class UserRepository(DataBase[User]):
    def get_users_by_name(self, name: str) -> list[User]:
        with self._get_session() as session:
            stmt = select(self.model_class).where(self.model_class.name == name)
            return session.exec(stmt).all()

    def get_adult_users(self) -> list[User]:
        with self._get_session() as session:
            stmt = select(self.model_class).where(self.model_class.age >= 18)
            return session.exec(stmt).all()


user_repo = UserRepository(User, 'users.db')
adults = user_repo.get_adult_users()
```

### 唯一约束

```python
class UserRepository(DataBase['UserRepository.ModelClass']):
    class ModelClass(ORMModel, table=True):
        __tablename__ = 'users'  # 指定表名
        __table_args__ = (UniqueConstraint('s', 't', name='uq_user_s_t'),)  # 联合唯一索引

        name: str | None = None
```

### 类型映射

LocalORM 支持以下 Python 类型到 SQL 类型的自动映射：

| Python 类型                        | SQL 类型  |
|----------------------------------|---------|
| \`int\`, \`Optional[int]\`       | INTEGER |
| \`float\`, \`Optional[float]\`   | REAL    |
| \`bool\`, \`Optional[bool]\`     | INTEGER |
| \`str\`, \`Optional[str]\`       | TEXT    |
| \`dict\`, \`list\`               | JSON    |
| \`dataclass\`, \`Optional[Any]\` | JSON    |
| \`pydantic\`, \`Optional[Any]\`  | JSON    |

### 批量操作优化

## API 参考

### DataBase 类


#### 添加操作

- \`add_model(data: dict) -> Model\` - 添加单条记录
- \`add_models(data_list: list[dict]) -> list[Model]\` - 批量添加
- \`add_model_or_ignore(data: dict) -> Model | None\` - 添加或忽略（唯一约束冲突时）

#### 查询操作

- \`get_model_by_id(id: int) -> Optional[Model]\` - 通过ID查询
- \`get_models_by_ids(ids: list[int]) -> Dict[int, Model]\` - 批量查询
- \`iter_all_models() -> List[Model]\` - 查询所有
- \`get_count() -> int\` - 获取总数

#### 更新操作

- \`update_model_by_id(id: int, data: dict) -> Optional[Model]\` - 更新记录

#### 删除操作

- \`delete_model_by_id(id: int) -> bool\` - 删除单条
- \`delete_model_by_ids(ids: list[int]) -> int\` - 批量删除，返回删除数量

#### 调试工具

- \`print_all()\` - 打印所有记录

```bash
# install
pip install localorm

```

## 完整示例

```python
# coding: utf-8

import logging
import time

from dataclasses import dataclass
from pydantic import BaseModel

from localorm import DataBase, UniqueConstraint, Field, select, ORMModel, PydanticField, JSON, DataclassField


@dataclass
class Property:
    a: int | None = None
    b: str | None = 'abc'


class Extra(BaseModel):
    a: int | None = None
    b: str | None = 'abc'


class UserRepository(DataBase['UserRepository.ModelClass']):
    class ModelClass(ORMModel, table=True):
        __tablename__ = 'users'  # 指定表名
        __table_args__ = (UniqueConstraint('s', 't', name='uq_user_s_t'),)  # 联合唯一索引

        name: str | None = None
        # age: int | None = None
        s: int | None = None
        t: int
        extra: Extra | None = PydanticField(Extra)

        property: Property | None = DataclassField(Property)

    def get_users_by_name(self, name: str) -> list[ModelClass]:
        with self._get_session() as session:
            stmt = select(self.ModelClass).where(self.ModelClass.name == name)
            results = session.exec(stmt).all()
            return results

    def gett(self, s, t):
        with self._get_session() as session:
            stmt = (
                select(self.ModelClass).where(self.ModelClass.s == s).where(self.ModelClass.t == t)
            )
            results = session.exec(stmt).all()
            return results


# ============================================================
# 测试示例
# ============================================================
def main():
    # user_repo = BaseRepository[User](User)
    user_repo = UserRepository('sqlite////Users/xx/tt.db')
    user = user_repo.add_model({
        # 'id': 12,
        'name': 'jwz',
        's': int(time.time() * 1000),
        't': int(time.time() * 1000),
        'age': 1,
        'extra': {
            'a': 1,
            'b': 'abc'
        },
        'property': {
            'a': 1,
            'b': 'abc'
        }
    })
    u = user_repo.get_model_by_id(user.id)
    # print(u.property.b)
    # us = []
    # for i in range(10):
    #     u = {'name': 'jwz', 's': i, 't': int(time.time()), 'age': 1}
    #     # user_repo.add_model(u)
    #     us.append(u)
    #
    # user_repo.add_models(us)

    # for u in user_repo.get_all_models():
    #     print(u.id)
    # for u in user_repo.gett(1, 121):
    #     print(u)
    # u = user_repo.get_model_by_id(5)
    # print(u)
    user_repo.print_all(reverse=False)
    # d = user_repo.get_users_by_name('jwz')
    # d = user_repo.gett(9, 1762252019)

    # print(d)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO, format='%(asctime)s %(name)s:%(lineno)d [%(levelname)s] %(message)s'
    )
    main()

```

## 注意事项

1. **字段删除**: 删除模型字段会触发表重建，数据会自动迁移，但建议提前备份
2. **字段过滤**: 传入未定义的字段会被自动过滤，不会报错
3. **事务管理**: 所有操作自动管理事务，无需手动提交
4. **连接池**: 每次操作使用独立 Session，操作完成后自动关闭
5. **大批量操作**: \`add_models\` 会自动分批处理，避免内存溢出

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
EOF

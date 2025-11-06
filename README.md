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
pip install -e .
```

## 快速开始

### 1. 定义模型

```python
from localorm import SQLModel, Field, DataBase, UniqueConstraint

class User(SQLModel, table=True):
    __tablename__ = 'users'
    __table_args__ = (UniqueConstraint('email', name='uq_email'),)

    id: int = Field(default=None, primary_key=True)
    name: str | None = None
    email: str | None = None
    age: int | None = None
```

### 2. 创建数据库实例

```python
# 方式1: 使用基础 DataBase 类
user_db = DataBase[User](User, 'users.db')

# 方式2: 继承扩展自定义方法
class UserRepository(DataBase[User]):
    def get_users_by_age(self, age: int) -> list[User]:
        with self._get_session() as session:
            stmt = select(self.model_class).where(self.model_class.age == age)
            return session.exec(stmt).all()

user_repo = UserRepository(User, 'users.db')
```

### 3. CRUD 操作

#### 添加数据

```python
# 添加单条
user = user_db.add_model({'name': 'Alice', 'email': 'alice@example.com', 'age': 30})
print(f"Added user ID: {user.id}")

# 批量添加
users_data = [
    {'name': 'Bob', 'email': 'bob@example.com', 'age': 25},
    {'name': 'Charlie', 'email': 'charlie@example.com', 'age': 35}
]
users = user_db.add_models(users_data)

# 添加或忽略（遇到唯一约束冲突时忽略）
user = user_db.add_model_or_ignore({'name': 'Alice', 'email': 'alice@example.com', 'age': 30})
if user is None:
    print("User already exists")
```

#### 查询数据

```python
# 通过 ID 查询单条
user = user_db.get_model_by_id(1)

# 批量查询多个 ID
users_dict = user_db.get_models_by_ids([1, 2, 3])  # 返回 {id: model} 字典

# 查询所有
all_users = user_db.get_all_models()

# 获取总数
count = user_db.get_count()
```

#### 更新数据

```python
# 更新指定字段
updated_user = user_db.update_model_by_id(1, {'age': 31, 'email': 'newemail@example.com'})

if updated_user:
    print(f"Updated: {updated_user.name}")
else:
    print("User not found")
```

#### 删除数据

```python
# 删除单条
success = user_db.delete_model_by_id(1)

# 批量删除
deleted_count = user_db.delete_model_by_ids([1, 2, 3])
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
class User(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str | None = None

# 修改后的模型（添加了 email 字段）
class User(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str | None = None
    email: str | None = None  # 新字段自动添加

# 重新初始化时自动同步
user_db = DataBase[User](User, 'users.db')
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
from localorm import SQLModel, Field, UniqueConstraint

class Product(SQLModel, table=True):
    __tablename__ = 'products'
    __table_args__ = (
        UniqueConstraint('sku', name='uq_sku'),  # 单字段唯一
        UniqueConstraint('brand', 'model', name='uq_brand_model'),  # 联合唯一
    )

    id: int = Field(default=None, primary_key=True)
    sku: str
    brand: str
    model: str
    price: float
```

### 类型映射

LocalORM 支持以下 Python 类型到 SQL 类型的自动映射：

| Python 类型 | SQL 类型 |
|------------|----------|
| \`int\`, \`Optional[int]\` | INTEGER |
| \`float\`, \`Optional[float]\` | REAL |
| \`bool\`, \`Optional[bool]\` | INTEGER |
| \`str\`, \`Optional[str]\` | TEXT |
| \`dict\`, \`list\` | JSON |

### 批量操作优化

```python
# 大批量数据自动分批处理（10000条/批）
large_dataset = [{'name': f'User{i}', 'age': i % 100} for i in range(50000)]
users = user_db.add_models(large_dataset)  # 自动分5批处理
```

## API 参考

### DataBase 类

#### 初始化
```python
DataBase[Model](model_class: Type[Model], save_path: str)
```

#### 添加操作
- \`add_model(data: dict) -> Model\` - 添加单条记录
- \`add_models(data_list: list[dict]) -> list[Model]\` - 批量添加
- \`add_model_or_ignore(data: dict) -> Model | None\` - 添加或忽略（唯一约束冲突时）

#### 查询操作
- \`get_model_by_id(id: int) -> Optional[Model]\` - 通过ID查询
- \`get_models_by_ids(ids: list[int]) -> Dict[int, Model]\` - 批量查询
- \`get_all_models() -> List[Model]\` - 查询所有
- \`get_count() -> int\` - 获取总数

#### 更新操作
- \`update_model_by_id(id: int, data: dict) -> Optional[Model]\` - 更新记录

#### 删除操作
- \`delete_model_by_id(id: int) -> bool\` - 删除单条
- \`delete_model_by_ids(ids: list[int]) -> int\` - 批量删除，返回删除数量

#### 调试工具
- \`print_all()\` - 打印所有记录

## 测试

```bash
# 安装测试依赖
pip install -e .

# 运行测试
pytest tests/ -v

# 查看测试覆盖率
pytest tests/ --cov=localorm --cov-report=html
```

## 完整示例

```python
from localorm import SQLModel, Field, DataBase, UniqueConstraint, select

# 定义模型
class Article(SQLModel, table=True):
    __tablename__ = 'articles'
    __table_args__ = (UniqueConstraint('url', name='uq_url'),)

    id: int = Field(default=None, primary_key=True)
    title: str
    url: str
    author: str | None = None
    views: int = 0

# 创建仓储类
class ArticleRepository(DataBase[Article]):
    def get_popular_articles(self, min_views: int = 100) -> list[Article]:
        with self._get_session() as session:
            stmt = select(self.model_class).where(
                self.model_class.views >= min_views
            ).order_by(self.model_class.views.desc())
            return session.exec(stmt).all()

    def increment_views(self, article_id: int) -> Optional[Article]:
        article = self.get_model_by_id(article_id)
        if article:
            return self.update_model_by_id(article_id, {'views': article.views + 1})
        return None

# 使用
repo = ArticleRepository(Article, 'articles.db')

# 添加文章
article = repo.add_model({
    'title': 'Python ORM Tutorial',
    'url': 'https://example.com/python-orm',
    'author': 'Alice'
})

# 增加浏览量
repo.increment_views(article.id)

# 获取热门文章
popular = repo.get_popular_articles(min_views=50)
for art in popular:
    print(f"{art.title}: {art.views} views")
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

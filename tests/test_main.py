# coding: utf-8

import logging
import os

import time

from dotenv import load_dotenv


from dataclasses import dataclass
from pydantic import BaseModel
from sqlalchemy import BigInteger

from localorm import (
    DataBase,
    UniqueConstraint,
    Field,
    select,
    ORMModel,
    PydanticField,
    JSON,
    DataclassField,
    Column,
    URL,
    immutabledict,
)


@dataclass
class Property:
    a: int | None = None
    b: str | None = 'abc'


class Extra(BaseModel):
    a: int | None = None
    b: str | None = 'abc'
    c: str = 'c'
    d: str = 'd'


class UserRepository(DataBase['UserRepository.ModelClass']):
    class ModelClass(ORMModel, table=True):
        __tablename__ = 'users'  # 指定表名
        __table_args__ = (UniqueConstraint('s', 't', name='uq_user_s_t'),)  # 联合唯一索引

        name: str | None = None
        age: int | None = Field(
            default=None,
            sa_type=BigInteger,  # 关键：指定使用 BigInteger 类型
        )
        s: int | None = Field(
            default=None,
            sa_type=BigInteger,  # 关键：指定使用 BigInteger 类型
        )
        t: int = Field(
            default=None,
            sa_type=BigInteger,  # 关键：指定使用 BigInteger 类型
        )
        extra: Extra | None = PydanticField(Extra)
        my_dict: dict | None = Field(
            default_factory=dict,
            sa_column=Column(JSON, nullable=True),
        )
        property: Property | None = DataclassField(Property)

    def get_users_by_name(self, name: str) -> list[ModelClass]:
        with self._get_session() as session:
            stmt = select(self.ModelClass).where(self.ModelClass.name == name)
            results = session.exec(stmt).all()
            return results

    def gett(self, s, t):
        with self._get_session() as session:
            stmt = select(self.ModelClass).where(self.ModelClass.s == s).where(self.ModelClass.t == t)
            results = session.exec(stmt).all()
            return results


# ============================================================
# 测试示例 需要安装pymysql, cryptography
# ============================================================
def main():
    load_dotenv()
    # user_repo = BaseRepository[User](User)
    # user_repo = UserRepository(
    #     URL(
    #         drivername='mysql+pymysql',
    #         username=os.getenv('MYSQL_USERNAME'),
    #         password=os.getenv('MYSQL_PASS'),
    #         host=os.getenv('MYSQL_HOST'),
    #         port=int(os.getenv('MYSQL_PORT')),
    #         database='free_misc',
    #         query=immutabledict({'charset': 'utf8mb4'}),
    #     )
    # )
    user_repo = UserRepository(
        'sqlite:///tt.db',
        connect_args={
            'check_same_thread': False,
            'timeout': 30,
        },
    )
    user_repo.get_model_by_id(42)
    # user = user_repo.add_model(
    #     {
    #         # 'id': 12,
    #         'name': 'jwz',
    #         's': int(time.time() * 1000),
    #         't': int(time.time() * 1000),
    #         'age': 1,
    #         # 'property': {'a': 1, 'b': 'abc', 'c': 'c', 'd': 123},
    #         'extra': {'a': 1, 'b': 'abc', 'c': 'c'},
    #     }
    # )
    # u = user_repo.get_model_by_id(user.id)
    # print(u)
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
    # for u in user_repo.iter_all_models(reverse=True, batch_size=2):
    #     print(u)
    # d = user_repo.get_users_by_name('jwz')
    # d = user_repo.gett(1767078437392, 1767078437392)

    # print(d)
    # print(user_repo.get_count())


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO, format='%(asctime)s %(name)s:%(lineno)d [%(levelname)s] %(message)s'
    )
    main()

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
    user_repo = UserRepository('tt.db')
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

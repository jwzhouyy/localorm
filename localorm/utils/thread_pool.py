# coding: utf-8

import logging
import random
import threading
import time

from queue import Queue
from typing import Any, Callable, Dict
from concurrent.futures import ThreadPoolExecutor


class ThreadPoolExecutorWithQueueSizeLimit(ThreadPoolExecutor):
    def __init__(self, max_queue_size=50, *args, **kwargs):
        super(ThreadPoolExecutorWithQueueSizeLimit, self).__init__(*args, **kwargs)
        self._work_queue = Queue(maxsize=max_queue_size)


def ThreadPool(
    max_workers=30,
    max_queue_size=100,
):
    return ThreadPoolExecutorWithQueueSizeLimit(
        max_workers=max_workers,
        max_queue_size=max_queue_size,
    )


def create_loop_thread(
    target_function: Callable,
    args: tuple = (),
    kwargs: Dict[str, Any] | None = None,
    loop_interval: float = 0,
) -> threading.Thread:
    """
    创建一个无限循环调用目标函数的线程

    参数:
        target_function: 要调用的函数
        args: 传递给函数的位置参数
        kwargs: 传递给函数的关键字参数
        loop_interval: 每次调用之间的间隔时间(秒)

    返回:
        配置好的线程对象，但尚未启动
    """
    if kwargs is None:
        kwargs = {}

    def loop_function():
        while True:
            target_function(*args, **kwargs)
            if loop_interval > 0:
                time.sleep(loop_interval)

    # 创建非守护线程（默认daemon=False）
    thread = threading.Thread(target=loop_function)
    return thread


def thread_pool_agent(
    actual_func: Callable,
    iter_object: list,
    max_workers: int = 10,
    max_queue_size: int = 20,
    fargs: tuple = (),
    fkwargs: dict = {},
):
    logger = logging.getLogger(__name__)

    def _log_future_exception(done_future, local_item):
        try:
            done_future.result()
        except BaseException:
            logger.exception('thread pool task failed: item=%s', local_item)

    with ThreadPool(max_workers=max_workers, max_queue_size=max_queue_size) as executor:
        for i, local_character_id in enumerate(iter_object, 1):
            logger.info('%s/%s', i, len(iter_object))
            if max_workers > 1:
                future = executor.submit(
                    actual_func,
                    local_character_id,
                    *fargs,
                    **fkwargs,
                )
                future.add_done_callback(
                    lambda done_future, local_item=local_character_id: _log_future_exception(
                        done_future, local_item
                    )
                )
            else:
                actual_func(local_character_id, *fargs, **fkwargs)


def task(n, uk=None):
    logging.getLogger(__name__).info(
        f"ident: {threading.get_ident()}, Task {uk} is starting, sleeping for {n} seconds."
    )
    time.sleep(n)  # 模拟耗时操作
    # logging.getLogger(__name__).info(f"ident: {threading.get_ident()}, Task {uk}, sleeping for {n} seconds is completed.")


def main():
    with ThreadPool(max_workers=2, max_queue_size=100) as ts:
        for i in range(10):
            # time.sleep(1)
            print(i)
            ts.submit(task, random.randint(1, 5), i)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format='%(asctime)s %(name)s:%(lineno)d [%(levelname)s] %(message)s'
    )
    pass
    # t_loop_thread()
    main()

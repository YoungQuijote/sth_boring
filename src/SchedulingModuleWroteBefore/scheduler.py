"""
资源池调度管理器
"""


from __future__ import annotations

import time
from typing import Union, Dict

import sys
import pathlib

import threading

from loguru import logger

_current_dir = pathlib.Path(__file__).parent.resolve()
sys.path.append(str(_current_dir.parent))

try:
    from openai_interface import OpenAiEndpoint, OpenaiApiWrapper, ChatPayload, ApiPayload
    from abc_cls import UrlPayload, ApiStatus, CircuitBreakerError
except ImportError:
    raise


class OpenaiLlmApiScheduler:
    _instance = None
    _instance_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        # 单例模式
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super(OpenaiLlmApiScheduler, cls).__new__(cls)

        return cls._instance

    def __init__(
            self,
            openai_api: Union[OpenaiApiWrapper, list[OpenaiApiWrapper], None] = None
    ):

        self._lock = threading.RLock()
        self._pool: list[OpenaiApiWrapper] = []
        self._last_api: Union[OpenaiApiWrapper, None] = None
        self._adapt_interval: int = 60
        self._interval_break_time: float = 0.0

        if isinstance(openai_api, list):
            self._pool.extend(openai_api)
        elif isinstance(openai_api, OpenaiApiWrapper):
            self._pool.append(openai_api)
        else:
            pass

        self._sum_weight = sum(_api.base_weight for _api in self._pool)

    def registry(self, openai_api: OpenaiApiWrapper) -> None:
        self._pool.append(openai_api)
        self._sum_weight = sum(_api.base_weight for _api in self._pool)

    def set_adapt_interval(self, interval: int) -> None:
        if interval <= 0:
            raise ValueError("interval must be greater than 0")
        self._adapt_interval = interval

    def acquire(
            self,
            endpoint: OpenAiEndpoint = OpenAiEndpoint.chat,
    ) -> UrlPayload:
        """
        获取LLM接口信息
        """
        with self._lock:
            if not self._pool:
                _e_url_payload = UrlPayload(url="", method="", access_token="")
                return _e_url_payload

            cool_down_weight = sum(_.base_weight for _ in self._pool)
            best_api: OpenaiApiWrapper
            _unused: int = 0

            for _api in self._pool:
                if _api.get_status() is ApiStatus.STOPPED:
                    _unused += 1

                    if _unused == len(self._pool):
                        raise CircuitBreakerError("No usable interface now, plz try later.")

                    continue

                # SWWR调度算法
                _api.swrr_weight += _api.get_weight()
                if best_api is None or _api.swrr_weight > best_api.swrr_weight:
                    best_api = _api

            best_api.swrr_weight -= cool_down_weight
            self._last_api = best_api

            return best_api(endpoint)

    def _redistribute(
            self,
            delta: int,
            changer: OpenaiApiWrapper
    ) -> None:
        """
        权重重分配

        :param delta: 权重变更
        :param changer: 发生权重变更的接口
        """
        # 确定重分配目标
        _targets = [
            _api for _api in self._pool
            if _api.interface_id != changer.interface_id
            and _api.get_status() is not ApiStatus.STOPPED
        ]
        if not _targets:
            return

        # 计算权重分配权重
        _base_sum = self._sum_weight
        _shares = [delta * (_api.base_weight / _base_sum) for _api in _targets]
        rounded = [int(round(_s)) for _s in _shares]

        # 精度补偿
        delta_fix = delta - sum(rounded)  # 误差: -1, 0, +1
        for idx in sorted(
            range(len(_targets)),
            key=lambda i: _targets[i].base_weight,  # 根据权重从小到大排序
            reverse=True
        ):
            if delta_fix == 0:
                break

            rounded[idx] += 1 if delta_fix > 0 else -1
            delta_fix -= 1 if delta_fix > 0 else 1

        # 执行重分配
        for _api, _delta in zip(_targets, rounded):
            _api.adapt_weight(_delta)

        logger.debug(f"权重重新分配: {changer.interface_id}: {delta} "
                     f"-> {[_api.base_weight for _api in _targets]}")

    def update_weight(
            self,
            success: bool,
    ) -> None:
        """
        更新权重
        """
        _status = self._last_api.get_status()

        if success:
            self._last_api.reset_fail()

            if _status is ApiStatus.ACTIVATED:
                pass
            elif _status is ApiStatus.RECOVERING:
                if time.time() > self._interval_break_time:
                    self._redistribute(
                        delta=self._last_api.recover_step,
                        changer=self._last_api
                    )
                    self._interval_break_time = time.time() + self._adapt_interval
            else:
                raise Exception("WTF, How could this be possible ???")

        else:
            self._last_api.record_fail()

            self._redistribute(
                delta=self._last_api.decay_step,
                changer=self._last_api
            )

    def __call__(self, *args, **kwargs) -> UrlPayload:
        try:
            url_payload = self.acquire(*args, **kwargs)
        except CircuitBreakerError as ce:
            logger.error(ce)
            raise
        except Exception as e:
            logger.exception(e)
            raise

        return url_payload

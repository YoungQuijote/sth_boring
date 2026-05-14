"""
模型调用接口--相关抽象类
"""


from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Union, TypedDict
from dataclasses import dataclass, field

import time

from threading import RLock


class UrlPayload(TypedDict):
    """
    Url相关信息封装声明

    Attributes:
        url (str): 完整的url
        method (str): url的请求方式
        access_token (str): url的鉴权认证
    """
    model_id: str
    url: str
    method: str
    access_token: str


@dataclass
class LlmApiConfig:
    """
    LLM 接口配置封装类
    """
    model_id: str
    base_url: str = "scheme://host:port/route"
    base_method: str = "POST"
    access_token: str = "sk-xxx"
    custom_param: Any = ..., field(init=False)


class ApiStatus(str, Enum):
    ACTIVATED = "activated"
    STOPPED = "circuit_break"
    RECOVERING = "recovering"


class CircuitBreakerError(RuntimeError):
    """熔断保护"""

    def __init__(
            self,
            message: Union[str, None] = None,
            retry_after: Union[str, None] = None
    ):
        self.retry_after = retry_after
        super().__init__(message or "Service is in circuit breaker. Please try again later.")


@dataclass
class LlmApiWrapper(ABC):
    """
    LLM接口封装类

    适用于资源调度管理器. 内置有"健康检查", "接口熔断"等功能

    Attributes:
        interface_id (str): 接口名称. 无实际作用
        interface_config (LlmApiConfig): LLM接口配置封装类

        base_weight (int): 调度权重
        decay_step (int):  权重衰减步长
        recover_step (int): 权重恢复步长
        max_fails (int): 规定时间内的最大失败次数 (达到该阈值会触发熔断)
        cool_down (float): 熔断冷却
    """
    interface_id: str
    interface_config: LlmApiConfig

    base_weight: int = 80  # 初始权重, 静态
    decay_step: int = 20
    recover_step: int = 20
    max_fails: int = 5
    cool_down: float = 60

    _lock: RLock = field(init=False)  # 线程锁
    _status: ApiStatus = field(init=False)  # 接口状态
    _dynamic_weight: int = field(init=False)  # 动态权重, 用于内部调整. 取值范围: [0, base_weight]
    swrr_weight: int = field(init=False)  # 实际暴露给外界的权重, 用于负载均衡: SWRR(_dynamic_weight) = swrr_weight
    _fail_cnt: int = field(init=False)  # 连续失败次数
    _cool_ending: float = field(init=False)  # 冷却结束时间

    def __post_init__(self):
        self._lock = RLock()
        self._status = ApiStatus.ACTIVATED
        self._dynamic_weight = self.base_weight
        self.swrr_weight = self.base_weight
        self._fail_cnt = 0
        self._cool_ending = 0.0

    @abstractmethod
    def health_check(self) -> bool:
        """
        健康检查
        """
        ...

    def get_status(self) -> ApiStatus:
        """
        获取API可用状态
        """
        if self._status is ApiStatus.STOPPED:
            if time.time() > self._cool_ending:
                self._dynamic_weight += self.recover_step
                self._cool_ending = 0.0
                self._status = ApiStatus.RECOVERING

        return self._status

    def get_weight(self) -> int:
        """获取调度权重"""
        return self._dynamic_weight

    def adapt_weight(self, delta: int) -> None:
        """调整调度权重"""
        if delta < 0:
            self._status = ApiStatus.RECOVERING

        self._dynamic_weight += delta
        if self._dynamic_weight < 0:
            self.circuit_break()

    def circuit_break(self) -> None:
        """
        负载熔断: 熔断期间拒绝调用

        触发熔断的条件:
        1. 健康检查失败 (立即触发)
        2. 连续失败次数达到熔断阈值
        """
        self._status = ApiStatus.STOPPED
        self._dynamic_weight = 0
        self._cool_ending = time.time() + self.cool_down
        self._fail_cnt = 0  # 重置连续失败次数

    def record_fail(self) -> None:
        """
        记录调用失败情况
        """
        self._fail_cnt += 1

    def reset_fail(self) -> None:
        """
        重置连续失败次数
        """
        self._fail_cnt = 0

    def __call__(self, *args, **kwargs) -> UrlPayload:
        with self._lock:
            if not (
                self.health_check()
                and self._fail_cnt < self.max_fails
            ):
                self.circuit_break()  # 触发熔断

            if self.get_status() is ApiStatus.STOPPED:
                raise CircuitBreakerError()

        url_payload = UrlPayload(
            model_id=self.interface_config.model_id,
            url=self.interface_config.base_url,
            method=self.interface_config.base_method,
            access_token=self.interface_config.access_token
        )

        return url_payload

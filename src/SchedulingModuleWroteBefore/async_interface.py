"""
openai格式LLM框架的异步请求接口类
"""


from enum import Enum
from typing import TypedDict, Any, Union

import asyncio
import aiohttp
import json

from loguru import logger


class OpenAiEndpoint(str, Enum):
    """OpenAI格式的模型调用接口--Endpoint枚举"""
    chat = "chat"
    health = "health"
    load = "load"
    ping = "ping"
    version = "version"


class ChatPayload(TypedDict):
    """
    LLM服务Chat对话结果封装声明

    Attributes:
        reason (str): 模型推理过程
        result (str): 模型输出内容
    """
    reason: str
    result: str


class ApiPayload(TypedDict):
    """
    LLM接口信息封装声明

    Attributes:
        chat (bool): 接口chat对话结果(Dict["reason": <模型推理过程>, "result": <模型输出内容>])
        health (str): 接口是否健康
        load (str): 接口负载数量 (int)
        ping (str): 接口是否可连通
        version (str): 接口模型版本号 (str)
    """
    chat: ChatPayload
    health: bool
    load: int
    ping: bool
    version: str
    success: bool


class AsyncRequest:
    def __init__(self):
        pass

    @staticmethod
    async def async_request_openai(
            url: str,
            model_id: str,
            context: str,
            access_token: str = "",
            *,
            session: Union[aiohttp.ClientSession, None] = None,
            method: str = "POST",
            stream_pattern: bool = True,
            headers: Union[dict, None] = None,
            param: Any = None,
            json_data: Union[dict, None] = None,
            messages: Union[list[dict], None] = None,
            thinking: bool = False,
            tools: Union[list[dict], None] = None,
            temperature: float = 0.0,
            timeout: int = 300,
            aiohttp_kwargs: Union[dict, None] = None,
            llm_kwargs: Union[dict, None] = None,
    ) -> aiohttp.ClientResponse:
        """
        这是基于<aiohttp模块的request方法>封装的LLM调用接口

        :param url: LLM服务API
        :param model_id: LLM服务模型标识
        :param context: 输入给LLM的文本
        :param access_token: LLM服务API的鉴权认证
        :param session: aiohttp模块的调用实例
        :param method: 调用方式("GET", "POST"). 默认为 "POST"
        :param stream_pattern: 流式调用模式开关. 默认为 True
        :param headers: session._request参数: 请求头. 缺省时将采用标准请求头, 并采用"Authorization"字段进行鉴权
        :param param: session._request参数: param请求体: Query
        :param json_data: session._request参数: json请求体: Any
        :param messages: 输入给LLM的messages. 完整, 多轮的上下文, 请按照openai规范的格式输入. 启用该参数时, <context>参数失效
        :param thinking: :param thinking: 是否允许模型思考 (推理)
        :param tools: 旧名<function_call>. 外挂工具描述, 请按照openai规范的格式输入
        :param temperature: LLM控制参数: 温度. 默认为 0.0
        :param timeout: 超时等待. 默认为300秒
        :param aiohttp_kwargs: aiohttp.ClientSession._request相关参数. 请采用: {"关键字": 数值} 的字典格式传入
        :param llm_kwargs: 控制LLM的相关参数. 请采用: {"关键字": 数值} 的字典格式传入

        :return: aiohttp.ClientResponse
        """
        headers = {
            "Accept": "*/*",
            "Content-Type": "application/json",
            **({"Authorization": access_token} if access_token else {}),
            **(headers or {})
        }

        if not aiohttp_kwargs:
            aiohttp_kwargs = {}

        if not llm_kwargs:
            llm_kwargs = {}

        json_data = json_data or {
            "model": model_id,
            "messages": messages
            if messages
            else [
                {
                    "role": "user",
                    "content": context
                },
            ],
            "tools": tools or [],
            "temperature": temperature,
            "stream": stream_pattern,
            "chat_template_kwargs": {
                "enable_thinking": thinking
            },
            **(llm_kwargs or {})
        }

        ssl_timeout = aiohttp.ClientTimeout(total=timeout)

        owns_session = session is None
        if owns_session:
            session = aiohttp.ClientSession()

        try:
            _response = await session.request(
                method=method,
                url=url,
                params=param,
                json=json_data,
                headers=headers,
                timeout=ssl_timeout,
                ssl=False,
                **aiohttp_kwargs
            )

            # 流式调用
            if stream_pattern:
                return _response

            # 非流式调用
            else:
                await session.close()
                return _response
        except Exception as e:
            logger.exception(f"TraceBack for {e}")
            raise
        finally:
            if owns_session:
                await session.close()

    @staticmethod
    async def __openai_stream_chat_response_async_processor(
            response: aiohttp.ClientResponse,
            details_log: bool = False
    ) -> ChatPayload:
        """
        这是用于处理由<aiohttp.ClientResponse._requests>发起, 由openai框架返回的, 流式响应的隐藏方法

        :param response: 由aiohttp发起, 由openai框架返回的流式响应
        :param details_log: 详情日志开关. 默认为False

        :return: openai返回的流式响应的解析结果
        """
        block_size = 1024  # 预设缓冲块大小
        reason_cache = [""] * block_size  # 初始化推理缓冲块
        result_cache = [""] * block_size  # 初始化结果缓冲块
        reason_cache_size = block_size  # 缓冲大小
        result_cache_size = block_size
        reason_point = 0
        result_point = 0

        async for line in response.content:
            decode_line = line.decode('utf-8-sig').removeprefix("data: ").strip()
            if decode_line:
                try:
                    json_line = json.loads(decode_line)
                except json.JSONDecodeError:
                    logger.error(f"JSONDecodeError: {decode_line}")
                    continue

                if json_line['choices'][0].get("finish_reason") == "stop":
                    break

                _json_reason_ = json_line['choices'][0]['delta'].get("reasoning_content")
                _json_result_ = json_line['choices'][0]['delta'].get("content")

                if _json_reason_ is not None:
                    # 如果获取到 reason_, 则使用推理缓冲块处理
                    if details_log:
                        logger.info(f"Reason: {_json_reason_}")

                    if reason_point == reason_cache_size:
                        # 如果推理缓冲块已满, 则扩展缓冲块
                        reason_cache.extend([""] * block_size)
                        reason_cache_size += block_size

                    reason_cache[reason_point] = _json_reason_
                    reason_point += 1

                if _json_result_ is not None:
                    # 如果获取到 result_, 则使用结果缓冲块处理
                    if details_log:
                        logger.info(f"Result: {_json_result_}")

                    if result_point == result_cache_size:
                        # 如果结果缓冲块已满, 则扩展缓冲块
                        result_cache.extend([""] * block_size)
                        result_cache_size += block_size

                    result_cache[result_point] = _json_result_
                    result_point += 1

        reason_content = "".join(reason_cache[:reason_point])
        result_content = "".join(result_cache[:result_point])

        chat_payload = ChatPayload(reason=reason_content, result=result_content)

        return chat_payload

    @staticmethod
    async def __openai_chat_response_async_phaser(
            response: aiohttp.ClientResponse,
            session: Union[aiohttp.ClientSession, None] = None,
            stream_pattern: bool = True,
            details_log: bool = False,
    ) -> ChatPayload:
        """
        这是用于处理: 由<aiohttp.ClientResponse._requests>发起, 由openai框架返回的, chat-response, 的隐藏方法

        :param response: aiohttp发起的, openai框架返回的, chat-response
        :param session: 外围loop循环创建的aiohttp.ClientSession. 端到端流程中, loop标记必须保持一致
        :param stream_pattern: <response>是否为流式报文. 默认为 True
        :param details_log: 详情日志开关. 默认为False

        :return: {"reason": "<模型推理内容>", "result": "<模型输出结果>"}
        """
        try:
            # 非流式调用
            if not stream_pattern:
                _json_response = await response.json()

                _json_reason = _json_response.get('choices')[0].get('reason')
                _json_result = _json_response['choices'][0]['message'].get('content')

            # 流式调用
            else:
                if not session:
                    raise RuntimeError(f"Streaming-Pattern must be used with param <session>, got {session}")

                _stream_response = await AsyncRequest.__openai_stream_chat_response_async_processor(
                    response=response,
                    details_log=details_log
                )

                await session.close()

                _json_reason = _stream_response.get('reason')
                _json_result = _stream_response.get('result')

            if details_log:
                logger.info(f"ReasoningContent: {_json_reason}. \n"
                            f"ResultContent: {_json_result}")

            chat_payload = ChatPayload(reason=_json_reason, result=_json_result)

        except Exception as e:
            logger.exception(f"TraceBack for {e}")
            chat_payload = ChatPayload(reason="ERROR", result=str(e))

        return chat_payload

    @staticmethod
    async def async_invoke_openai(
            url: str,
            model_id: str,
            context: str,
            access_token: str = "",
            endpoint: OpenAiEndpoint = OpenAiEndpoint.chat,
            *,
            session: Union[aiohttp.ClientSession, None] = None,
            method: str = "POST",
            stream_pattern: bool = True,
            headers: Union[dict, None] = None,
            param: Any = None,
            json_data: Union[dict, None] = None,
            messages: Union[list[dict], None] = None,
            thinking: bool = False,
            tools: Union[list[dict], None] = None,
            temperature: float = 0.0,
            timeout: int = 300,
            details_log: bool = False,
            aiohttp_kwargs: Union[dict, None] = None,
            llm_kwargs: Union[dict, None] = None,
    ) -> ApiPayload:
        """
        这是用于异步调用openai框架部署的LLM-API的方法

        :param url: LLM服务API
        :param model_id: LLM服务模型标识
        :param context: 输入给LLM的文本
        :param access_token: LLM服务API的鉴权认证
        :param endpoint: 请求进行的操作. 默认为 "chat"
        :param session: aiohttp模块的调用实例
        :param method: 调用方式("GET", "POST"). 默认为 "POST"
        :param stream_pattern: 流式调用模式开关. 默认为 True
        :param headers: session._request参数: 请求头. 缺省时将采用标准请求头, 并采用"Authorization"字段进行鉴权
        :param param: session._request参数: param请求体: Query
        :param json_data: session._request参数: json请求体: Any
        :param messages: 输入给LLM的messages. 完整, 多轮的上下文, 请按照openai规范的格式输入. 启用该参数时, <context>参数失效
        :param thinking: 是否允许模型思考 (推理)
        :param tools: 旧名<function_call>. 外挂工具描述, 请按照openai规范的格式输入
        :param temperature: LLM控制参数: 温度. 默认为 0.0
        :param timeout: 超时等待. 默认为300秒
        :param details_log: 详情日志开关. 默认为 False
        :param aiohttp_kwargs: aiohttp.ClientSession._request相关参数. 请采用: {"关键字": 数值} 的字典格式传入
        :param llm_kwargs: 控制LLM的相关参数. 请采用: {"关键字": 数值} 的字典格式传入

        :return:
        {
            "chat": {"reason": "xxx", "result": "xxx"},
            "health": bool,
            "load": int,
            "ping": bool,
            "version": str,
            "success": bool
        }
        """
        api_payload = ApiPayload(
            chat={"reason": "null", "result": "null"},
            health=False,
            load=-1,
            ping=False,
            version="null",
            success=False
        )

        owns_session = session is None
        if owns_session:
            session = aiohttp.ClientSession()

        _response = await AsyncRequest.async_request_openai(
            url=url,
            model_id=model_id,
            context=context,
            access_token=access_token,
            session=session,
            method=method,
            stream_pattern=stream_pattern,
            headers=headers,
            param=param,
            json_data=json_data,
            messages=messages,
            thinking=thinking,
            tools=tools,
            temperature=temperature,
            timeout=timeout,
            aiohttp_kwargs=aiohttp_kwargs,
            llm_kwargs=llm_kwargs
        )

        try:
            if endpoint == "chat":
                _chat_response = await AsyncRequest.__openai_chat_response_async_phaser(
                    response=_response,
                    session=session,
                    stream_pattern=stream_pattern,
                    details_log=details_log
                )
                api_payload["chat"] = _chat_response
                api_payload["success"] = _response.status == 200

            elif endpoint == "health":
                api_payload["health"] = _response.status == 200
                api_payload["success"] = True

            elif endpoint == "load":
                raise NotImplementedError("This feature is not implemented yet.")

            elif endpoint == "ping":
                api_payload["ping"] = _response.status == 200
                api_payload["success"] = True

            elif endpoint == "version":
                raise NotImplementedError("This feature is not implemented yet.")

            else:
                raise NotImplementedError("This feature is not implemented yet.")
        finally:
            if owns_session:
                await session.close()

        return api_payload

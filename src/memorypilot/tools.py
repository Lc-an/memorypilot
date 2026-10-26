"""Scope-bound tools backed by a tiny fictional catalogue."""

from langchain_core.tools import tool

from memorypilot.repository import Repository
from memorypilot.schemas import Scope

HOTELS = [
    {"id": "hz_01", "name": "示例湖畔酒店", "city": "杭州", "price": 420},
    {"id": "hz_02", "name": "示例西湖客栈", "city": "杭州", "price": 650},
    {"id": "sh_01", "name": "示例滨江酒店", "city": "上海", "price": 550},
]


def make_tools(repository: Repository, scope: Scope) -> list:
    @tool
    def search_accommodation(city: str, max_price: float) -> dict:
        """查询本地虚构酒店；max_price 是人民币每晚最高价格，不能用于真实预订。"""
        if max_price <= 0 or max_price > 100000:
            return {"error": "价格范围无效", "results": []}
        return {
            "fixture": True,
            "currency": "CNY",
            "unit": "per_night",
            "results": [
                item for item in HOTELS if item["city"] == city and item["price"] <= max_price
            ],
        }

    @tool
    def read_evidence(source_id: str) -> dict:
        """按来源编号读取当前用户、旅行及实验范围内的原始消息。"""
        evidence = repository.read_evidence(scope, source_id)
        return evidence.model_dump() if evidence else {"error": "来源不存在或不属于当前范围。"}

    return [search_accommodation, read_evidence]

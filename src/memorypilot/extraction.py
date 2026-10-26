"""Reuse LangMem for API-backed fact extraction; keep the mock deliberately narrow."""

import re

from langchain_core.messages import HumanMessage
from langmem import create_memory_manager

from memorypilot.schemas import CandidateFact

INSTRUCTIONS = """只从当前用户消息提取本次旅行的明确要求。
只支持住宿每晚预算、饮食要求、目的地、旅行日期。
不提取问题、假设、助手建议或已经被否定的值。修改时只提取最终有效值。
quote 必须逐字出现在当前用户消息内。不要猜测未明确说明的未来生效时间。
住宿预算仅输出数值字符串，单位为当前示例的人民币每晚。
不要把旅行总预算当成住宿每晚预算。
如果出现未来才生效、针对别人的要求或不明确的作用范围，先不要提取。
"""


class LangMemExtractor:
    def __init__(self, model):
        self.manager = create_memory_manager(
            model,
            schemas=[CandidateFact],
            instructions=INSTRUCTIONS,
            enable_updates=False,
            enable_deletes=False,
        )

    def extract(self, text: str) -> list[CandidateFact]:
        result = self.manager.invoke({"messages": [HumanMessage(content=text)], "max_steps": 1})
        return [item.content for item in result if isinstance(item.content, CandidateFact)]


class MockExtractor:
    """Recognize a few test phrases only; this is not a production language model."""

    def extract(self, text: str) -> list[CandidateFact]:
        if any(marker in text for marker in ["明年", "下个月", "假如", "如果", "小王", "小李"]):
            return []
        candidates = []
        if ("每晚" in text or "住宿" in text) and ("预算" in text or "不超过" in text):
            matches = list(re.finditer(r"(\d+(?:\.\d+)?)\s*元?", text))
            if matches and not any(word in text for word in ["最初", "原来", "多少", "之前"]):
                match = matches[-1]
                candidates.append(
                    CandidateFact(
                        attribute="accommodation_budget_per_night",
                        value=match.group(1),
                        quote=match.group(0),
                    )
                )
        if "不吃海鲜" in text and "不再" not in text:
            candidates.append(CandidateFact(attribute="diet", value="不吃海鲜", quote="不吃海鲜"))
        return candidates

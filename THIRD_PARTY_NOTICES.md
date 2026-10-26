# Third-party notices

## LangGraph ReAct Agent Template

- Source: https://github.com/langchain-ai/react-agent
- Base commit: 87aac0fdcb811d05457314a42418f3fbe139933a
- License: MIT, retained in LICENSE.
- Reused and adapted: src/react_agent model/tool loop, message state, configuration structure, and tests.
- The original README is preserved in docs/UPSTREAM_README.md.

## Runtime dependencies

LangGraph and LangMem use MIT licenses. langchain-deepseek is part of LangChain's MIT-licensed integration packages. Other direct and transitive dependencies retain their respective upstream licenses; exact versions and sources are recorded in uv.lock.

DeepSeek is accessed as an external API service. No model weights are included.

## Fixtures and datasets

The tiny hotel catalogue is fictional application test data created for this project. No TravelPlanner or MemoryArena source code or full datasets have been copied into the runtime.

The documents under docs/ contain planning references. Referencing a project does not mean its complete implementation or dataset has been redistributed.

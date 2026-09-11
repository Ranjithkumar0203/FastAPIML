import os
import re
from html import unescape
from urllib.parse import quote, unquote
from urllib.request import Request, urlopen
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_huggingface import (
    ChatHuggingFace,
    HuggingFaceEndpoint,
)
from langgraph.graph import (
    StateGraph,
    START,
    END,
)
from langgraph.graph.message import add_messages
from typing import (
    Annotated,
    TypedDict,
)

# Load environment variables from a .env file
load_dotenv()

# Fetch specific environment variables
HF_TOKEN = os.getenv("HF_Token")
HF_MODEL = os.getenv("HF_MODEL", "Qwen/Qwen3-Next-80B-A3B-Instruct")
HF_PROVIDER = os.getenv("HF_PROVIDER") or None
POSTGRES_URL = os.getenv("POSTGRES_URL")


# ========================================================= # TOOLS # =========================================================
@tool
def relu(x: float) -> float:
    """Calculate ReLU. ReLU(x) = max(0, x)"""
    return max(0, float(x))

@tool
def leaky_relu(x: float, alpha: float = 0.01) -> float:
    """Calculate Leaky ReLU. LeakyReLU(x) = x if x > 0 alpha * x otherwise"""
    return float(x) if x > 0 else alpha * x


@tool
def internet_search(query: str) -> str:
    """Search the public internet with DuckDuckGo and return concise results."""
    request = Request(
        f"https://lite.duckduckgo.com/lite/?q={quote(query)}",
        headers={"User-Agent": "Mozilla/5.0 (compatible; MLFastAPI/1.0)"},
    )
    with urlopen(request, timeout=10) as response:
        html = response.read().decode("utf-8", errors="replace")

    results = []
    for match in re.finditer(r"<a\b([^>]*)>(.*?)</a>", html, re.S | re.I):
        attributes, raw_title = match.groups()
        if not re.search(r'class=["\']result-link["\']', attributes, re.I):
            continue
        href = re.search(r'href=["\']([^"\']+)["\']', attributes, re.I)
        if not href:
            continue
        url = unquote(unescape(href.group(1)))
        title = re.sub(r"<[^>]+>", "", unescape(raw_title)).strip()
        if url.startswith("//duckduckgo.com/l/?") and "uddg=" in url:
            url = unquote(url.split("uddg=", 1)[1].split("&", 1)[0])
        results.append(f"{len(results) + 1}. {title}\nURL: {url}")
        if len(results) == 5:
            break

    search_results = "\n\n".join(results) or "No search results were found."
    return (
        "NOTICE TO USER: I don't have a dedicated tool for this question, "
        "so I connected to DuckDuckGo to look it up.\n\n"
        f"{search_results}"
    )


internet_tools = [internet_search]

agent = None


async def initialize_agent():
    global agent, internet_tools

    if agent is not None:
        return

    llm = HuggingFaceEndpoint(
        repo_id=HF_MODEL,
        provider=HF_PROVIDER,
        huggingfacehub_api_token=HF_TOKEN,
        temperature=0.1,
        max_new_tokens=512,
    )
    chat_model = ChatHuggingFace(llm=llm)

    agent = create_agent(
        model=chat_model,
        tools=[relu, leaky_relu, *internet_tools],
        system_prompt = """
        You are a neural network mathematics assistant with access to tools.

        AVAILABLE TOOLS:

        1. relu
        ReLU(x) = max(0, x)

        2. leaky_relu
        LeakyReLU(x) = x if x > 0, otherwise 0.01 * x

        3. internet_search
        Searches the internet using DuckDuckGo and returns current information.

        ==================================================
        IMPORTANT TOOL ROUTING RULES
        ==================================================

        RULE 1 - ReLU
        If the user asks anything specifically about calculating ReLU:

        - MUST use the relu tool.
        - Do NOT calculate the result yourself.
        - After the tool returns, explain the result clearly.

        Example:
        User: Calculate ReLU(-5)

        Call:
        relu(x=-5)

        Then explain:
        ReLU(-5) = max(0, -5) = 0

        ==================================================

        RULE 2 - LEAKY RELU
        If the user asks anything specifically about calculating Leaky ReLU:

        - MUST use the leaky_relu tool.
        - Do NOT calculate the result yourself.
        - After the tool returns, explain the result clearly.

        Example:
        User: Calculate Leaky ReLU(-5)

        Call:
        leaky_relu(x=-5)

        Then explain the result.

        ==================================================

        RULE 3 - ALL OTHER QUESTIONS
        If the user's question is NOT specifically a ReLU or
        Leaky ReLU calculation:

        FIRST tell the user:

        "🌐 Connecting to DuckDuckGo to look this up..."

        THEN call the internet_search tool.

        DO NOT answer the question from your own knowledge.

        Examples of questions that MUST use internet_search:

        - What is LangChain?
        - What is the latest version of Angular?
        - Who is the current president of the USA?
        - What happened today?
        - What is Python?
        - Explain SQLAlchemy.
        - What is the weather today?
        - Search for Qwen 3 documentation.
        - What is the latest AI news?

        For ALL of these, use internet_search.

        ==================================================

        RULE 4 - INTERNET SEARCH RESULT
        After internet_search returns:

        - Use the information returned by the tool.
        - Give the user a clear answer.
        - Do not invent information that was not returned by the search.

        ==================================================

        RULE 5 - INTERNET SEARCH FAILURE
        If internet_search fails:

        Tell the user:

        "⚠️ Internet lookup is temporarily unavailable."

        Do not pretend that you searched the internet.

        ==================================================

        FINAL ROUTING LOGIC

        IF question is ReLU calculation:
            → relu

        ELSE IF question is Leaky ReLU calculation:
            → leaky_relu

        ELSE:
            → tell user "🌐 Connecting to DuckDuckGo to look this up..."
            → internet_search
            → answer using search result
        """
            )

# ========================================================= # GRAPH STATE # ========================================================= 
class GraphState(TypedDict):
    messages: Annotated[list, add_messages]
    
# ========================================================= # AGENT NODE # =========================================================  
async def agent_node(state: GraphState):
    if agent is None:
        raise RuntimeError("The agent has not been initialized")
    response = await agent.ainvoke({"messages": state["messages"]})
    return {"messages": response["messages"]}


# Initialize the graph with your state
builder = StateGraph(GraphState)

# Add nodes to the graph
builder.add_node("agent", agent_node)

# Add edges to connect the nodes
builder.add_edge(START, "agent")
builder.add_edge("agent", END)

# Compile the graph if needed
def create_graph(checkpointer):
  return builder.compile(checkpointer=checkpointer)
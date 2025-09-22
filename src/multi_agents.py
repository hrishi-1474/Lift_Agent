# Import Libraries
import warnings

warnings.filterwarnings("ignore")
import functools
import traceback
import os
import pandas as pd
import json
from typing import TypedDict, Annotated
from typing import Dict, Any
import re
import copy

# LangGraph imports
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import add_messages

# LangChain imports
from langchain_core.messages import (
    AnyMessage,
    SystemMessage,
    HumanMessage,
    ToolMessage,
    AIMessage,
)
from langchain.output_parsers.openai_functions import JsonOutputFunctionsParser
from langchain.output_parsers.structured import StructuredOutputParser, ResponseSchema
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory, ConversationSummaryBufferMemory
from langchain_core.tools import Tool
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain.callbacks.base import BaseCallbackHandler

# Import Support Files
from supervisor import (
    supervisor_prompt,
    supervisor_function_def,
    tier_mapping_system_prompt,
    tier_mapping_user_prompt,
)
from helpers import execute_analysis
from insight_prompt import (
    insight_agent_prompt,
    insight_agent_expense_tool_prompt,
    insight_agent_budget_tool_prompt,
    insight_agent_graph_merger_tool_prompt,
)


def extract_content_within_tag(text: str, tag: str) -> str:
    """
    Extract content inside <tag>...</tag> tags.
    If no such tags exist, return the original text.
    """
    match = re.search(rf"<{tag}>(.*?)</{tag}>", text, flags=re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def get_string_formatted_tier_mapping(df, tier_1_col, tier_2_col, tier_3_col):
    final_str = ""
    for tier_1_item, tier_1_grp in df.groupby(tier_1_col):
        if final_str == "":
            final_str = f"- {tier_1_item}"
        else:
            final_str = f"{final_str}\n- {tier_1_item}"
        for tier_2_item, tier_2_grp in tier_1_grp.groupby(tier_2_col):
            final_str = f"{final_str}\n\t- {tier_2_item}"
            for _, row in tier_2_grp.iterrows():
                final_str = f"{final_str}\n\t\t- {row[tier_3_col]}"
    return final_str


# ------------------------------
# Custom Callback for Step Tracing
# ------------------------------
class StepRecorder(BaseCallbackHandler):
    def __init__(self):
        self.steps = []

    def on_agent_action(self, action, **kwargs):
        self.steps.append(
            {
                "thought": action.log,
                "tool": action.tool,
                "tool_input": action.tool_input,
            }
        )

    def on_tool_end(self, output, **kwargs):
        if self.steps:
            self.steps[-1]["observation"] = output

    def on_agent_finish(self, finish, **kwargs):
        self.steps.append({"final_answer": finish.log})


class MultiAgentSystem:

    def __init__(
        self,
        model_name,
        api_key,
        expense_dataset,
        budget_dataset,
        plot_path,
    ):
        # Initialise model
        self.llm = ChatOpenAI(model=model_name, api_key=api_key, temperature=0)
        # Datasets
        self.expense_dataset = expense_dataset
        self.budget_dataset = budget_dataset
        self.insight_agent_prompt = insight_agent_prompt.format(
            expense_df=expense_dataset.head().to_string(),
            budget_df=budget_dataset.head().to_string(),
        )
        self.insight_agent_expense_tool_prompt = (
            insight_agent_expense_tool_prompt.format(
                expense_df=expense_dataset.head().to_string()
            )
        )
        self.insight_agent_budget_tool_prompt = insight_agent_budget_tool_prompt.format(
            budget_df=budget_dataset.head().to_string()
        )
        self.insight_agent_graph_merger_tool_prompt = (
            insight_agent_graph_merger_tool_prompt
        )
        self.tier_mapping_system_prompt = tier_mapping_system_prompt
        self.tier_mapping_user_prompt = tier_mapping_user_prompt
        # Tier mapping string
        self.tier_mapping_str = get_string_formatted_tier_mapping(
            pd.concat([expense_dataset, budget_dataset]).drop_duplicates(
                subset=["Tier 1", "Tier 2", "Tier 3"]
            ),
            tier_1_col="Tier 1",
            tier_2_col="Tier 2",
            tier_3_col="Tier 3",
        )
        # Execute analysis
        self.execute_analysis = execute_analysis
        # Plot path
        # Create folder if not available
        os.makedirs(plot_path, exist_ok=True)
        self.plot_path = plot_path
        # Initialise memory with summarisation capability
        # Supervisor Agent Memory
        self.supervisor_agent_memory = ConversationSummaryBufferMemory(
            llm=self.llm,
            memory_key="chat_history",
            return_messages=True,
            max_token_limit=500,  # When token limit is exhausted, automatic summarization is triggered
        )
        # Insight Agent Memory
        self.insight_agent_memory = ConversationSummaryBufferMemory(
            llm=self.llm,
            memory_key="chat_history",
            return_messages=True,
            max_token_limit=500,  # When token limit is exhausted, automatic summarization is triggered
        )
        # Supervisor chain
        self.supervisor_chain = (
            supervisor_prompt
            | self.llm.bind_functions(
                functions=[supervisor_function_def], function_call="route"
            )
            | JsonOutputFunctionsParser()
        )
        # Initialise graph
        self.graph = self.get_workflow_graph()

    # Tools
    def expense_data_tool(self, query: str) -> Dict[str, Any]:
        # Prompt template
        prompt_temp = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    self.insight_agent_expense_tool_prompt,
                ),  # This contains the data description and the question
                MessagesPlaceholder(variable_name="messages"),
            ]
        )
        # Invoke LLM
        result = self.llm.invoke(
            prompt_temp.invoke({"messages": [HumanMessage(content=query)]})
        )
        # Response
        response = self.execute_analysis.invoke(
            {
                "input_dict": {"df": self.expense_dataset},
                "response_text": result.content,
                "PLOT_DIR": self.plot_path,
            }
        )
        # Keys present in response (All these extracted from the llm response)
        # approach
        # answer
        # figure
        # code
        # chart_code
        return response

    def budget_data_tool(self, query: str) -> Dict[str, Any]:
        # Prompt template
        prompt_temp = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    self.insight_agent_budget_tool_prompt,
                ),  # This contains the data description and the question
                MessagesPlaceholder(variable_name="messages"),
            ]
        )
        # Invoke LLM
        result = self.llm.invoke(
            prompt_temp.invoke({"messages": [HumanMessage(content=query)]})
        )
        # Response
        response = self.execute_analysis.invoke(
            {
                "input_dict": {"df": self.budget_dataset},
                "response_text": result.content,
                "PLOT_DIR": self.plot_path,
            }
        )
        # Keys present in response (All these extracted from the llm response)
        # approach
        # answer
        # figure
        # code
        # chart_code
        return response

    def graph_merger_tool(self, query: str) -> Dict[str, Any]:
        # Prompt template
        prompt_temp = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    self.insight_agent_graph_merger_tool_prompt,
                ),  # This contains the description
                MessagesPlaceholder(variable_name="messages"),
            ]
        )
        # Invoke LLM
        result = self.llm.invoke(
            prompt_temp.invoke(
                {
                    "messages": [
                        HumanMessage(
                            content=f"Output(s) from Expense/Budget Tool: {query}"
                        )
                    ]
                }
            )
        )
        # Response
        response = self.execute_analysis.invoke(
            {
                "input_dict": {},
                "response_text": result.content,
                "PLOT_DIR": self.plot_path,
            }
        )
        # Keys present in response (All these extracted from the llm response)
        # approach
        # answer
        # figure
        # code
        # chart_code
        return response

    def extract_tier_hierarchy(self, query):
        # Define the prompt with placeholders for variables
        tier_mapping_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self.tier_mapping_system_prompt.strip()),  # System message
                (
                    "human",
                    self.tier_mapping_user_prompt.strip(),
                ),  # Human question placeholder
            ]
        )
        # Invoke the LLM
        result = self.llm.invoke(
            tier_mapping_prompt.invoke(
                {
                    "tier_hierarchy": self.tier_mapping_str,
                    "user_question": query,
                }
            )
        )
        # Parse the output
        try:
            # Parse json
            json_input = re.sub(
                r"^```json\s*|\s*```$", "", result.content.strip(), flags=re.MULTILINE
            )
            # Get Python dict
            parsed = json.loads(json_input)
            return parsed
        except Exception as e:
            print(f"{e} \n{traceback.format_exc()}")
            return None

    # Agent
    def supervisor_agent(self, query, chat_history):

        # Invoke chain with enhanced context
        result = self.supervisor_chain.invoke(
            {
                "question": query,  # Human question
                "chat_history": chat_history,  # Chat history placeholder
            }
        )
        if result["next"] == "SELF_RESPONSE":
            # Response provided by supervisor
            if "direct_response" in result:
                # Get the direct response, if not available get the thought process
                return_response = ""
                if result.get("direct_response"):
                    if result.get("direct_response") != "":
                        return_response = result["direct_response"]
                    else:
                        # Check for thought process
                        if result.get("thought_process"):
                            if result.get("thought_process") != "":
                                return_response = result["thought_process"]
                elif result.get("thought_process"):
                    if result.get("thought_process") != "":
                        return_response = result["thought_process"]

                # Direct response
                return {
                    "result": result,
                    "messages": [AIMessage(content=return_response, name="supervisor")],
                    "next": "FINISH",
                    "type": "direct_response",
                }
            else:
                # No direct response even if supervisor is tasked with answering the question
                return {
                    "result": result,
                    "messages": [
                        AIMessage(
                            content=result.get(
                                "thought_process",
                                "I do not understand your question. Please provide a different question.",
                            ),
                            name="supervisor",
                        )
                    ],
                    "next": "FINISH",
                    "type": "no_direct_response",
                }
        else:
            # Call the Tier hierarchy extractor
            tier_mapping_query = result.get("enriched_question")
            # Check for enriched question
            if tier_mapping_query:
                # Get Tier mapping information
                tier_mapping_response = self.extract_tier_hierarchy(
                    query=tier_mapping_query
                )
                print("Tier mapping response:")
                print(tier_mapping_response)
                print(110 * "-")
                # Check if mapping information is needed
                if tier_mapping_response:
                    if tier_mapping_response.get("mapping_needed", False) == True:
                        if tier_mapping_response.get("results"):
                            json_output = tier_mapping_response["results"]
                            # Update supervisor memory
                            message = f"For query '{tier_mapping_query}', following tier(s) are relevant: {json_output}"
                            self.supervisor_agent_memory.chat_memory.add_user_message(
                                message
                            )
                        else:
                            message = f"For query '{tier_mapping_query}', there seems to be no relevant Tier 1/2/3 items."
                            tier_mapping_error_message = "Unable to get the relevant Tier 1/2/3 items for the mentioned query. Please provide appropriate mapping."
                            result["tier_mapping_error"] = tier_mapping_error_message
                            # Update supervisor memory
                            self.supervisor_agent_memory.chat_memory.add_user_message(
                                message
                            )
                            return {
                                "result": result,
                                "messages": [
                                    AIMessage(content=message, name="supervisor")
                                ],
                                "next": "FINISH",
                                "type": "tier_mapping_error",
                            }
            routing_message = result.get("thought_process", "N/A")
            return {
                "result": result,
                "messages": [AIMessage(content=routing_message, name="supervisor")],
                "next": result["next"],
                "type": "agent",
            }

    # Agent
    def insight_agent(self):
        # Tools for this insight agent
        expense_tool = Tool.from_function(
            func=self.expense_data_tool,
            name="analyze_expense_data",
            description="Analyze expense data (both historical and current year) based on the question.",
        )
        budget_tool = Tool.from_function(
            func=self.budget_data_tool,
            name="analyze_budget_data",
            description="Analyze budget data based on the question.",
        )
        graph_merge_tool = Tool.from_function(
            func=self.graph_merger_tool,
            name="graph_merger_tool",
            description="Combines outputs from Expense and Budget tools into a single merged answer_dict, consolidated insight, and one unified plotly chart.",
        )
        # Tools
        tools = [expense_tool, budget_tool, graph_merge_tool]

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self.insight_agent_prompt),
                MessagesPlaceholder("history"),  # Past user/agent conversation
                ("human", "{input}"),
                MessagesPlaceholder("agent_scratchpad"),  # Tool reasoning trace
            ]
        )
        agent = create_openai_functions_agent(self.llm, tools, prompt)
        return AgentExecutor(
            agent=agent, tools=tools, verbose=True, return_intermediate_steps=True
        )

    # Function to create the workflow graph
    def get_workflow_graph(
        self,
    ):

        # Supervisor Agent Node
        def supervisor_step(state: Dict[str, Any]):
            # When supervisor agent is run
            if "question" in state:
                # Memory
                # Messages, truncated/summarized if needed
                memory_vars = self.supervisor_agent_memory.load_memory_variables({})
                result = self.supervisor_agent(
                    state["question"], memory_vars["chat_history"]
                )
                # Add input to supervisor in the memory
                # Input message
                self.supervisor_agent_memory.chat_memory.add_user_message(
                    state["question"]
                )
                # Output message
                self.supervisor_agent_memory.chat_memory.add_ai_message(
                    result["messages"][0].content
                )
            # When graph chain is run
            elif "output" in state:
                # Memory
                # Messages, truncated/summarized if needed
                memory_vars = self.supervisor_agent_memory.load_memory_variables({})
                output_from_agent = extract_content_within_tag(
                    state["output"], "answer"
                )
                result = self.supervisor_agent(
                    f"Final answer by '{state['agent']}' agent: {output_from_agent}",
                    memory_vars["chat_history"],
                )
                # Add output to supervisor in the memory
                # Input message
                self.supervisor_agent_memory.chat_memory.add_user_message(
                    f"Final answer by '{state['agent']}' agent: {output_from_agent}",
                )
                # Output message
                self.supervisor_agent_memory.chat_memory.add_ai_message(
                    result["messages"][0].content
                )
            else:
                print(f"Invalid output received from agent {state['agent']}")
                result = copy.deepcopy(state)
            return result

        # Insight Agent Node
        def insight_step(state: Dict[str, Any]):
            question = None
            # Enriched question
            if state.get("enriched_question"):
                question = state["enriched_question"]
            else:
                if state.get("result"):
                    if state["result"].get("enriched_question"):
                        question = state["result"]["enriched_question"]
            # If question is not available
            if question is not None:
                agent = self.insight_agent()
                # Memory
                # Messages, truncated/summarized if needed
                memory_vars = self.insight_agent_memory.load_memory_variables({})
                # Attach custom step recorder
                recorder = StepRecorder()
                # Invoke the agent
                result = agent.invoke(
                    {
                        "input": f"{question}",
                        "history": memory_vars["chat_history"],
                    },
                    config={"callbacks": [recorder]},
                )
                # Add to memory the input and output
                # Input message
                self.insight_agent_memory.chat_memory.add_user_message(result["input"])
                # Output messsage
                self.insight_agent_memory.chat_memory.add_ai_message(result["output"])
                result["recorder_steps"] = recorder.steps
                result["agent"] = "Insight Agent"
                return result
            else:
                print("Insight Agent did not receive the enriched question")
                result["final_answer"] = (
                    "I did not receive the question from the Supervisor. I'm unable to provide the answer"
                )
                result["agent"] = "Insight Agent"
                return result

        # Build the workflow graph
        workflow = StateGraph(Dict[str, Any])
        workflow.add_node("Insight Agent", insight_step)
        workflow.add_node("supervisor", supervisor_step)

        # Workers always return to supervisor
        workflow.add_edge("Insight Agent", "supervisor")

        # Supervisor decides the next step
        # Add conditional edges
        conditional_map = {"Insight Agent": "Insight Agent", "FINISH": END}
        workflow.add_conditional_edges(
            "supervisor", lambda x: x["next"], conditional_map
        )
        workflow.set_entry_point("supervisor")

        # Use the passed memory instance
        return workflow.compile()

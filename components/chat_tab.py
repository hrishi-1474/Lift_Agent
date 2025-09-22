import streamlit as st
from streamlit_extras.stylable_container import stylable_container
import random
import copy
import os
import pandas as pd
from langchain.schema import HumanMessage
from langgraph.graph.message import add_messages

# Import files
from .session_state_manager import init_session_state

init_session_state()
from .ui_helpers import (
    warning_box,
    chat_avatars,
    display_saved_plot,
    add_text,
    container_css_styles,
    chat_avatars_color_bg,
    messages_to_text,
    get_base64_image,
    display_content_type_1,
    display_content_type_2,
)
from src.multi_agents import MultiAgentSystem, extract_content_within_tag

text_color = "#E30A13"
chat_container_css_styles = """
    {
        background-color: #FFFFFF;
        padding-top: 1em;
        padding-right: 1em;
        padding-bottom: 1em;
        padding-left: 1em;
        border-radius: 0.5em;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
        height: 530px; /* Fixed height */
        overflow-y: auto; /* Scroll if content exceeds */
    }
"""

default_supervisor_expanded = False
default_insight_agent_expanded = False
show_answer = False


def render_chat_tab():
    # Header container
    with stylable_container(
        key="chat_title",
        css_styles=container_css_styles,
    ):
        c1, c2, _, c3 = st.columns([0.2, 0.45, 0.12, 0.18], vertical_alignment="top")
        with c1:
            add_text(text="Start Chat Session:", text_color=text_color, size=5)
        with c2:
            if st.session_state["use_backend_data"] == True:
                possible_options = ["Expense", "Budget"]
                select_options = st.multiselect(
                    "Select the dataset(s)",
                    possible_options,
                    default=possible_options,
                    placeholder="Select dataset",
                    label_visibility="collapsed",
                    disabled=True,
                )
            else:
                possible_options = []
                if st.session_state["expense_data_file_name"]:
                    possible_options.append("Expense")
                if st.session_state["budget_data_file_name"]:
                    possible_options.append("Budget")
                select_options = st.multiselect(
                    "Select the dataset(s)",
                    possible_options,
                    default=possible_options,
                    placeholder="Select dataset",
                    label_visibility="collapsed",
                    disabled=True,
                )
            st.markdown("")
        with c3:
            chat_button = st.button("Create Chat Session", icon=":material/add_circle:")
            # If chat button is hit
            if chat_button:
                # Reset session
                st.session_state["messages"] = []
                st.session_state["show_chat_session"] = True
                st.session_state["agent_obj"] = None
                if st.session_state["use_backend_data"] == True:
                    st.session_state["agent_obj"] = MultiAgentSystem(
                        model_name=st.session_state["model_name"],
                        api_key=st.session_state["open_ai_key"],
                        expense_dataset=pd.DataFrame(
                            st.session_state["backend_expense_data"]
                        ),
                        budget_dataset=pd.DataFrame(
                            st.session_state["backend_budget_data"]
                        ),
                        plot_path=st.session_state["plot_path"],
                    )
                else:
                    if (
                        st.session_state["expense_data_file_name"]
                        and st.session_state["budget_data_file_name"]
                    ):
                        st.session_state["agent_obj"] = MultiAgentSystem(
                            model_name=st.session_state["model_name"],
                            api_key=st.session_state["open_ai_key"],
                            expense_dataset=pd.DataFrame(
                                st.session_state["expense_data"]
                            ),
                            budget_dataset=pd.DataFrame(
                                st.session_state["budget_data"]
                            ),
                            plot_path=st.session_state["plot_path"],
                        )
    if st.session_state["agent_obj"]:
        # Chat session container
        if st.session_state["show_chat_session"]:
            with stylable_container(
                key="chat_session",
                css_styles=chat_container_css_styles,
            ):
                # Chat container
                chat_container = st.container()
                with chat_container:
                    for message in st.session_state["messages"]:
                        if message["role"] == "user":
                            with st.chat_message(
                                "user2", avatar=chat_avatars["User_ChatGPT"]
                            ):
                                display_content_type_1(
                                    message["content"],
                                    chat_avatars_color_bg["User_ChatGPT"],
                                )
                        elif message["role"] == "assistant":
                            if message["error_response"] == True:
                                with st.chat_message(
                                    "assistant",
                                    avatar=chat_avatars["Error"],
                                ):
                                    display_content_type_1(
                                        message["content"],
                                        chat_avatars_color_bg["Error"],
                                    )
                            else:
                                if message["agent"] == "supervisor":
                                    with st.chat_message(
                                        "assistant",
                                        avatar=chat_avatars.get(
                                            "Supervisor_ChatGPT",
                                            chat_avatars["Assistant"],
                                        ),
                                    ):
                                        # Expander settings
                                        supervisor_expanded = copy.deepcopy(
                                            default_supervisor_expanded
                                        )
                                        if message["result"]["type"] in [
                                            "direct_response",
                                            "no_direct_response",
                                            "tier_mapping_error",
                                        ]:
                                            supervisor_expanded = True
                                        with st.expander(
                                            "Supervisor Agent Response",
                                            expanded=supervisor_expanded,
                                        ):
                                            supervisor_content = ""
                                            if message["result"]["type"] == "agent":
                                                supervisor_content = (
                                                    "<b>Thought Process:</b>&nbsp;&nbsp;"
                                                    + str(
                                                        message["result"]["result"][
                                                            "thought_process"
                                                        ]
                                                    )
                                                    + "<br><br><b>Enriched Question:</b>&nbsp;&nbsp;"
                                                    + str(
                                                        message["result"]["result"][
                                                            "enriched_question"
                                                        ]
                                                    )
                                                )
                                            elif (
                                                message["result"]["type"]
                                                == "direct_response"
                                            ):
                                                supervisor_content = (
                                                    "<b>Thought Process:</b>&nbsp;&nbsp;"
                                                    + str(
                                                        message["result"]["result"][
                                                            "thought_process"
                                                        ]
                                                    )
                                                    + "<br><br><b>Direct Response:</b>&nbsp;&nbsp;"
                                                    + str(
                                                        message["result"]["messages"][
                                                            0
                                                        ].content
                                                    )
                                                )
                                            elif (
                                                message["result"]["type"]
                                                == "no_direct_response"
                                            ):
                                                supervisor_content = (
                                                    "<b>Thought Process:</b>&nbsp;&nbsp;"
                                                    + str(
                                                        message["result"]["result"][
                                                            "thought_process"
                                                        ]
                                                    )
                                                    + "<br><br><b>Thought Process/Response:</b>&nbsp;&nbsp;"
                                                    + str(
                                                        message["result"]["messages"][
                                                            0
                                                        ].content
                                                    )
                                                )
                                            elif (
                                                message["result"]["type"]
                                                == "tier_mapping_error"
                                            ):
                                                supervisor_content = (
                                                    "<b>Thought Process:</b>&nbsp;&nbsp;"
                                                    + str(
                                                        message["result"]["result"][
                                                            "thought_process"
                                                        ]
                                                    )
                                                    + "<br><br><b>Tier Mapping Error:</b>&nbsp;&nbsp;"
                                                    + str(
                                                        message["result"]["result"][
                                                            "tier_mapping_error"
                                                        ]
                                                    )
                                                )

                                            # Supervisor will return a though process and enriched question
                                            display_content_type_1(
                                                supervisor_content,
                                                chat_avatars_color_bg.get(
                                                    "Supervisor_ChatGPT",
                                                    chat_avatars_color_bg["Assistant"],
                                                ),
                                                margin_bottom="1em",
                                            )
                                elif message["agent"] == "Insight Agent":
                                    # Recorder steps
                                    recorder_steps = message["result"].get(
                                        "recorder_steps", []
                                    )
                                    # Get the non-answer steps which have some oberservation within them
                                    non_answer_steps = []
                                    answer_step = None
                                    for step in recorder_steps:
                                        # Observation is valid and the answer is not None or blank then proceed with showing the approach
                                        if step.get("observation"):
                                            non_answer_steps.append(step)
                                        else:
                                            answer_step = step

                                    # Show the non-answer steps
                                    if len(non_answer_steps) > 0:
                                        display_response = ""
                                        # Loop through the steps to put in one container
                                        for step in non_answer_steps:
                                            # Approach
                                            approach = step["observation"]["approach"]
                                            # Answer
                                            answer = step["observation"]["answer"]
                                            # Tool Used
                                            tool_used = (
                                                "Expense Tool"
                                                if step["tool"]
                                                == "analyze_expense_data"
                                                else (
                                                    "Budget Tool"
                                                    if step["tool"]
                                                    == "analyze_budget_data"
                                                    else (
                                                        "Graph Tool"
                                                        if step["tool"]
                                                        == "graph_merger_tool"
                                                        else "N/A"
                                                    )
                                                )
                                            )
                                            if show_answer:
                                                if display_response == "":
                                                    display_response = (
                                                        "<b>Approach:</b>&nbsp;&nbsp;"
                                                        + str(approach)
                                                        + "<br><br><b>Tool(s) Used:</b>&nbsp;&nbsp;"
                                                        + tool_used
                                                        + "<br><br><b>Answer:</b>&nbsp;&nbsp;"
                                                        + str(answer)
                                                    )
                                                else:
                                                    display_response = (
                                                        display_response
                                                        + "<hr>"
                                                        + "<b>Approach:</b>&nbsp;&nbsp;"
                                                        + str(approach)
                                                        + "<br><br><b>Tool(s) Used:</b>&nbsp;&nbsp;"
                                                        + tool_used
                                                        + "<br><br><b>Answer:</b>&nbsp;&nbsp;"
                                                        + str(answer)
                                                    )
                                            else:
                                                if display_response == "":
                                                    display_response = (
                                                        "<b>Approach:</b>&nbsp;&nbsp;"
                                                        + str(approach)
                                                        + "<br><br><b>Tool(s) Used:</b>&nbsp;&nbsp;"
                                                        + tool_used
                                                    )
                                                else:
                                                    display_response = (
                                                        display_response
                                                        + "<hr>"
                                                        + "<b>Approach:</b>&nbsp;&nbsp;"
                                                        + str(approach)
                                                        + "<br><br><b>Tool(s) Used:</b>&nbsp;&nbsp;"
                                                        + tool_used
                                                    )
                                        # Display content
                                        with st.chat_message(
                                            "assistant",
                                            avatar=chat_avatars.get(
                                                "Insight_ChatGPT",
                                                chat_avatars["Assistant"],
                                            ),
                                        ):
                                            with st.expander(
                                                "Insight Agent Approach",
                                                expanded=default_insight_agent_expanded,
                                            ):
                                                display_content_type_1(
                                                    display_response,
                                                    chat_avatars_color_bg.get(
                                                        "Insight_Approach_ChatGPT",
                                                        chat_avatars_color_bg[
                                                            "Assistant"
                                                        ],
                                                    ),
                                                    margin_bottom="1em",
                                                )
                                    # Show the answer step
                                    if answer_step is not None:
                                        with st.chat_message(
                                            "assistant",
                                            avatar=chat_avatars.get(
                                                "Insight_ChatGPT",
                                                chat_avatars["Assistant"],
                                            ),
                                        ):
                                            answer_content = extract_content_within_tag(
                                                answer_step["final_answer"], "answer"
                                            )
                                            graph_content = extract_content_within_tag(
                                                answer_step["final_answer"], "graph"
                                            )
                                            # Split the graphs
                                            # Filter for applicable graph content
                                            filtered_graph_content = [
                                                g.strip()
                                                for g in graph_content.split("|")
                                                if ".json" in g.strip()
                                            ]
                                            if len(filtered_graph_content) == 0:
                                                display_content_type_1(
                                                    "<b>Final Answer:</b><br>"
                                                    + answer_content,
                                                    chat_avatars_color_bg.get(
                                                        "Insight_Answer_ChatGPT",
                                                        chat_avatars_color_bg[
                                                            "Assistant"
                                                        ],
                                                    ),
                                                    margin_bottom="0em",
                                                )
                                            else:
                                                display_content_type_2(
                                                    "<b>Final Answer:</b><br>"
                                                    + answer_content,
                                                    chat_avatars_color_bg.get(
                                                        "Insight_Answer_ChatGPT",
                                                        chat_avatars_color_bg[
                                                            "Assistant"
                                                        ],
                                                    ),
                                                    filtered_graph_content,
                                                )
                    st.markdown("")

            chat_query_container_css_styles = """
                {
                    background-color: #FFFFFF;
                    padding-top: 1em;
                    padding-right: 1em;
                    padding-bottom: 2em;
                    padding-left: 1em;
                    border-radius: 0.5em;
                    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
                }
            """
            with stylable_container(
                key="chat_query_session",
                css_styles=chat_query_container_css_styles,
            ):
                # --- Chat input ---
                if prompt := st.chat_input(
                    "I'm your assistant. Ask me whenever you're ready!"
                ):

                    # 1️⃣ Show user message immediately
                    st.session_state.messages.append(
                        {
                            "role": "user",
                            "agent": "User",
                            "content": prompt,
                            "result": [],
                            "next": "supervisor",
                            "call_bot": True,
                            "error_response": False,
                        }
                    )
                    st.rerun()  # Refresh UI so user message appears instantly

            # 2️⃣ After rerun, detect if last message is user and reply is missing
            # Previous query must be user query
            if (
                st.session_state.messages
                and st.session_state.messages[-1]["call_bot"] == True
                and st.session_state.messages[-1]["error_response"] == False
            ):
                previous_message_dict = st.session_state.messages[-1]

                # Get response from Bot
                with chat_container:
                    avatar_icon = chat_avatars["Assistant"]
                    if previous_message_dict["next"] == "supervisor":
                        avatar_icon = chat_avatars["Supervisor_ChatGPT"]
                    elif previous_message_dict["next"] == "Insight Agent":
                        avatar_icon = chat_avatars["Insight_ChatGPT"]
                    with st.chat_message(
                        "assistant",
                        avatar=avatar_icon,
                    ):
                        with st.spinner("Generating..."):
                            try:
                                if previous_message_dict["next"] == "supervisor":
                                    result = (
                                        st.session_state["agent_obj"]
                                        .graph.nodes[previous_message_dict["next"]]
                                        .invoke(
                                            {
                                                "question": previous_message_dict[
                                                    "content"
                                                ]
                                            }
                                        )
                                    )
                                elif previous_message_dict["next"] == "Insight Agent":
                                    result = (
                                        st.session_state["agent_obj"]
                                        .graph.nodes[previous_message_dict["next"]]
                                        .invoke(
                                            {
                                                "enriched_question": previous_message_dict[
                                                    "result"
                                                ][
                                                    "result"
                                                ][
                                                    "enriched_question"
                                                ]
                                            }
                                        )
                                    )
                                    result["next"] = "FINISH"
                            except Exception as e:
                                # Add the message
                                st.session_state.messages.append(
                                    {
                                        "role": "assistant",
                                        "agent": previous_message_dict[
                                            "next"
                                        ],  # Agent answering the query
                                        "content": f"Error in bot response. Restart the chat session.\nError traceback: {e}",
                                        "result": [],
                                        "next": None,
                                        "call_bot": False,
                                        "error_response": True,
                                    }
                                )
                                st.rerun()
                # Check if last previous messages are from bot (Not more than 10 responses must be from bot)
                reversed_messages = st.session_state.messages[::-1]
                # Base case
                current = reversed_messages[0]
                i = 1
                counter = 0
                while i < len(reversed_messages):
                    if current == reversed_messages[i]:
                        counter += 1
                        i += 1
                    else:
                        break

                # Add the message
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "agent": previous_message_dict[
                            "next"
                        ],  # Agent answering the query
                        "content": None,
                        "result": result,
                        "next": result["next"],
                        "call_bot": (
                            True
                            if (result["next"] != "FINISH" and counter < 10)
                            else False
                        ),
                        "error_response": False,
                    }
                )
                st.rerun()
    else:
        warning_box("Agent not available!")

# https://github.com/victoryhb/streamlit-option-menu
from streamlit_option_menu import option_menu
import streamlit as st
from PIL import Image
import pandas as pd

# Import files
from .session_state_manager import init_session_state

init_session_state()
from .ui_helpers import get_horizontal_line
from src.multi_agents import MultiAgentSystem


def backend_toggle(previous_state):
    # Previous state
    if st.session_state[previous_state] == False:
        # Do not use backend data
        st.session_state["messages"] = []
        st.session_state["show_chat_session"] = True
        st.session_state["agent_obj"] = None
        if (
            st.session_state["expense_data_file_name"]
            and st.session_state["budget_data_file_name"]
        ):
            st.session_state["agent_obj"] = MultiAgentSystem(
                model_name=st.session_state["model_name"],
                api_key=st.session_state["open_ai_key"],
                expense_dataset=pd.DataFrame(st.session_state["expense_data"]),
                budget_dataset=pd.DataFrame(st.session_state["budget_data"]),
                plot_path=st.session_state["plot_path"],
            )
    else:
        # Use backend data
        st.session_state["messages"] = []
        st.session_state["show_chat_session"] = True
        st.session_state["agent_obj"] = MultiAgentSystem(
            model_name=st.session_state["model_name"],
            api_key=st.session_state["open_ai_key"],
            expense_dataset=pd.DataFrame(st.session_state["backend_expense_data"]),
            budget_dataset=pd.DataFrame(st.session_state["backend_budget_data"]),
            plot_path=st.session_state["plot_path"],
        )


def render_sidebar():
    with st.sidebar:
        logo = Image.open("logo/sigmoid_logo.png")
        c1, c2 = st.columns([0.5, 0.5])
        with c1:
            st.image(logo, width=200)
        logo = Image.open("logo/lift_logo.png")
        with c2:
            st.image(logo, width=200)
        get_horizontal_line(color="#E30A13")
        st.markdown("")
        selected = option_menu(
            menu_title=None,
            options=["Home", "Chat Sessions", "Settings"],
            icons=["house", "chat", "gear"],
            default_index=0,
            orientation="vertical",
            styles={
                "container": {
                    "padding": "0!important",
                    "background-color": "#FFFFFF",
                },
                "nav-link": {
                    "text-align": "left",
                    "margin": "8px",
                    "--hover-color": "#eee",
                    "border-radius": "5em",
                },
                "nav-link-selected": {
                    "background-color": "#FDE5E5",
                    "color": "#DA1E18",
                    "border-radius": "5em",
                    "border": "1px solid #DA1E18",
                },
            },
        )
        get_horizontal_line(color="#E30A13")
        _, c1 = st.columns([0.05, 0.95])
        with c1:
            st.toggle(
                "Use backend data",
                key="use_backend_data",
                on_change=backend_toggle,
                args=("use_backend_data",),
            )
        return selected

import streamlit as st
from streamlit_extras.stylable_container import stylable_container
from .ui_helpers import container_css_styles, add_text

text_color = "#E30A13"


def render_settings_tab():
    with stylable_container(
        key="settings_main",
        css_styles=container_css_styles,
    ):
        add_text(text="Settings", text_color=text_color, size=4)
        st.markdown("")
        api_key = st.text_input(
            "OpenAI API Key", type="password", value=st.session_state["open_ai_key"]
        )
        st.write("")
        model_name = st.selectbox(
            "LLM Model",
            ["gpt-4", "gpt-4o", "gpt-4o-mini", "gpt-3.5"],
            index=["gpt-4", "gpt-4o", "gpt-4o-mini", "gpt-3.5"].index(
                st.session_state["model_name"]
            ),
        )
        st.markdown("")
        _, c1 = st.columns([0.92, 0.08])
        with c1:
            if st.button("Submit"):
                st.session_state["model_name"] = model_name
                st.session_state["open_ai_key"] = api_key
        st.write("")

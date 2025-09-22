"""
Created on Fri Aug 8 2025

@author: Nitish Sawant
"""

# Steps to run the app
# streamlit run app.py

# Import Libraries
import warnings

warnings.filterwarnings("ignore")
import streamlit as st

import pandas as pd
import os
import yaml

import sys

sys.path.append("src")

# Page config
st.set_page_config(
    page_title="PepsiCo - LIFT Bot",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Import files
from components.session_state_manager import init_session_state

init_session_state()

from components.sidebar import render_sidebar
from components.home_tab import render_home
from components.chat_tab import render_chat_tab
from components.settings_tab import render_settings_tab

# Load custom CSS
with open("style/custom.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

selected_tab = render_sidebar()
# Routing
if selected_tab == "Home":
    render_home()
if selected_tab == "Chat Sessions":
    render_chat_tab()
elif selected_tab == "Settings":
    render_settings_tab()

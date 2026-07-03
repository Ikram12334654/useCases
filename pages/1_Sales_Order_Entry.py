"""Hub page wrapper for Use Case 1 — Sales Order Entry."""

import streamlit as st

st.set_page_config(page_title="Sales Order Entry", page_icon="📄", layout="wide")

from usecases.sales_order.ui import render

render()

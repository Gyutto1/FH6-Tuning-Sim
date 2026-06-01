from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import streamlit as st


def section_header(title: str, caption: str | None = None) -> None:
    st.subheader(title)
    if caption:
        st.caption(caption)


def metric_card(label: str, value: object, help_text: str | None = None) -> None:
    st.metric(label, value, help=help_text)


def status_badge(label: str, tone: str = "info") -> None:
    if tone == "success":
        st.success(label)
    elif tone == "warning":
        st.warning(label)
    elif tone == "error":
        st.error(label)
    else:
        st.info(label)


def empty_state(message: str) -> None:
    st.info(message)


@contextmanager
def advanced_expander(label: str = "高级信息", expanded: bool = False) -> Iterator[None]:
    with st.expander(label, expanded=expanded):
        yield

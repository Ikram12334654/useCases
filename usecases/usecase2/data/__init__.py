"""data — UC2 seed data and sample payment generators.

Marks this directory as a regular package so ``usecases.usecase2.data`` and its
submodules (``seed``, ``make_sample_pdfs``) import reliably on every Python /
platform. Without this file the directory is only a namespace package, which
Streamlit Cloud's Python 3.14 import machinery rejects with
``KeyError: 'usecases.usecase2.data'``.
"""

"""CSS injection for The Underdoc — dark editorial theme."""

import streamlit as st


def inject_css() -> None:
    """Inject global CSS for the dark editorial theme.

    Call once at the top of main.py before any other st calls.
    Uses system serif stack (Georgia fallback) — no CDN dependency.
    """
    st.markdown(
        """
        <style>
        /* ── Typography ── */
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Lora:wght@400;500&display=swap');

        html, body, [class*="css"] {
            font-family: 'Lora', 'Georgia', 'Times New Roman', serif;
        }

        /* ── Wordmark ── */
        .underdoc-wordmark {
            font-family: 'Playfair Display', 'Georgia', serif;
            font-size: 1.6rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            color: #f0f0f0;
            line-height: 1;
        }
        .underdoc-wordmark span {
            color: #2d9e4f;
        }

        /* ── Red rule divider ── */
        .red-rule {
            border: none;
            border-top: 2px solid #2d9e4f;
            margin: 0.4rem 0 1.2rem 0;
        }

        /* ── Section label (e.g. "EREDIVISIE 2025-26") ── */
        .section-label {
            font-family: 'Playfair Display', 'Georgia', serif;
            font-size: 0.65rem;
            font-weight: 700;
            letter-spacing: 0.18em;
            text-transform: uppercase;
            color: #888;
            margin-bottom: 0.2rem;
        }

        /* ── Team card ── */
        .team-card {
            background: #1a1a1a;
            border: 1px solid #2a2a2a;
            border-left: 3px solid #2a2a2a;
            padding: 0.85rem 1rem;
            margin-bottom: 0.5rem;
            cursor: pointer;
            transition: border-left-color 0.15s ease;
        }
        .team-card:hover {
            border-left-color: #2d9e4f;
        }
        .team-card-name {
            font-family: 'Playfair Display', 'Georgia', serif;
            font-size: 1rem;
            font-weight: 600;
            color: #f0f0f0;
            margin-bottom: 0.25rem;
        }
        .team-card-meta {
            font-size: 0.72rem;
            color: #888;
            letter-spacing: 0.05em;
        }
        .team-card-meta strong {
            color: #bbb;
        }

        /* ── Match row ── */
        .match-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.6rem 0;
            border-bottom: 1px solid #222;
        }
        .match-date {
            font-size: 0.7rem;
            color: #666;
            letter-spacing: 0.06em;
            min-width: 5rem;
        }
        .match-scoreline {
            font-family: 'Playfair Display', 'Georgia', serif;
            font-size: 0.9rem;
            color: #f0f0f0;
            flex: 1;
            text-align: center;
        }
        .match-scoreline .score {
            color: #2d9e4f;
            font-weight: 700;
        }

        /* ── Panel 3 header ── */
        .report-header {
            font-family: 'Playfair Display', 'Georgia', serif;
            font-size: 1.6rem;
            font-weight: 700;
            color: #f0f0f0;
            line-height: 1.2;
            margin-bottom: 0.3rem;
        }
        .report-subhead {
            font-size: 0.72rem;
            color: #666;
            letter-spacing: 0.1em;
            text-transform: uppercase;
        }

        /* ── Sidebar wordmark ── */
        .sidebar-wordmark {
            font-family: 'Playfair Display', 'Georgia', serif;
            font-size: 1.1rem;
            font-weight: 700;
            color: #f0f0f0;
            letter-spacing: 0.03em;
        }
        .sidebar-wordmark span {
            color: #2d9e4f;
        }

        /* ── Streamlit button overrides ── */
        div[data-testid="stButton"] > button {
            border-radius: 0 !important;
            border: 1px solid #333 !important;
            font-family: 'Lora', 'Georgia', serif;
            font-size: 0.8rem;
            letter-spacing: 0.04em;
        }
        div[data-testid="stButton"] > button:hover {
            border-color: #2d9e4f !important;
            color: #2d9e4f !important;
        }

        /* ── Remove Streamlit default top padding ── */
        .block-container {
            padding-top: 1.5rem !important;
        }

        /* ── Expander ── */
        details summary {
            font-size: 0.75rem;
            color: #666;
            letter-spacing: 0.05em;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

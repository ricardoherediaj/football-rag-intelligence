"""Football RAG Intelligence - Gradio UI

Dark theme with neon green accent (Netpass aesthetic).
Simple 2-column layout: Controls + Output.
"""
import sys
from pathlib import Path
import gradio as gr

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from football_rag.models.rag_pipeline import FootballRAGPipeline
from football_rag import viz_tools
from football_rag.router import classify_intent


def chat_handler(query: str, api_key: str, provider: str):
    """Handle user query - route to visualization or text analysis."""

    if not query.strip():
        return "⚠️ Please enter a query", None, gr.update(visible=True), gr.update(visible=False)

    if not api_key.strip():
        return "⚠️ Please enter your API key to continue", None, gr.update(visible=True), gr.update(visible=False)

    try:
        pipeline = FootballRAGPipeline(provider=provider, api_key=api_key)

        ctx = pipeline._identify_match(query)
        if not ctx:
            return (
                "❌ **Match not found**\n\nTry asking about a specific match like:\n"
                "- 'Heracles vs PEC Zwolle'\n"
                "- 'Feyenoord vs Ajax'\n"
                "- 'PSV vs AZ'",
                None,
                gr.update(visible=True),
                gr.update(visible=False)
            )

        intent = classify_intent(query)

        if intent['tool'] == 'generate_dashboard':
            try:
                viz_path = viz_tools.generate_dashboard(ctx.match_id, ctx.home_team, ctx.away_team)
                return (
                    f"**Dashboard Generated**\n\n{ctx.home_team} vs {ctx.away_team}",
                    viz_path,
                    gr.update(visible=False),
                    gr.update(visible=True)
                )
            except Exception as viz_error:
                return (
                    f"❌ **Visualization Error**\n\n{ctx.home_team} vs {ctx.away_team}\n\nCouldn't generate dashboard: {str(viz_error)}",
                    None,
                    gr.update(visible=True),
                    gr.update(visible=False)
                )

        elif intent['tool'] == 'generate_team_viz':
            try:
                team_name = ctx.home_team if ctx.home_team.lower() in query.lower() else ctx.away_team
                viz_path = viz_tools.generate_team_viz(ctx.match_id, team_name, intent['viz_type'])
                return (
                    f"**{intent['viz_type'].replace('_', ' ').title()}**\n\n{team_name} - {ctx.home_team} vs {ctx.away_team}",
                    viz_path,
                    gr.update(visible=False),
                    gr.update(visible=True)
                )
            except Exception as viz_error:
                return (
                    f"❌ **Visualization Error**\n\n{ctx.home_team} vs {ctx.away_team}\n\nCouldn't generate {intent['viz_type']}: {str(viz_error)}",
                    None,
                    gr.update(visible=True),
                    gr.update(visible=False)
                )

        elif intent['tool'] == 'generate_match_viz':
            try:
                viz_path = viz_tools.generate_match_viz(ctx.match_id, intent['viz_type'])
                return (
                    f"**{intent['viz_type'].replace('_', ' ').title()}**\n\n{ctx.home_team} vs {ctx.away_team}",
                    viz_path,
                    gr.update(visible=False),
                    gr.update(visible=True)
                )
            except Exception as viz_error:
                return (
                    f"❌ **Visualization Error**\n\n{ctx.home_team} vs {ctx.away_team}\n\nCouldn't generate {intent['viz_type']}: {str(viz_error)}",
                    None,
                    gr.update(visible=True),
                    gr.update(visible=False)
                )

        else:
            result = pipeline.run(query)
            if "error" in result:
                return (
                    f"❌ **Error**\n\n{result['error']}",
                    None,
                    gr.update(visible=True),
                    gr.update(visible=False)
                )

            commentary = result.get("commentary", "No commentary generated")
            return (
                f"**Tactical Analysis**\n\n{ctx.home_team} vs {ctx.away_team}\n\n---\n\n{commentary}",
                None,
                gr.update(visible=True),
                gr.update(visible=False)
            )

    except Exception as e:
        return (
            f"❌ **Error**\n\n{str(e)}\n\nPlease check your API key and try again.",
            None,
            gr.update(visible=True),
            gr.update(visible=False)
        )


custom_css = """
/* Netpass aesthetic - dark theme with neon green accent */
.gradio-container {
    background-color: #0C0D0E !important;
}

/* Header styling */
.header-text h1 {
    color: #FFFFFF !important;
    font-weight: 700 !important;
    font-size: 2.5em !important;
    margin-bottom: 0.2em !important;
}

.header-text p {
    color: #00FF88 !important;
    font-size: 1.1em !important;
}

/* Controls sidebar */
.controls-panel {
    background-color: #1a1b1e !important;
    border-right: 2px solid #00FF88 !important;
    padding: 1.5em !important;
    border-radius: 8px !important;
}

/* Primary button (Analyze Match) */
.primary-btn {
    background: linear-gradient(135deg, #00FF88 0%, #00CC6E 100%) !important;
    color: #0C0D0E !important;
    font-weight: bold !important;
    border: none !important;
    padding: 12px 24px !important;
    font-size: 1.1em !important;
}

.primary-btn:hover {
    background: linear-gradient(135deg, #00CC6E 0%, #00AA5C 100%) !important;
    transform: translateY(-2px) !important;
    transition: all 0.2s ease !important;
}

/* Example queries */
.examples-section {
    background-color: #1a1b1e !important;
    padding: 1em !important;
    border-radius: 8px !important;
    margin-top: 1em !important;
}

/* Output area */
.output-panel {
    background-color: #1a1b1e !important;
    padding: 2em !important;
    border-radius: 8px !important;
    min-height: 600px !important;
}

/* Text output */
.output-text {
    color: #FFFFFF !important;
    font-size: 1.05em !important;
    line-height: 1.6 !important;
}

/* Input fields */
input, select, textarea {
    background-color: #0C0D0E !important;
    color: #FFFFFF !important;
    border: 1px solid #00FF88 !important;
}

label {
    color: #FFFFFF !important;
    font-weight: 600 !important;
}
"""


with gr.Blocks(theme=gr.themes.Soft(primary_hue="green", secondary_hue="slate"), css=custom_css) as demo:

    gr.Markdown(
        """
        # Football RAG Intelligence ⚽
        **Post-Match Tactical Analysis • Eredivisie 2025-26**
        """,
        elem_classes=["header-text"]
    )

    with gr.Row():
        with gr.Column(scale=1, elem_classes=["controls-panel"]):
            gr.Markdown("### API Configuration")

            api_key = gr.Textbox(
                label="API Key",
                type="password",
                placeholder="Enter your API key...",
                info="Required for analysis"
            )

            provider = gr.Dropdown(
                choices=["anthropic", "openai", "gemini"],
                label="Provider",
                value="anthropic",
                info="Select your LLM provider"
            )

            gr.Markdown("### Query")

            query = gr.Textbox(
                label="Ask about any match",
                placeholder="Show dashboard for Heracles vs PEC Zwolle...",
                lines=3
            )

            submit_btn = gr.Button(
                "🔍 Analyze Match",
                variant="primary",
                elem_classes=["primary-btn"]
            )

            gr.Markdown(
                """
                ### Quick Examples
                Click to try:
                """,
                elem_classes=["examples-section"]
            )

            examples = gr.Examples(
                examples=[
                    "Show dashboard for Heracles vs PEC Zwolle",
                    "Show passing network for Feyenoord",
                    "What was PSV's pressing strategy against Ajax?",
                    "Show shot map for AZ vs Utrecht",
                    "How did Heracles build up play against PEC?"
                ],
                inputs=query,
                label=""
            )

        with gr.Column(scale=2, elem_classes=["output-panel"]):
            gr.Markdown("### Output", elem_classes=["output-text"])

            text_output = gr.Markdown(
                "Enter a query and click 'Analyze Match' to begin...",
                elem_classes=["output-text"],
                visible=True
            )

            image_output = gr.Image(
                label="Visualization",
                visible=False,
                height=800
            )

    submit_btn.click(
        fn=chat_handler,
        inputs=[query, api_key, provider],
        outputs=[text_output, image_output, text_output, image_output]
    )


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False
    )

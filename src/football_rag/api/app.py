"""
FastAPI + Gradio application.
"""

from fastapi import FastAPI
import gradio as gr


app = FastAPI(title="Football RAG Intelligence", version="0.1.0")


def process_question(question: str) -> str:
    """Process football question through RAG pipeline."""
    # TODO: Implement RAG query processing
    return f"You asked: {question}. RAG response coming soon!"


# Gradio interface
with gr.Blocks(title="Football Scouting Intelligence") as interface:
    gr.Markdown("# ⚽ Football RAG Intelligence")
    gr.Markdown("Ask questions about Eredivisie and Championship matches!")
    
    with gr.Row():
        question_input = gr.Textbox(
            label="Your Question",
            placeholder="How did Bergwijn perform vs top 6 teams?",
            lines=2
        )
        submit_btn = gr.Button("Ask", variant="primary")
    
    answer_output = gr.Textbox(
        label="Analysis",
        lines=5,
        interactive=False
    )
    
    submit_btn.click(
        fn=process_question,
        inputs=question_input,
        outputs=answer_output
    )


# Mount Gradio app
app = gr.mount_gradio_app(app, interface, path="/")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
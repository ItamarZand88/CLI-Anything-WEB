import sys

import click

from cli_web.notebooklm.core.client import NotebookLMClient
from cli_web.notebooklm.core.models import parse_chat_message
from cli_web.notebooklm.utils.output import output_json, output_table


@click.group()
def chat():
    """NotebookLM chat operations."""
    pass


@chat.command()
@click.option("--notebook-id", required=True, help="The notebook ID.")
@click.pass_context
def history(ctx, notebook_id):
    """Get chat history for a notebook."""
    json_mode = ctx.obj["json"]
    client = NotebookLMClient()
    try:
        threads_response = client.get_chat_threads(notebook_id)
        thread_id = threads_response[0][0][0]
        result = client.get_chat_history(thread_id)
        messages_array = result[0]
        parsed = [parse_chat_message(msg) for msg in messages_array]

        if json_mode:
            output_json(parsed)
        else:
            headers = ["Timestamp", "Text"]
            rows = [[m["timestamp"], m["text"]] for m in parsed]
            output_table(headers, rows)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@chat.command()
@click.option("--notebook-id", required=True, help="The notebook ID.")
@click.pass_context
def suggested(ctx, notebook_id):
    """Get suggested questions."""
    json_mode = ctx.obj["json"]
    client = NotebookLMClient()
    try:
        result = client.get_summary(notebook_id)
        # Response: [[summary_list], [questions_list], ...], context_id
        data_list = result[0] if isinstance(result[0], list) else result
        summary = ""
        if data_list and isinstance(data_list[0], list) and data_list[0]:
            summary = data_list[0][0] if data_list[0] else ""
        questions_outer = data_list[1] if len(data_list) > 1 and isinstance(data_list[1], list) else []
        # questions_outer is [[q1, q2, ...]] — unwrap
        questions_raw = questions_outer[0] if questions_outer and isinstance(questions_outer[0], list) else questions_outer

        data = {
            "summary": summary,
            "questions": [
                {"question": q[0], "prompt": q[1] if len(q) > 1 else ""}
                for q in questions_raw if isinstance(q, list) and q
            ],
        }

        if json_mode:
            output_json(data)
        else:
            click.echo(f"Summary: {summary}\n")
            headers = ["Question"]
            rows = [[q["question"]] for q in data["questions"]]
            output_table(headers, rows)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@chat.command()
@click.option("--notebook-id", required=True, help="The notebook ID.")
@click.option("--question", required=True, help="The question to ask.")
@click.pass_context
def ask(ctx, notebook_id, question):
    """Send a question to a notebook's chat."""
    json_mode = ctx.obj.get("json", False)
    try:
        client = NotebookLMClient()
        threads_response = client.get_chat_threads(notebook_id)
        thread_id = threads_response[0][0][0]

        raw_sources = client.list_sources(notebook_id)
        source_ids = [s[0][0] for s in raw_sources if isinstance(s[0], list)]

        # The streaming API may fail with multiple sources — the server
        # expects a specific source selection format. Send all and retry
        # with individual sources if needed.
        try:
            result = client.ask_question(notebook_id, question, source_ids, thread_id)
        except RuntimeError:
            # Retry with just the first source
            result = client.ask_question(notebook_id, question, source_ids[:1], thread_id)

        if json_mode:
            output_json(result)
        else:
            click.echo(result.get("text", ""))
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

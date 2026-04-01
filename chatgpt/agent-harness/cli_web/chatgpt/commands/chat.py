"""Chat commands — ask questions and generate images with ChatGPT."""

from __future__ import annotations

import click

from ..core.client import ChatGPTClient
from ..utils.helpers import handle_errors, print_json, resolve_json_mode

try:
    from rich.console import Console
    from rich.markdown import Markdown

    _RICH = True
except ImportError:
    _RICH = False


@click.group("chat")
def chat_group():
    """Send messages and generate images with ChatGPT."""


@chat_group.command("ask")
@click.argument("question")
@click.option("--model", default=None, help="Model slug (e.g. gpt-5-4-thinking). Use 'models' command to list.")
@click.option("--conversation", default=None, help="Continue an existing conversation by ID.")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def ask(ctx, question: str, model: str | None, conversation: str | None, json_mode: bool) -> None:
    """Ask ChatGPT a question."""
    json_mode = resolve_json_mode(json_mode)

    with handle_errors(json_mode=json_mode):
        with ChatGPTClient() as client:
            if _RICH and not json_mode:
                console = Console(stderr=True)
                with console.status("Thinking..."):
                    result = client.send_message(
                        message=question,
                        conversation_id=conversation,
                        model=model,
                    )
            else:
                result = client.send_message(
                    message=question,
                    conversation_id=conversation,
                    model=model,
                )

            text = result.get("text", "")
            conv_id = result.get("conversation_id")

            if json_mode:
                print_json({
                    "success": True,
                    "data": {
                        "text": text,
                        "conversation_id": conv_id,
                        "model": model or "default",
                    },
                })
            else:
                if _RICH and text:
                    Console().print(Markdown(text))
                else:
                    click.echo(text or "(no response)")


@chat_group.command("image")
@click.argument("prompt")
@click.option("--style", default=None, help="Image style to prepend to prompt.")
@click.option("--output", "-o", default=None, type=click.Path(), help="Save image to file.")
@click.option("--conversation", default=None, help="Continue an existing conversation by ID.")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def image(ctx, prompt: str, style: str | None, output: str | None, conversation: str | None, json_mode: bool) -> None:
    """Generate an image with ChatGPT."""
    json_mode = resolve_json_mode(json_mode)
    full_prompt = f"{style} style: {prompt}" if style else prompt

    with handle_errors(json_mode=json_mode):
        with ChatGPTClient() as client:
            if _RICH and not json_mode:
                console = Console(stderr=True)
                with console.status("Generating image..."):
                    result = client.send_message(
                        message=full_prompt,
                        conversation_id=conversation,
                        image_mode=True,
                    )
            else:
                result = client.send_message(
                    message=full_prompt,
                    conversation_id=conversation,
                    image_mode=True,
                )

            file_id = result.get("file_id")
            conv_id = result.get("conversation_id")
            download_url = result.get("download_url")
            text = result.get("text", "")

            # Auto-download if output path given
            if output and download_url:
                img_bytes = client.download_file(download_url)
                with open(output, "wb") as f:
                    f.write(img_bytes)
                if not json_mode:
                    click.echo(f"Image saved to {output} ({len(img_bytes)} bytes)")

            if json_mode:
                data = {
                    "file_id": file_id,
                    "conversation_id": conv_id,
                    "download_url": download_url,
                    "text": text or None,
                }
                if output and download_url:
                    data["saved_to"] = output
                print_json({"success": True, "data": data})
            elif not output:
                if file_id:
                    click.echo(f"Image generated: file_id={file_id}")
                    if download_url:
                        click.echo(f"Download: cli-web-chatgpt images download {file_id} -c {conv_id}")
                elif text:
                    click.echo(text)
                else:
                    click.echo("No image was generated.", err=True)

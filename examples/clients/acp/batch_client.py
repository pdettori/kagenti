import asyncio
import sys
from contextlib import suppress
import asyncclick as click

from acp_sdk import GenericEvent, MessageCompletedEvent, MessagePartEvent
from acp_sdk.client import Client
from acp_sdk.models import Message, MessagePart

@click.command()
@click.option("--name")
@click.option("--url", default="http://localhost:8000")
@click.option("--iterations", type=int, required=True, help="Number of times to send the message")
@click.option("--user-message", required=True, help="Message to send")
async def run_client(name, url, iterations, user_message) -> None:
    print(f"url={url}  name={name}")
    with suppress(EOFError):
        async with Client(base_url=url) as client, client.session() as session:
            for _ in range(iterations):
                user_message_input = Message(parts=[MessagePart(content=user_message, role="user")])

                log_type = None
                async for event in client.run_stream(agent=name, input=[user_message_input]):
                    match event:
                        case MessagePartEvent(part=MessagePart(content=content)):
                            if log_type:
                                print()
                                log_type = None
                            print(content, end="", flush=True)
                        case GenericEvent():
                            [(new_log_type, content)] = event.generic.model_dump().items()
                            if new_log_type != log_type:
                                if log_type is not None:
                                    print()
                                print(f"{new_log_type}: ", end="", file=sys.stderr, flush=True)
                                log_type = new_log_type
                            print(content, end="", file=sys.stderr, flush=True)
                        case MessageCompletedEvent():
                            print()
                        case _:
                            if log_type:
                                print()
                                log_type = None
                            print(f"ℹ️ {event.type}", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(run_client())

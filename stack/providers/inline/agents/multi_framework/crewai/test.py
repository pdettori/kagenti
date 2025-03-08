import importlib
from crewai.agents.parser import AgentAction, AgentFinish
from crewai.agents.crew_agent_executor import ToolResult
import asyncio
from .converters import EventProcessor



impl_class = "examples.agents.crewai.math_agent.MathAgent.getCrew"




try:
    partial_impl_class, method_name = impl_class.rsplit(".", 1)
    module_name, class_name = partial_impl_class.rsplit(".", 1)
    my_module = importlib.import_module(module_name)

    ep = EventProcessor()

    # Get the class object and instantiate it
    crewai_agent_class = getattr(my_module, class_name)
   
except Exception as e:
    print(f"Failed to load agent: {e}")
    raise


async def main(method_name):
    instance = crewai_agent_class("ollama/llama3.2:3b-instruct-fp16", "http://localhost:11434", ep.enqueue_event_wrapper)
    method = getattr(instance, method_name)
    prompt = "calculate 3 + 5. Take the result and divide it by by 2"
    kickoff_task = asyncio.create_task(method().kickoff_async(inputs={'prompt': prompt}))
    #await asyncio.gather(ep.process_events(), kickoff_task)
    
    # print(">>>>>>>>>>>>>>>>>>> HELLO")

    # async for event in ep.process_events():
    #     print(f"Processed: {event}")

    # # Ensure all tasks complete
    # await kickoff_task

    # A wrapper coroutine to iterate over the async generator
    async def run_event_processor():
        async for event in ep.process_events():
            print(f"Processed: {event}")

    # Create a task for running the event processor
    process_events_task = asyncio.create_task(run_event_processor())

    try:
        await kickoff_task
    finally:
        await process_events_task
        # Ensure shutdown if kicker finishes first
        ep.finished.set()
        
    print("Main result:", kickoff_task.result())


if __name__ == "__main__":
    asyncio.run(main(method_name))
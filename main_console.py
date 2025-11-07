import asyncio

from whatsapp.agent.agents import agent_service


async def main():
    question = "What is 2 + 2?"
    result = await agent_service(question)
    # si result es un objeto complejo, accede a la propiedad final_output como en tu ejemplo
    print(getattr(result, "final_output", result))


if __name__ == "__main__":
    asyncio.run(main())

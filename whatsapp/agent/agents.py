from agents import Agent, Runner

from whatsapp.agent.load_instruction import load_instructions_from_doc
from whatsapp.config import AGENT_NAME, logger  # <-- agregamos logger


async def agent_service(question: str, role_qualifier_id: str = None):
    """
    Ejecuta el agente con las instrucciones correspondientes y siempre devuelve
    un dict con 'final_output' como string, para evitar errores de serialización.
    """
    try:
        # Cargar instrucciones desde Google Docs según role_qualifier_id
        if role_qualifier_id:
            instructions = load_instructions_from_doc(role_qualifier_id)
            logger.info(
                f"📄 Instrucciones cargadas desde Google Docs para role_qualifier_id={role_qualifier_id}"
            )
        else:
            # fallback: instrucciones genéricas
            instructions = "Hola, soy tu asistente, instrucciones genéricas."
            logger.info("📄 Usando instrucciones genéricas")

        # Log completo de instrucciones (opcional: solo primeras 200 chars)
        logger.debug(
            f"Instrucciones usadas: {str(instructions)[:200]}{'...' if len(str(instructions)) > 200 else ''}"
        )

        agent = Agent(
            name=AGENT_NAME,
            instructions=instructions,
        )

        result = await Runner.run(agent, question)

        # Extraer final_output del RunResult o dict
        if hasattr(result, "final_output"):
            output = str(result.final_output)
        elif isinstance(result, dict):
            output = str(result.get("final_output", str(result)))
        else:
            output = str(result)

        return {"final_output": output}

    except Exception as e:
        return {"error": str(e), "final_output": f"Ocurrió un error: {e}"}

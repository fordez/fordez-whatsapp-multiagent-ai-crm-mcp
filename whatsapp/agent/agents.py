from agents import Agent, Runner

from whatsapp.agent.load_instruction import load_instructions_from_doc
from whatsapp.config import AGENT_NAME, logger

# Cache local para instrucciones
INSTRUCTIONS_CACHE = {}


async def agent_service(question: str, role_qualifier_id: str = None):
    """
    Ejecuta el agente con las instrucciones correspondientes y devuelve
    siempre un dict con 'final_output' como string para evitar errores de serialización.
    """
    try:
        # =============================
        # Cargar instrucciones con cache
        # =============================
        if role_qualifier_id:
            if role_qualifier_id in INSTRUCTIONS_CACHE:
                instructions = INSTRUCTIONS_CACHE[role_qualifier_id]
                logger.info(
                    f"🟢 Usando cache de instrucciones para role_qualifier_id={role_qualifier_id}"
                )
            else:
                instructions = load_instructions_from_doc(role_qualifier_id)
                INSTRUCTIONS_CACHE[role_qualifier_id] = instructions
                logger.info(
                    f"📄 Instrucciones cargadas desde Google Docs para role_qualifier_id={role_qualifier_id}"
                )
        else:
            instructions = "Hola, soy tu asistente, instrucciones genéricas."
            logger.info("📄 Usando instrucciones genéricas")

        # Log opcional: primeras 200 chars
        logger.debug(
            f"Instrucciones usadas: {str(instructions)[:200]}{'...' if len(str(instructions)) > 200 else ''}"
        )

        # =============================
        # Ejecutar agente
        # =============================
        agent = Agent(
            name=AGENT_NAME,
            instructions=instructions,
        )

        result = await Runner.run(agent, question)

        # Extraer final_output
        if hasattr(result, "final_output"):
            output = str(result.final_output)
        elif isinstance(result, dict):
            output = str(result.get("final_output", str(result)))
        else:
            output = str(result)

        return {"final_output": output}

    except Exception as e:
        logger.error(f"❌ Error ejecutando agente: {e}")
        return {"error": str(e), "final_output": f"Ocurrió un error: {e}"}

"""
Servicio de agente con herramientas nativas (sin MCP Server).
Migrado para mejor latencia y rendimiento con memoria local SQLite.
Archivos SQLite guardados en la carpeta 'memory/'.
"""

import os

from agents import Agent, Runner
from agents.extensions.memory import AdvancedSQLiteSession
from agents.model_settings import ModelSettings

from whatsapp.agent.tools import ALL_TOOLS
from whatsapp.config import config

# Carpeta donde se guardarán las bases de datos SQLite
MEMORY_DIR = "memory"
os.makedirs(MEMORY_DIR, exist_ok=True)

# Sesiones persistentes por usuario con memoria SQLite
SESSIONS: dict[str, AdvancedSQLiteSession] = {}


async def get_user_session(session_key: str) -> AdvancedSQLiteSession:
    """Obtiene o crea una sesión SQLite avanzada para el usuario."""
    if session_key not in SESSIONS:
        # Ruta completa para la base de datos del usuario
        db_path = os.path.join(MEMORY_DIR, f"{session_key}.db")
        SESSIONS[session_key] = AdvancedSQLiteSession(
            session_id=session_key, db_path=db_path, create_tables=True
        )
    return SESSIONS[session_key]


async def agent_service(
    user_message: str,
    system_instructions: str,
    session_key: str,
    user_data: dict | None = None,
) -> dict:
    """
    Ejecuta el agente con herramientas nativas y memoria local SQLite.
    """
    try:
        session = await get_user_session(session_key)

        # Preparar contexto adicional con user_data
        context_message = ""
        if user_data:
            context_parts = [f"{k}: {v}" for k, v in user_data.items()]
            context_message = "Información del usuario:\n" + "\n".join(context_parts)

        final_prompt = (
            f"{context_message}\n\nMensaje del usuario: {user_message}"
            if context_message
            else user_message
        )

        # Crear agente con herramientas nativas
        agent = Agent(
            name=config.agent_name,
            instructions=system_instructions,
            tools=ALL_TOOLS,
            model_settings=ModelSettings(tool_choice="auto"),
        )

        # Ejecutar agente usando la memoria SQLite
        result = await Runner.run(agent, final_prompt, session=session)

        # Almacenar información de uso y tokenización
        await session.store_run_usage(result)

        final_output = getattr(result, "final_output", str(result))
        return {"final_output": final_output}

    except Exception as e:
        return {
            "final_output": "Lo siento, ocurrió un error al procesar tu solicitud. Por favor, intenta nuevamente.",
            "error": str(e),
        }


def clear_user_session(session_key: str) -> bool:
    """Limpia la sesión de un usuario específico y su memoria SQLite."""
    if session_key in SESSIONS:
        del SESSIONS[session_key]
        db_path = os.path.join(MEMORY_DIR, f"{session_key}.db")
        if os.path.exists(db_path):
            os.remove(db_path)  # Elimina el archivo SQLite del disco
        return True
    return False


def get_active_sessions_count() -> int:
    """Retorna el número de sesiones activas."""
    return len(SESSIONS)

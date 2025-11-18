"""
Servicio de agente con herramientas nativas (sin MCP Server)
Memoria persistente en SQLite (carpeta memory/).
Incluye guardrail de entrada usando un clasificador LLM.
Gestiona el contexto del sheet_crm_id vía RunContextWrapper.
"""

import os

from agents import (
    Agent,
    GuardrailFunctionOutput,
    InputGuardrailTripwireTriggered,
    RunContextWrapper,
    Runner,
    TResponseInputItem,
    input_guardrail,
)
from agents.extensions.memory import AdvancedSQLiteSession
from agents.model_settings import ModelSettings
from pydantic import BaseModel

from whatsapp.agent.tools import ALL_TOOLS
from whatsapp.config import config


# ============================================================
# MODELO DE CONTEXTO
# ============================================================
class AgentContextData(BaseModel):
    sheet_crm_id: str | None = None


USER_CONTEXTS: dict[str, RunContextWrapper[AgentContextData]] = {}


# ============================================================
# MEMORIA PERSISTENTE SQLite POR USUARIO
# ============================================================
MEMORY_DIR = "memory"
os.makedirs(MEMORY_DIR, exist_ok=True)

SESSIONS: dict[str, AdvancedSQLiteSession] = {}


async def get_user_session(session_key: str) -> AdvancedSQLiteSession:
    if session_key not in SESSIONS:
        db_path = os.path.join(MEMORY_DIR, f"{session_key}.db")
        print(f"[MEMORY] Iniciando sesión SQLite → {session_key}")
        SESSIONS[session_key] = AdvancedSQLiteSession(
            session_id=session_key,
            db_path=db_path,
            create_tables=True,
        )
    return SESSIONS[session_key]


# ============================================================
# GUARDRAIL CLASSIFIER AGENT
# ============================================================
class SafetyCheckOutput(BaseModel):
    is_flagged: bool
    label: str
    reasoning: str


safety_classifier_agent = Agent(
    name="safety-classifier",
    instructions=(
        "Eres un clasificador de seguridad. Detecta insultos, violencia, "
        "contenido sexual, ilegal o peligroso. Si el mensaje es seguro, "
        "marca is_flagged en false. Responde SOLO JSON con: "
        "{ is_flagged, label, reasoning }"
    ),
    output_type=SafetyCheckOutput,
)


# ============================================================
# INPUT GUARDRAIL — AISLADO (NO SESIÓN, NO CONTEXTO, NO HISTORIAL)
# ============================================================
@input_guardrail
async def safety_guardrail(
    ctx: RunContextWrapper[AgentContextData],
    agent: Agent,
    input: str | list[TResponseInputItem],
) -> GuardrailFunctionOutput:
    print(f"[GUARDRAIL] Analizando mensaje del usuario")

    # -------------------------------------------------------
    # (1) Extraer el texto real sin importar el formato
    # -------------------------------------------------------
    if isinstance(input, str):
        user_msg = input
    else:
        user_msg = ""
        try:
            if isinstance(input, list) and len(input) > 0:
                first = input[0]
                if isinstance(first, dict):
                    user_msg = first.get("text") or first.get("message") or str(first)
                else:
                    user_msg = (
                        getattr(first, "text", None)
                        or getattr(first, "message", None)
                        or str(first)
                    )
            else:
                user_msg = str(input)
        except Exception:
            user_msg = str(input)

    # -------------------------------------------------------
    # (2) Ejecutar el clasificador totalmente aislado
    #     sin session + sin context → NO historial
    # -------------------------------------------------------
    result = await Runner.run(
        safety_classifier_agent,
        user_msg,
        session=None,  # ← No memoria
        context=None,  # ← No contexto del agente principal
    )

    fo = getattr(result, "final_output", result)

    # -------------------------------------------------------
    # (3) Normalizar salida
    # -------------------------------------------------------
    is_flagged = False
    label = ""
    reasoning = ""

    if hasattr(fo, "is_flagged"):
        is_flagged = bool(fo.is_flagged)
        label = fo.label or ""
        reasoning = fo.reasoning or ""

    elif isinstance(fo, dict):
        is_flagged = bool(fo.get("is_flagged", False))
        label = fo.get("label", "") or ""
        reasoning = fo.get("reasoning", "") or ""

    else:
        try:
            import json

            parsed = json.loads(str(fo))
            if isinstance(parsed, dict):
                is_flagged = bool(parsed.get("is_flagged", False))
                label = parsed.get("label", "") or ""
                reasoning = parsed.get("reasoning", "") or ""
        except Exception:
            pass

    output = SafetyCheckOutput(
        is_flagged=is_flagged,
        label=label,
        reasoning=reasoning,
    )

    return GuardrailFunctionOutput(
        output_info=output,
        tripwire_triggered=is_flagged,
    )


# ============================================================
# SERVICIO PRINCIPAL DEL AGENTE
# ============================================================
async def agent_service(
    user_message: str,
    system_instructions: str,
    session_key: str,
    user_data: dict | None = None,
    sheet_crm_id: str | None = None,
) -> dict:
    try:
        print(f"[AGENT] Nuevo mensaje recibido (session={session_key})")

        # Sesión persistente
        session = await get_user_session(session_key)

        # Contexto
        if session_key not in USER_CONTEXTS:
            USER_CONTEXTS[session_key] = RunContextWrapper(AgentContextData())
            print(f"[CONTEXT] Contexto inicializado")

        ctx_wrapper = USER_CONTEXTS[session_key]

        # Actualizar sheet CRM
        if sheet_crm_id:
            ctx_wrapper.context.sheet_crm_id = sheet_crm_id
            print(f"[CONTEXT] sheet_crm_id actualizado")

        # Construir prompt
        if user_data:
            extra = "\n".join([f"{k}: {v}" for k, v in user_data.items()])
            full_prompt = f"{extra}\n\nMensaje: {user_message}"
        else:
            full_prompt = user_message

        # Agente principal
        agent = Agent(
            name=config.agent_name,
            instructions=system_instructions,
            tools=ALL_TOOLS,
            input_guardrails=[safety_guardrail],
            model_settings=ModelSettings(tool_choice="auto"),
        )

        # Ejecutar
        result = await Runner.run(
            agent,
            full_prompt,
            session=session,
            context=ctx_wrapper.context,
        )

        await session.store_run_usage(result)

        output = getattr(result, "final_output", str(result))

        print("[AGENT] Respuesta generada")

        return {"final_output": output}

    except InputGuardrailTripwireTriggered:
        print("[GUARDRAIL] Mensaje bloqueado")
        return {"final_output": "Mensaje bloqueado por políticas de seguridad."}

    except Exception as e:
        print(f"[ERROR] {e}")
        return {
            "final_output": "Error procesando solicitud.",
            "error": str(e),
        }


# ============================================================
# UTILIDADES
# ============================================================
def clear_user_session(session_key: str) -> bool:
    if session_key in SESSIONS:
        del SESSIONS[session_key]
        db_path = os.path.join(MEMORY_DIR, f"{session_key}.db")

        if os.path.exists(db_path):
            os.remove(db_path)

        print(f"[MEMORY] Sesión eliminada")
        return True

    return False


def get_active_sessions_count() -> int:
    return len(SESSIONS)

from autogen import ConversableAgent
from whatsapp.agent.llm_config import get_llm_config

llm_config = get_llm_config()

# Router inteligente
marketing_router = ConversableAgent(
    name="marketing_router",
    system_message="""
Eres el coordinador de marketing. Para cada mensaje del usuario decide:
- 'lead_classifier' si es un lead nuevo o interesado.
- 'retargeting_agent' si ya fue contactado o no respondió.
Devuelve SOLO el nombre del agente destino.
""",
    llm_config=llm_config,
)

# Lead Classifier
lead_classifier = ConversableAgent(
    name="lead_classifier",
    system_message="""
🎯 Objetivo: Calificar leads y lograr que agenden sesión gratuita.
Responde en 1-3 líneas, tono cálido y profesional.
""",
    llm_config=llm_config,
)

# Retargeting Agent
retargeting_agent = ConversableAgent(
    name="retargeting_agent",
    system_message="""
🎯 Objetivo: Reactivar leads que no respondieron.
Responde cortamente con CTA, tono profesional y cálido.
""",
    llm_config=llm_config,
)

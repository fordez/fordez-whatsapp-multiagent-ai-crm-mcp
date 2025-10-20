from whatsapp.agent.agents import marketing_agent


class MarketingChat:
    def __init__(self):
        self.conversation_history = []

    def reply(self, user_input):
        # Guardar mensaje del usuario
        self.conversation_history.append({"role": "user", "content": user_input})

        # Generar respuesta directamente con el agente único
        agent_reply = marketing_agent.generate_reply(
            messages=[{"role": "system", "content": marketing_agent.system_message}]
            + self.conversation_history[-3:]  # usar últimos 3 mensajes
        )

        # Guardar respuesta en historial
        self.conversation_history.append({"role": "assistant", "content": agent_reply})
        return agent_reply

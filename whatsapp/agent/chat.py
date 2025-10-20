from whatsapp.agent.agents import marketing_router, lead_classifier, retargeting_agent


class MarketingChat:
    def __init__(self):
        self.conversation_history = []

    def route_message(self, user_input):
        # Guardar mensaje del usuario
        self.conversation_history.append({"role": "user", "content": user_input})

        # Router decide agente
        routing_reply = marketing_router.generate_reply(
            messages=[{"role": "system", "content": marketing_router.system_message}]
            + self.conversation_history[-3:]
        )
        target_agent_name = routing_reply.strip().lower()
        return target_agent_name

    def agent_reply(self, user_input, target_agent_name):
        if "lead" in target_agent_name:
            agent_reply = lead_classifier.generate_reply(
                messages=[{"role": "system", "content": lead_classifier.system_message}]
                + self.conversation_history[-3:]
            )
        elif "retarget" in target_agent_name:
            agent_reply = retargeting_agent.generate_reply(
                messages=[
                    {"role": "system", "content": retargeting_agent.system_message}
                ]
                + self.conversation_history[-3:]
            )
        else:
            agent_reply = "No entendí a qué agente dirigir este mensaje."

        # Guardar respuesta en historial
        self.conversation_history.append({"role": "assistant", "content": agent_reply})
        return agent_reply

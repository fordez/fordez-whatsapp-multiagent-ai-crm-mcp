from whatsapp.agent.chat import MarketingChat

print("🤖 Chat de Marketing (modo WhatsApp modular)")
print("💬 Escribe tu mensaje (o 'salir' para terminar).")

chat = MarketingChat()

while True:
    try:
        user_input = input("\nYou: ")
        if user_input.lower() in ["salir", "exit", "quit"]:
            print("👋 Terminando sesión.")
            break

        target_agent_name = chat.route_message(user_input)
        print(f"\n🔀 Enrutado a: {target_agent_name}")

        agent_reply = chat.agent_reply(user_input, target_agent_name)
        print(f"\n🧠 {target_agent_name}: {agent_reply}")

    except KeyboardInterrupt:
        print("\n👋 Sesión interrumpida.")
        break

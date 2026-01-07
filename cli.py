from src.agents.jira_agent import JiraAgent
from src.core.config import config

def main():
    print("🚀 Jira Agent CLI is starting...")
    
    if not config.GROQ_API_KEY:
        print("❌ Error: GROQ_API_KEY not found.")
        return

    agent = JiraAgent()
    print("\nAgent initialized with skills. Type 'exit' to quit.")
    
    while True:
        user_input = input("\nWhat would you like to do? > ")
        if user_input.lower() in ['exit', 'quit', 'q']:
            break
            
        print("\nProcessing...\n" + "-"*30)
        try:
            current_version = agent.generate_ticket(user_input)
            
            while True:
                print(current_version)
                print("-" * 30)

                choice = input("\nPost (y), Revise (r), or Cancel (n) > ").lower()
                
                if choice == 'y':
                    print(agent.post_content(current_version))
                    break

                elif choice == 'r':
                    notes = input("What would you like to change? > ")
                    print("\nRevising...\n" + "-"*30)
                    current_version = agent.generate_ticket(user_input, current_version, notes)
                else:
                    print("Skipped.")
                    break

        except Exception as e:
            print(f"❌ An error occurred: {e}")

if __name__ == "__main__":
    main()


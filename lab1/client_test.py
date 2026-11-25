from openai import OpenAI

# Configure client to point to local Ollama instance
client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"  # Required by SDK format; ignored by Ollama
)

conversation=[
        {
            "role": "system",
            "content": "You are an academic mentor."
        }
    ]

def run_loop_turn():
    while True:
        user=input("User: ")
        if user.lower() == "exit" or user.lower() == "quit":
            break
        conversation.append(
            {
                "role": "user",
                "content": user
            }
        )
        response = client.chat.completions.create(
            model="qwen2.5:1.5b",
            temperature=0.2,
            messages=conversation
        )

        conversation.append(
            {
                "role": "assistant",
                "content": response.choices[0].message.content
            }
        )

        print("Assitant: ")
        print(response.choices[0].message.content)

        #print("\n---")
        #print(f"Usage: {response.usage.prompt_tokens} prompt tokens, "
        #     f"{response.usage.completion_tokens} completion tokens.")#
if __name__ == "__main__":
    run_loop_turn()

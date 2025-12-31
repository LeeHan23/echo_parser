
import os
import sys

def test_api_key(api_key):
    print(f"Testing API Key: {api_key[:5]}...{api_key[-5:] if len(api_key) > 10 else ''}")
    
    try:
        from openai import OpenAI
    except ImportError:
        print("Error: 'openai' library is not installed.")
        print("Please run: pip install openai")
        return

    try:
        client = OpenAI(api_key=api_key)
        # Try to list models as a lightweight test
        models = client.models.list()
        print("\nSUCCESS! API Key is valid.")
        print(f"Retrieved {len(list(models))} models.")
        
        # Optional: Try a small chat completion
        print("Testing Chat Completion...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello, are you working?"}],
            max_tokens=10
        )
        print("Chat Response:", response.choices[0].message.content)
        
    except Exception as e:
        print(f"\nFAILED. Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        key = sys.argv[1]
    else:
        key = input("Enter your OpenAI API Key: ").strip()
    
    if key:
        test_api_key(key)
    else:
        print("No key provided.")

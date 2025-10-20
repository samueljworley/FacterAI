from openai import OpenAI
import os

# Get API key from environment
api_key = os.getenv('OPENAI_API_KEY')
print(f"API key starts with: {api_key[:7]}...")

# Initialize client
client = OpenAI(api_key=api_key)

try:
    # Test GPT-4O API call
    response = client.chat.completions.create(
        model="gpt-4o",  # Exact model name
        messages=[{"role": "user", "content": "Say hello!"}]
    )
    print("Success! GPT-4O Response:", response.choices[0].message.content)
except Exception as e:
    print("Error with GPT-4O:", str(e))



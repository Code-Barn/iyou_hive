import os
from google.genai import Client

def list_my_models():
    api_key = os.environ.get("GEMINI_API_KEY")
    # NO version specified here
    client = Client(api_key=api_key)

    print(f"{'MODEL NAME':<40} | {'METHODS'}")
    print("-" * 70)

    try:
        # In the new SDK, it is model.supported_methods
        for model in client.models.list():
            methods = ", ".join(model.supported_methods)
            print(f"{model.name:<40} | {methods}")
    except Exception as e:
        print(f"Failed to list models: {e}")

if __name__ == "__main__":
    list_my_models()

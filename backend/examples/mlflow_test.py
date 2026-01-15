import mlflow
import os
from openai import OpenAI


# os.environ["OPENAI_API_KEY"] = 'OPENAI_API_KEY'
mlflow.set_tracking_uri("sqlite:///mlflow.db")
mlflow.set_experiment("my-genai-experiment")

# Print connection information
print(f"MLflow Tracking URI: {mlflow.get_tracking_uri()}")
print(f"Active Experiment: {mlflow.get_experiment_by_name('my-genai-experiment')}")

# # Test logging
# with mlflow.start_run():
#     mlflow.log_param("test_param", "test_value")
#     print("✓ Successfully connected to MLflow!")

# Enable automatic tracing for all OpenAI API calls
mlflow.openai.autolog()

# Instantiate the OpenAI client
client = OpenAI()

# # Invoke chat completion API
# response = client.chat.completions.create(
#     model="o4-mini",
#     messages=[
#         {"role": "system", "content": "You are a helpful weather assistant."},
#         {"role": "user", "content": "What's the weather like in Seattle?"},
#     ],
# )


# print(response)

import requests
from mlflow.entities import SpanType
import json

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current temperature for provided coordinates in celsius.",
            "parameters": {
                "type": "object",
                "properties": {
                    "latitude": {"type": "number"},
                    "longitude": {"type": "number"},
                },
                "required": ["latitude", "longitude"],
                "additionalProperties": False,
            },
            "strict": True,
        },
    }
]

# Decorated with @mlflow.trace to trace the function call.
@mlflow.trace(span_type=SpanType.TOOL)
def get_weather(latitude, longitude):
    response = requests.get(
        f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m,wind_speed_10m&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m"
    )
    data = response.json()
    return data["current"]["temperature_2m"]



# Define a simple tool calling agent
@mlflow.trace(span_type=SpanType.AGENT)
def run_tool_agent(question: str):
    messages = [{"role": "user", "content": question}]

    # Invoke the model with the given question and available tools
    response = client.chat.completions.create(
        model="o4-mini",
        messages=messages,
        tools=tools,
    )
    
    ai_msg = response.choices[0].message #生成tool 需要的argument/parameter
    print(ai_msg)
    messages.append(ai_msg)

    # If the model requests tool call(s), invoke the function with the specified arguments
    if tool_calls := ai_msg.tool_calls:
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            if function_name == "get_weather":
                # Invoke the tool function with the provided arguments
                args = json.loads(tool_call.function.arguments)
                tool_result = get_weather(**args)
            else:
                raise RuntimeError("An invalid tool is returned from the assistant!")

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(tool_result),
                }
            )

        # Sent the tool results to the model and get a new response
        response = client.chat.completions.create(model="o4-mini", messages=messages)

    return response.choices[0].message.content

# Run the tool calling agent
question = "What's the weather like in Seattle?"
answer = run_tool_agent(question)
print(answer)

# mlflow server --backend-store-uri sqlite:///mlflow.d
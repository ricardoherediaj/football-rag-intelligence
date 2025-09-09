import requests

vector_store_path = "http://localhost:6333"


non_relevant_dialog = {  # This will test Guardrail
    "messages": [
        {"role": "user", "content": "What is the company's sick leave policy?"},
        {
            "role": "assistant",
            "content": "The company's sick leave policy allows employees to take a certain number of sick days per year. Please refer to the employee handbook for specific details and eligibility criteria.",
        },
        {"role": "user", "content": "What is the meaning of life?"},
    ],
    "vector_store_path": vector_store_path,
}

relevant_dialog = {  # This will test schema
    "messages": [
        {"role": "user", "content": "What is  discussed in the HR manual?"},
    ],
    "vector_store_path": vector_store_path,
}


response = requests.post("http://localhost:8000/predict", json=non_relevant_dialog)
print(response.json())
# print(response.headers["X-Request-Id"])  # This will print "00000"


print("-------------------")
print("Relevant Dialog")

response = requests.post("http://localhost:8000/predict", json=relevant_dialog)
print(response.json())

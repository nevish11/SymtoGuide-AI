import requests
from django.conf import settings

def analyze_symptoms_with_ai(symptom_text):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "http://localhost:8000",
    "X-Title": "Health AI"
    }


    # AI ને સ્પષ્ટ સૂચના આપો કે JSON જ આપે
    system_prompt = (
        "You are a healthcare assistant. Analyze symptoms and return ONLY a JSON object with this structure: "
        '{"illnesses": [{"name": "string", "match": int}], "confidence": int, "urgency": "self_monitor|schedule_appointment|urgent_care|emergency", "guidance": "string"}'
    )

    data = {
        "model": "openai/gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": symptom_text}
        ],
        "response_format": { "type": "json_object" } # આ લાઈનથી AI JSON જ આપશે
    }

    response = requests.post(url, headers=headers, json=data, timeout=30)
    return response.json()
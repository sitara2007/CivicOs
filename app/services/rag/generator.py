from openai import OpenAI

from app.core.config import get_settings
from app.services.rag.retriever import retrieve

settings = get_settings()
client = OpenAI(api_key=settings.openai_api_key or "missing-api-key")

def get_answer(question):
    chunks = retrieve(question)
    context = "\n".join([c['text'] for c in chunks])
    
    prompt = f"Use this context to answer the question: {context}\n\nQuestion: {question}"
    
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

if __name__ == "__main__":
    print(get_answer("Who is eligible for this scheme?"))

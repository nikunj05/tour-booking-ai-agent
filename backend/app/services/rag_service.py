import os
import faiss
import numpy as np
from pypdf import PdfReader
from openai import OpenAI

client = OpenAI()

EMBED_MODEL = "text-embedding-3-small"

# Store in memory (for now)
vector_store = None
chunks_store = []


# =========================================
# 📄 Load PDF and Create Embeddings
# =========================================
def process_pdf(file_path: str):
    global vector_store, chunks_store

    reader = PdfReader(file_path)

    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text() + "\n"

    # Split into chunks
    chunks = split_text(full_text)

    embeddings = []
    for chunk in chunks:
        response = client.embeddings.create(
            model=EMBED_MODEL,
            input=chunk
        )
        embeddings.append(response.data[0].embedding)

    embeddings = np.array(embeddings).astype("float32")

    dimension = len(embeddings[0])
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)

    vector_store = index
    chunks_store = chunks


# =========================================
# ✂ Split Text
# =========================================
def split_text(text, chunk_size=500):
    words = text.split()
    chunks = []

    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)

    return chunks


# =========================================
# 🤖 Ask Question From PDF
# =========================================
def ask_pdf(question: str):

    if vector_store is None:
        return "PDF not loaded."

    # Create embedding for question
    response = client.embeddings.create(
        model=EMBED_MODEL,
        input=question
    )

    question_embedding = np.array(
        [response.data[0].embedding]
    ).astype("float32")

    # Search similar chunks
    D, I = vector_store.search(question_embedding, k=3)

    context = "\n\n".join([chunks_store[i] for i in I[0]])

    prompt = f"""
You must answer ONLY from the context below.
If answer not found, say:
"Information not available in provided document."

Context:
{context}

Question:
{question}
"""

    chat_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Answer strictly from provided context."},
            {"role": "user", "content": prompt}
        ]
    )

    return chat_response.choices[0].message.content

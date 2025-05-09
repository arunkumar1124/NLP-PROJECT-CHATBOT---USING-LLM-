from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import faiss
import numpy as np

# Load model and tokenizer (TinyLlama)
model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
tokenizer = AutoTokenizer.from_pretrained(model_name)

# Optimize model loading for GPU
device = "cuda" if torch.cuda.is_available() else "cpu"

# Load model with proper device placement
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float16 if device == "cuda" else torch.float32,
    device_map="auto" if device == "cuda" else None  # Only use device_map for CUDA
)

# Enable model optimizations
if device == "cuda":
    # Enable better memory efficiency
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    # Enable faster attention computation
    torch.backends.cudnn.benchmark = True
else:
    # For CPU, explicitly move model to device
    model = model.to(device)

model.eval()

def load_text_file(file):
    return file.read().decode("utf-8")

def chunk_text(text, chunk_size=300):
    words = text.split()
    return [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]

def build_faiss_index(chunks):
    from sentence_transformers import SentenceTransformer
    embedder = SentenceTransformer("all-MiniLM-L6-v2", device=device)  # Use GPU for embeddings

    embeddings = embedder.encode(chunks, show_progress_bar=True)
    dim = embeddings[0].shape[0]
    index = faiss.IndexFlatL2(dim)
    index.add(np.array(embeddings))
    return index, chunks

def get_most_relevant_chunks(query, index, chunk_list, top_k=3):
    from sentence_transformers import SentenceTransformer
    embedder = SentenceTransformer("all-MiniLM-L6-v2", device=device)  # Use GPU for embeddings
    query_vec = embedder.encode([query])
    _, indices = index.search(np.array(query_vec), top_k)
    return [chunk_list[i] for i in indices[0]]

def generate_answer(query, context, history=[]):
    prompt = f"""You are an assistant that answers questions based on provided context.
Context:
{context}
User: {query}
Assistant:"""

    inputs = tokenizer(prompt, return_tensors="pt", truncation=True).to(device)
    
    # Optimize generation parameters for speed
    outputs = model.generate(
        **inputs,
        max_new_tokens=150,
        num_beams=1,  # Use greedy search for speed
        do_sample=False,  # Disable sampling for faster generation
        temperature=1.0,
        pad_token_id=tokenizer.eos_token_id
    )
    
    return tokenizer.decode(outputs[0], skip_special_tokens=True).split("Assistant:")[-1].strip()

from fastapi import FastAPI
from pydantic import BaseModel
from spelling_engine import correction, get_feedback  # Importing your functions

app = FastAPI()

# This defines what the "Order" from the frontend looks like
class SentenceRequest(BaseModel):
    text: str

@app.post("/analyze")
async def analyze_sentence(request: SentenceRequest):
    # 1. Break down the sentence
    words = request.text.lower().split()
    
    # 2. Run your Peter Norvig logic
    corrected_words = [correction(w) for w in words]
    corrected_text = " ".join(corrected_words)
    
    # 3. Calculate stats
    total = len(words)
    mistakes = sum(1 for o, c in zip(words, corrected_words) if o != c)
    percentage = (mistakes / total) * 100 if total > 0 else 0
    
    # 4. Get your feedback logic
    level, feedback = get_feedback(percentage)
    
    # 5. Send it back to the React app as JSON
    return {
        "original": request.text,
        "corrected": corrected_text,
        "mistakes": mistakes,
        "percentage": round(percentage, 2),
        "level": level,
        "feedback": feedback
    }
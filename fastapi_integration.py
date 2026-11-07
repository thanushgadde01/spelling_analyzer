"""
FastAPI Integration for Spelling Analyzer
Compatible with the modular spell.py
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import os

# Import from the modular spell.py instead of spelling_analyzer.py
from spell import (
    load_dictionary,
    correct_text,
    analyze_spelling,
    determine_level_and_feedback,
    append_entry_to_master
)

# ============================================================================
# FASTAPI APP SETUP
# ============================================================================

app = FastAPI(
    title="Spelling Analyzer API",
    description="API for analyzing and correcting English spelling mistakes",
    version="1.0.0"
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# GLOBAL DICTIONARY - Load once at startup
# ============================================================================

DICTIONARY_PATH = os.getenv("DICT_PATH", "big.txt")
MASTER_CSV_PATH = os.getenv("MASTER_CSV_PATH", "master.csv")

# Global variable to store the loaded dictionary
WORD_FREQ_DICT = None

@app.on_event("startup")
async def startup_event():
    """Load dictionary when the API starts"""
    global WORD_FREQ_DICT
    print(f"📚 Loading dictionary from {DICTIONARY_PATH}...")
    WORD_FREQ_DICT = load_dictionary(DICTIONARY_PATH)
    
    if not WORD_FREQ_DICT:
        print("⚠️  WARNING: Dictionary is empty. Spell correction may not work!")
    else:
        print(f"✅ Dictionary loaded with {len(WORD_FREQ_DICT)} unique words")

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class SentenceRequest(BaseModel):
    """Request model for sentence analysis"""
    text: str = Field(..., min_length=1, description="Text to analyze for spelling mistakes")
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "I havv a drream to becme a softwre enginear"
            }
        }


class AnalysisResponse(BaseModel):
    """Response model for analysis results"""
    original: str
    corrected: str
    total_words: int
    mistakes: int
    percentage: float
    level: str
    feedback: str


class UserDataRequest(BaseModel):
    """Request model for saving user data with analysis"""
    text: str
    name: str
    age: Optional[str] = None
    study: Optional[str] = None
    graduated: Optional[str] = None
    occupation: Optional[str] = None
    hobbies: Optional[str] = None
    goal: Optional[str] = None
    self_intro: Optional[str] = None


class SaveResponse(BaseModel):
    """Response model for save operations"""
    success: bool
    message: str
    analysis: AnalysisResponse


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "Spelling Analyzer API",
        "version": "1.0.0",
        "dictionary_loaded": WORD_FREQ_DICT is not None and len(WORD_FREQ_DICT) > 0
    }


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_sentence(request: SentenceRequest):
    """
    Analyze a sentence for spelling mistakes.
    
    This endpoint:
    1. Tokenizes the input text
    2. Corrects spelling using Peter Norvig's algorithm
    3. Calculates mistake statistics
    4. Provides proficiency level and feedback
    
    Args:
        request: SentenceRequest with text to analyze
        
    Returns:
        AnalysisResponse with analysis results
    """
    # Check if dictionary is loaded
    if not WORD_FREQ_DICT:
        raise HTTPException(
            status_code=503,
            detail="Dictionary not loaded. Service unavailable."
        )
    
    try:
        # 1. Correct the text using the modular function
        original_words, corrected_words, corrected_text = correct_text(
            request.text, 
            WORD_FREQ_DICT
        )
        
        # 2. Analyze spelling mistakes
        stats = analyze_spelling(original_words, corrected_words)
        
        # 3. Get feedback based on mistake percentage
        level, feedback = determine_level_and_feedback(stats['mistake_percentage'])
        
        # 4. Return structured response
        return AnalysisResponse(
            original=request.text,
            corrected=corrected_text,
            total_words=stats['total_words'],
            mistakes=stats['mistakes'],
            percentage=round(stats['mistake_percentage'], 2),
            level=level,
            feedback=feedback
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing text: {str(e)}"
        )


@app.post("/analyze-and-save", response_model=SaveResponse)
async def analyze_and_save(request: UserDataRequest):
    """
    Analyze text and save results with user data to master CSV.
    
    This endpoint:
    1. Performs spelling analysis
    2. Saves results along with user profile data to master.csv
    3. Returns analysis results
    
    Args:
        request: UserDataRequest with text and user profile data
        
    Returns:
        SaveResponse with success status and analysis results
    """
    # Check if dictionary is loaded
    if not WORD_FREQ_DICT:
        raise HTTPException(
            status_code=503,
            detail="Dictionary not loaded. Service unavailable."
        )
    
    try:
        # 1. Perform analysis
        original_words, corrected_words, corrected_text = correct_text(
            request.text, 
            WORD_FREQ_DICT
        )
        
        stats = analyze_spelling(original_words, corrected_words)
        level, feedback = determine_level_and_feedback(stats['mistake_percentage'])
        
        # 2. Prepare entry for master CSV
        entry = {
            "Name": request.name,
            "Age": request.age,
            "Study": request.study,
            "Graduated": request.graduated,
            "Occupation": request.occupation,
            "Hobbies": request.hobbies,
            "Goal": request.goal,
            "Self_Intro": request.self_intro,
            "Original_Input": request.text,
            "Corrected_Input": corrected_text,
            "Total_Words": stats['total_words'],
            "Mistakes": stats['mistakes'],
            "Mistake_Percentage": stats['mistake_percentage'],
            "Level": level,
            "Feedback": feedback
        }
        
        # 3. Save to master CSV
        append_entry_to_master(entry, MASTER_CSV_PATH)
        
        # 4. Return response
        analysis = AnalysisResponse(
            original=request.text,
            corrected=corrected_text,
            total_words=stats['total_words'],
            mistakes=stats['mistakes'],
            percentage=round(stats['mistake_percentage'], 2),
            level=level,
            feedback=feedback
        )
        
        return SaveResponse(
            success=True,
            message="Analysis completed and data saved successfully",
            analysis=analysis
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing request: {str(e)}"
        )


@app.get("/stats")
async def get_statistics():
    """
    Get overall statistics from master CSV.
    
    Returns:
        Statistics about all stored analyses
    """
    try:
        import pandas as pd
        
        if not os.path.exists(MASTER_CSV_PATH):
            return {
                "total_entries": 0,
                "unique_users": 0,
                "message": "No data available yet"
            }
        
        df = pd.read_csv(MASTER_CSV_PATH)
        
        return {
            "total_entries": len(df),
            "unique_users": df['Name'].nunique(),
            "average_mistake_percentage": round(df['Mistake_Percentage'].mean(), 2),
            "level_distribution": df['Level'].value_counts().to_dict(),
            "total_words_analyzed": df['Total_Words'].sum(),
            "total_mistakes_found": df['Mistakes'].sum()
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving statistics: {str(e)}"
        )


# ============================================================================
# COMPATIBILITY NOTE
# ============================================================================

"""
COMPARISON WITH YOUR FASTAPI CODE:

YOUR CODE (from spelling_engine):
    from spelling_engine import correction, get_feedback
    
    corrected_words = [correction(w) for w in words]
    level, feedback = get_feedback(percentage)

MY MODULAR CODE (spell):
    from spell import (
        correct_text,
        determine_level_and_feedback
    )
    
    original_words, corrected_words, corrected_text = correct_text(text, word_freq_dict)
    level, feedback = determine_level_and_feedback(percentage)

KEY DIFFERENCES:
1. Function names are different:
   - Your: correction() → My: correct_word()
   - Your: get_feedback() → My: determine_level_and_feedback()

2. My functions require word_freq_dict parameter (the loaded dictionary)
3. My correct_text() returns tuple of (original, corrected, corrected_text)

SOLUTION:
This fastapi_integration.py file properly uses the modular spell
functions and maintains the same API contract as your original FastAPI code.
"""

# ============================================================================
# RUN INSTRUCTIONS
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("""
    🚀 Starting Spelling Analyzer API...
    
    📖 API Documentation will be available at:
       http://localhost:8000/docs
    
    🔧 Environment Variables:
       DICT_PATH - Path to dictionary file (default: big.txt)
       MASTER_CSV_PATH - Path to master CSV (default: master.csv)
    
    Example usage:
       curl -X POST "http://localhost:8000/analyze" \\
            -H "Content-Type: application/json" \\
            -d '{"text": "I havv a drream"}'
    """)
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

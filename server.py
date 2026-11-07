"""
Complete Backend for Spelling Analyzer
FastAPI server that connects with React frontend
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import os
import sys

# Add parent directory to path to import spell
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from spell import (
        load_dictionary,
        correct_text,
        analyze_spelling,
        determine_level_and_feedback,
        append_entry_to_master
    )
except ImportError:
    print("Error: spell.py not found. Make sure it's in the same directory.")
    sys.exit(1)

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
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:5173", "http://localhost:5174"],
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
    print("="*60)
    print("🚀 Starting Spelling Analyzer API")
    print("="*60)
    print(f"📚 Loading dictionary from: {DICTIONARY_PATH}")
    
    WORD_FREQ_DICT = load_dictionary(DICTIONARY_PATH)
    
    if not WORD_FREQ_DICT:
        print("⚠️  WARNING: Dictionary is empty or not found!")
        print(f"   Please ensure {DICTIONARY_PATH} exists")
    else:
        print(f"✅ Dictionary loaded successfully!")
        print(f"   Total words: {len(WORD_FREQ_DICT):,}")
    
    print(f"💾 Master CSV path: {MASTER_CSV_PATH}")
    print("="*60)
    print("🌐 Server is ready!")
    print("📖 API Documentation: http://localhost:8000/docs")
    print("="*60)

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class SentenceRequest(BaseModel):
    """Request model for simple sentence analysis"""
    text: str = Field(..., min_length=1, description="Text to analyze")
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "I havv a drream to becme a softwre enginear"
            }
        }


class UserDataRequest(BaseModel):
    """Request model for full user data with analysis"""
    text: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    age: Optional[str] = None
    study: Optional[str] = None
    graduated: Optional[str] = "no"
    occupation: Optional[str] = None
    hobbies: Optional[str] = None
    goal: Optional[str] = None
    self_intro: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "I lovv programing and want to becme a softwre enginear",
                "name": "John Doe",
                "age": "25",
                "study": "Computer Science",
                "graduated": "yes",
                "occupation": "Developer",
                "hobbies": "Reading, Coding",
                "goal": "Become a Tech Lead",
                "self_intro": "I am a passionate developer..."
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
        "dictionary_loaded": WORD_FREQ_DICT is not None and len(WORD_FREQ_DICT) > 0,
        "dictionary_size": len(WORD_FREQ_DICT) if WORD_FREQ_DICT else 0,
        "endpoints": {
            "analyze": "POST /analyze - Simple text analysis",
            "analyze_and_save": "POST /analyze-and-save - Analyze and save to CSV",
            "stats": "GET /stats - Get statistics from database",
            "docs": "GET /docs - API documentation"
        }
    }


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_sentence(request: SentenceRequest):
    """
    Analyze a sentence for spelling mistakes (without saving).
    
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
            detail={
                "error": "Dictionary not loaded",
                "message": f"Please ensure {DICTIONARY_PATH} exists and contains valid data"
            }
        )
    
    try:
        # 1. Correct the text
        original_words, corrected_words, corrected_text = correct_text(
            request.text, 
            WORD_FREQ_DICT
        )
        
        # 2. Analyze spelling mistakes
        stats = analyze_spelling(original_words, corrected_words)
        
        # 3. Get feedback
        level, feedback = determine_level_and_feedback(stats['mistake_percentage'])
        
        # 4. Return results
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
            detail={
                "error": "Analysis failed",
                "message": str(e)
            }
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
            detail={
                "error": "Dictionary not loaded",
                "message": f"Please ensure {DICTIONARY_PATH} exists and contains valid data"
            }
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
            "Age": request.age or "",
            "Study": request.study or "",
            "Graduated": request.graduated or "no",
            "Occupation": request.occupation or "",
            "Hobbies": request.hobbies or "",
            "Goal": request.goal or "",
            "Self_Intro": request.self_intro or "",
            "Original_Input": request.text,
            "Corrected_Input": corrected_text,
            "Total_Words": stats['total_words'],
            "Mistakes": stats['mistakes'],
            "Mistake_Percentage": stats['mistake_percentage'],
            "Level": level,
            "Feedback": feedback
        }
        
        # 3. Save to master CSV
        print(f"💾 Saving entry for user: {request.name}")
        append_entry_to_master(entry, MASTER_CSV_PATH)
        print(f"✅ Entry saved successfully!")
        
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
            message=f"Analysis completed and saved successfully for {request.name}",
            analysis=analysis
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Processing failed",
                "message": str(e)
            }
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
                "message": "No data available yet. Submit your first analysis!"
            }
        
        df = pd.read_csv(MASTER_CSV_PATH)
        
        if df.empty:
            return {
                "total_entries": 0,
                "unique_users": 0,
                "message": "Database is empty"
            }
        
        # Calculate statistics
        stats = {
            "total_entries": len(df),
            "unique_users": int(df['Name'].nunique()),
            "average_mistake_percentage": round(float(df['Mistake_Percentage'].mean()), 2),
            "total_words_analyzed": int(df['Total_Words'].sum()),
            "total_mistakes_found": int(df['Mistakes'].sum()),
            "level_distribution": df['Level'].value_counts().to_dict(),
            "best_performer": {
                "name": df.loc[df['Mistake_Percentage'].idxmin(), 'Name'],
                "percentage": round(float(df['Mistake_Percentage'].min()), 2)
            },
            "most_active_user": {
                "name": df['Name'].value_counts().index[0],
                "sessions": int(df['Name'].value_counts().iloc[0])
            }
        }
        
        return stats
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to retrieve statistics",
                "message": str(e)
            }
        )


@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "dictionary": {
            "loaded": WORD_FREQ_DICT is not None,
            "size": len(WORD_FREQ_DICT) if WORD_FREQ_DICT else 0,
            "path": DICTIONARY_PATH
        },
        "database": {
            "path": MASTER_CSV_PATH,
            "exists": os.path.exists(MASTER_CSV_PATH)
        }
    }


# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("""
    ============================================================
    SPELLING ANALYZER API - STARTING SERVER
    ============================================================
    
    API Documentation:  http://localhost:8000/docs
    Health Check:       http://localhost:8000/health
    Statistics:         http://localhost:8000/stats
    
    Make sure:
       1. spelling_analyzer.py is in the same directory
       2. big.txt dictionary file exists
       3. React frontend runs on http://localhost:3000
    
    Press CTRL+C to stop the server
    """)
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000, 
        reload=False,
        log_level="info"
    )

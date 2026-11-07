"""
FastAPI server for the Spelling Analyzer.

Run:  cd backend && uvicorn server:app --reload --port 8000
Env:  DICT_PATH, BIGRAM_PATH, MASTER_CSV_PATH, CORS_ORIGINS, USE_LANGUAGETOOL=1
"""
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from spell import SpellChecker, determine_level_and_feedback
from storage import append_entry_to_master, load_or_create_master_csv

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("spelling.server")

BASE_DIR = Path(__file__).resolve().parent            # paths no longer depend on the working directory
DICT_PATH = os.getenv("DICT_PATH") or None            # None -> bundled clean frequency dictionary
BIGRAM_PATH = os.getenv("BIGRAM_PATH") or None
MASTER_CSV_PATH = Path(os.getenv("MASTER_CSV_PATH", BASE_DIR / "master.csv"))
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:3001,http://localhost:5173,http://localhost:5174",
).split(",")

checker: Optional[SpellChecker] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global checker
    # Fail fast with a clear message instead of silently running with an empty dictionary.
    checker = SpellChecker(dictionary_path=DICT_PATH, bigram_path=BIGRAM_PATH)
    if checker.size < 1000:
        raise RuntimeError(f"Dictionary looks wrong: only {checker.size} words loaded (DICT_PATH={DICT_PATH}).")
    log.info("Dictionary loaded: %s words | master CSV: %s", f"{checker.size:,}", MASTER_CSV_PATH)
    yield


app = FastAPI(title="Spelling Analyzer API", version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


# ---------------------------------------------------------------- models
class SentenceRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=20000)
    ignore_words: List[str] = Field(default_factory=list, description="Names/terms that must never be flagged")
    auto_correct: bool = True


class UserDataRequest(SentenceRequest):
    name: str = Field(..., min_length=1)
    age: Optional[str] = None
    study: Optional[str] = None
    graduated: Optional[str] = "no"
    occupation: Optional[str] = None
    hobbies: Optional[str] = None
    goal: Optional[str] = None
    self_intro: Optional[str] = None


class CorrectionOut(BaseModel):
    start: int
    end: int
    original: str
    suggestion: str
    suggestions: List[str]
    confidence: float
    kind: str            # "spelling" | "context"
    applied: bool


class GrammarOut(BaseModel):
    start: int
    end: int
    original: str
    suggestion: str
    message: str
    rule: str


class AnalysisResponse(BaseModel):
    # unchanged fields (the React app keeps working)
    original: str
    corrected: str
    total_words: int
    mistakes: int                # spelling mistakes
    percentage: float            # spelling mistake %
    level: str
    feedback: str
    # new fields
    grammar_issues: int
    grammar_percentage: float
    corrections: List[CorrectionOut]
    grammar: List[GrammarOut]


class SaveResponse(BaseModel):
    success: bool
    message: str
    analysis: AnalysisResponse


# ---------------------------------------------------------------- helpers
def _require_checker() -> SpellChecker:
    if checker is None:
        raise HTTPException(503, detail="Dictionary not loaded")
    return checker


def _run(req: SentenceRequest) -> AnalysisResponse:
    result = _require_checker().check(req.text, ignore_words=req.ignore_words, auto_apply=req.auto_correct)
    level, feedback = determine_level_and_feedback(result.spelling_percentage, result.grammar_percentage)
    return AnalysisResponse(
        original=result.original, corrected=result.corrected, total_words=result.total_words,
        mistakes=result.spelling_mistakes, percentage=round(result.spelling_percentage, 2),
        level=level, feedback=feedback,
        grammar_issues=len(result.grammar), grammar_percentage=round(result.grammar_percentage, 2),
        corrections=[CorrectionOut(**vars(c)) for c in result.corrections],
        grammar=[GrammarOut(**vars(g)) for g in result.grammar],
    )


# ---------------------------------------------------------------- endpoints
# Plain `def` (not async): the work is CPU-bound, so FastAPI runs it in a worker thread.
@app.get("/")
def root():
    return {"status": "running", "service": "Spelling Analyzer API", "version": app.version,
            "dictionary_size": checker.size if checker else 0}


@app.get("/health")
def health():
    return {"status": "healthy" if checker else "starting",
            "dictionary": {"loaded": checker is not None, "size": checker.size if checker else 0},
            "database": {"path": str(MASTER_CSV_PATH), "exists": MASTER_CSV_PATH.exists()}}


@app.post("/analyze", response_model=AnalysisResponse)
def analyze(req: SentenceRequest):
    return _run(req)


@app.post("/analyze-and-save", response_model=SaveResponse)
def analyze_and_save(req: UserDataRequest):
    analysis = _run(req)
    append_entry_to_master({
        "Name": req.name, "Age": req.age or "", "Study": req.study or "",
        "Graduated": req.graduated or "no", "Occupation": req.occupation or "",
        "Hobbies": req.hobbies or "", "Goal": req.goal or "", "Self_Intro": req.self_intro or "",
        "Original_Input": req.text, "Corrected_Input": analysis.corrected,
        "Total_Words": analysis.total_words, "Mistakes": analysis.mistakes,
        "Mistake_Percentage": analysis.percentage, "Grammar_Issues": analysis.grammar_issues,
        "Level": analysis.level, "Feedback": analysis.feedback,
    }, MASTER_CSV_PATH)
    return SaveResponse(success=True, message=f"Analysis saved for {req.name}", analysis=analysis)


@app.get("/stats")
def stats():
    df = load_or_create_master_csv(MASTER_CSV_PATH)
    if df.empty:
        return {"total_entries": 0, "unique_users": 0, "message": "No data yet. Submit your first analysis!"}
    counts = df["Name"].value_counts()
    return {
        "total_entries": len(df),
        "unique_users": int(df["Name"].nunique()),
        "average_mistake_percentage": round(float(df["Mistake_Percentage"].mean()), 2),
        "total_words_analyzed": int(df["Total_Words"].sum()),
        "total_mistakes_found": int(df["Mistakes"].sum()),
        "level_distribution": df["Level"].value_counts().to_dict(),
        "best_performer": {"name": df.loc[df["Mistake_Percentage"].idxmin(), "Name"],
                           "percentage": round(float(df["Mistake_Percentage"].min()), 2)},
        "most_active_user": {"name": counts.index[0], "sessions": int(counts.iloc[0])},
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)

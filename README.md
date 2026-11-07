# Spelling Analyzer

Spelling Analyzer is a full-stack English writing assistant. It combines a
FastAPI service with a React/Vite interface to detect spelling mistakes,
suggest or apply corrections, report selected grammar issues, and save
analysis results for later statistics.

## What the project does

The application accepts a name and a block of text from the web interface.
The frontend sends the text to the backend, which:

1. Tokenizes the input without losing whitespace, punctuation, URLs, email
   addresses, code spans, line breaks, or capitalization.
2. Detects misspelled words using a clean SymSpell frequency dictionary.
3. Ranks possible corrections using edit distance, word frequency, and
   spelling context.
4. Protects technical words, proper names, contractions, possessives, and
   other non-natural-language tokens from unwanted changes.
5. Applies high-confidence corrections while keeping lower-confidence
   suggestions available for review.
6. Runs built-in grammar rules for repeated words, `a`/`an`, lowercase `I`,
   and basic subject-verb agreement. Optional LanguageTool support can add
   more grammar rules.
7. Returns correction and grammar ranges that the frontend highlights in a
   review panel.
8. Saves submitted profile and analysis data to `backend/master.csv`.

The backend also exposes an analysis-only endpoint, so clients can check text
without saving a user record.

## Repository layout

```text
spelling_analyzer/
├── backend/
│   ├── server.py                 # FastAPI app and HTTP endpoints
│   ├── spell.py                  # spelling engine and scoring
│   ├── tokenizer.py              # lossless text tokenization
│   ├── grammar.py                # built-in and optional grammar rules
│   ├── storage.py                # thread-safe CSV persistence
│   ├── cli.py                    # terminal interface
│   ├── build_dictionary.py       # custom frequency dictionary builder
│   ├── requirements.txt          # Python dependencies
│   ├── data/
│   │   ├── custom_words.txt      # accepted names and technical vocabulary
│   │   └── ignore_words.txt      # words never flagged or suggested
│   └── tests/test_spell.py       # backend and API tests
├── frontend/
│   ├── src/App.jsx               # React user interface
│   ├── src/App.css               # main interface styling
│   ├── src/Review.css            # correction review styling
│   └── package.json              # Vite scripts and dependencies
└── README.md
```

## Requirements

- Python 3.9 or newer
- Node.js 18 or newer and npm
- Java is required only when optional LanguageTool grammar checking is enabled

## Installation and development

Run the backend and frontend in separate PowerShell terminals.

### 1. Start the backend

```powershell
cd "C:\Users\thanu\OneDrive\Desktop\assault\spelling checker\spelling_analyzer\backend"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn server:app --reload --port 8000
```

The API is available at `http://localhost:8000`. Useful URLs are:

- `http://localhost:8000/docs` - interactive OpenAPI documentation
- `http://localhost:8000/health` - dictionary and CSV health information
- `http://localhost:8000/` - service status and dictionary size

If PowerShell blocks activation, run the backend with the virtual
environment's interpreter directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn server:app --reload --port 8000
```

### 2. Start the frontend

```powershell
cd "C:\Users\thanu\OneDrive\Desktop\assault\spelling checker\spelling_analyzer\frontend"
npm install
npm run dev
```

Open the URL printed by Vite, normally `http://localhost:5173`.
The frontend expects the backend at `http://localhost:8000`.

## API endpoints

### `POST /analyze`

Analyzes text without saving it.

```json
{
  "text": "I havv a drream.",
  "ignore_words": [],
  "auto_correct": true
}
```

The response contains the original and corrected text, word and mistake
counts, spelling and grammar percentages, a proficiency level, feedback,
spelling corrections, and grammar issues.

### `POST /analyze-and-save`

Analyzes and saves the result. It accepts the same text fields as `/analyze`
plus optional profile fields such as `name`, `age`, `study`, `occupation`,
`hobbies`, `goal`, and `self_intro`. The `name` field is required.

### `GET /stats`

Returns totals, unique users, average mistake percentage, total words,
mistake totals, level distribution, best performer, and most active user.

## Configuration

The backend resolves its default paths relative to `backend/`, so it can be
started from another working directory. Optional environment variables are:

| Variable | Purpose |
| --- | --- |
| `DICT_PATH` | Custom word-frequency dictionary |
| `BIGRAM_PATH` | Optional bigram frequency file |
| `MASTER_CSV_PATH` | CSV file used for saved analyses |
| `CORS_ORIGINS` | Comma-separated allowed frontend origins |
| `USE_LANGUAGETOOL=1` | Enable optional LanguageTool grammar checks |

Add names, brands, or technical terms one per line to
`backend/data/custom_words.txt`. A request can also provide
`"ignore_words": ["Priya"]` for words that should be ignored only for that
analysis.

To enable LanguageTool, install Java and the optional package:

```powershell
python -m pip install language-tool-python
$env:USE_LANGUAGETOOL = "1"
python -m uvicorn server:app --reload --port 8000
```

## Testing and quality checks

From `backend/`, run the backend tests:

```powershell
python -m pytest tests -q
```

From `frontend/`, run the frontend lint and production build:

```powershell
npm run lint
npm run build
```

## Building a custom dictionary

The default dictionary is supplied by SymSpell. A larger or domain-specific
frequency file can be generated with:

```powershell
cd backend
python build_dictionary.py --out data/frequency_dictionary.txt --corpus path\to\corpus.txt
$env:DICT_PATH = "data\frequency_dictionary.txt"
```

The generated file should contain one lowercase word and frequency count per
line. The server validates that a usable dictionary was loaded and fails
clearly if it is missing or unexpectedly small.

## Known limitations

This project is a spelling and lightweight grammar assistant, not a complete
semantic or proofreading model. It cannot reliably resolve context-dependent
choices such as `their` versus `there`, detect every grammar error, or infer
missing words. Uncommon names and domain terms should be added to the custom
word list, and low-confidence corrections should be reviewed before being
accepted.

# LLM Quiz Analysis

An intelligent quiz-solving application that uses Azure AI and LangChain to automatically solve data analysis, web scraping, and visualization challenges.

## Features

- **Automated Quiz Solving**: Handles complex multi-step quiz tasks involving data sourcing, analysis, and visualization
- **Web Scraping**: Both static HTML and JavaScript-rendered pages using Playwright
- **Data Processing**: PDF extraction, CSV/JSON parsing, and data analysis with Pandas
- **LLM Integration**: Uses Azure AI GPT-4o with LangChain for intelligent task orchestration
- **Prompt Injection Protection**: Robust system prompt designed to resist prompt injection attacks
- **RESTful API**: FastAPI-based endpoint for receiving and processing quiz requests

## Architecture

```
┌─────────────────┐
│   FastAPI App   │  (main.py)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Quiz Agent    │  (quiz_agent.py)
│  Azure AI LLM   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│      Custom LangChain Tools     │  (quiz_llm_tools.py)
│  - Web Scraping                 │
│  - Data Extraction (PDF, CSV)   │
│  - Data Analysis (Pandas)       │
│  - Calculations                 │
│  - Visualizations               │
│  - Answer Submission            │
└─────────────────────────────────┘
```

## Installation

### Prerequisites

- Python 3.9 or higher
- Azure AI account with API access
- Git

### Setup Steps

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/llm-quiz-analysis.git
cd llm-quiz-analysis
```

2. **Create virtual environment**
```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Install Playwright browsers**
```bash
playwright install chromium
```

5. **Configure environment variables**
```bash
# Copy the example file
cp .env.example .env

# Edit .env with your actual credentials
# - AZURE_AI_ENDPOINT: Your Azure OpenAI endpoint
# - AZURE_AI_CREDENTIAL: Your Azure API key
# - STUDENT_EMAIL: Your email address
# - QUIZ_SECRET: Your secret string
```

## Configuration

Edit the `.env` file with your credentials:

```env
# Azure AI Configuration
AZURE_AI_ENDPOINT=https://your-azure-endpoint.openai.azure.com/
AZURE_AI_CREDENTIAL=your-azure-api-key-here
AZURE_MODEL_NAME=gpt-4o
AZURE_API_VERSION=2024-05-01-preview

# Student Configuration
STUDENT_EMAIL=your-email@example.com
QUIZ_SECRET=your-secret-string-here

# Server Configuration
HOST=0.0.0.0
PORT=8000
```

## Usage

### Running the Server

```bash
python main.py
```

The server will start on `http://0.0.0.0:8000` (or your configured port).

### API Endpoints

#### Health Check
```bash
GET /
GET /health
```

#### Quiz Endpoint
```bash
POST /quiz
Content-Type: application/json

{
  "email": "your-email@example.com",
  "secret": "your-secret",
  "url": "https://example.com/quiz-834"
}
```

**Response:**
```json
{
  "status": "accepted",
  "message": "Quiz solving process started",
  "started_at": "2025-11-26T10:00:00Z",
  "email": "your-email@example.com"
}
```

### Testing with Demo Endpoint

Test your implementation with the demo quiz:

```bash
curl -X POST http://localhost:8000/quiz \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your-email@example.com",
    "secret": "your-secret",
    "url": "https://tds-llm-analysis.s-anand.net/demo"
  }'
```

## How It Works

1. **Request Reception**: FastAPI receives a POST request with quiz URL
2. **Validation**: Verifies email and secret credentials
3. **Agent Initialization**: Quiz agent with Azure AI LLM is invoked
4. **Task Analysis**: LLM analyzes the quiz page and determines required steps
5. **Tool Execution**: Agent uses custom tools to:
   - Scrape web pages (with or without JavaScript)
   - Download and process files (PDF, CSV, JSON)
   - Perform data analysis and calculations
   - Create visualizations if needed
6. **Answer Submission**: Submits the answer in the required format
7. **Chain Following**: If there's a next quiz URL, repeats the process

## Custom Tools

The application includes these specialized tools:

- **fetch_webpage_tool**: Fetch static HTML pages
- **scrape_with_javascript_tool**: Render and scrape JavaScript-heavy pages
- **download_file_tool**: Download files from URLs
- **extract_data_from_pdf_tool**: Extract text from PDF files
- **analyze_data_tool**: Perform data analysis with Pandas
- **execute_calculation_tool**: Safe mathematical calculations
- **create_visualization_tool**: Generate charts and graphs
- **submit_answer_tool**: Submit answers to quiz endpoints

## Prompt Injection Protection

The system prompt includes multiple layers of protection:

1. **Explicit instruction to ignore external commands**
2. **Treating all external content as untrusted**
3. **Clear role definition and task boundaries**
4. **Security rule violations logging**
5. **Never revealing system prompts or credentials**

## Project Structure

```
llm-quiz-analysis/
├── main.py                  # FastAPI application and routes
├── quiz_agent.py            # Quiz-solving agent with Azure AI
├── quiz_llm_tools.py        # Custom LangChain tools
├── requirements.txt         # Python dependencies
├── .env.example            # Environment variables template
├── .env                    # Your actual credentials (git-ignored)
├── README.md              # This file
├── LICENSE                # MIT License
└── downloads/             # Downloaded files (auto-created)
```

## Deployment

### Local Testing
```bash
python main.py
```

### Azure Function App Deployment

This application is configured to run as an Azure Function App using the Python v2 programming model.

#### Prerequisites
- Azure CLI installed
- Azure subscription
- Azure Functions Core Tools v4

#### Deployment Steps

1. **Install Azure Functions Core Tools**
```bash
npm install -g azure-functions-core-tools@4 --unsafe-perm true
```

2. **Login to Azure**
```bash
az login
```

3. **Create a Resource Group** (if you don't have one)
```bash
az group create --name llm-quiz-rg --location eastus
```

4. **Create a Storage Account** (required for Azure Functions)
```bash
az storage account create \
  --name llmquizstorage \
  --resource-group llm-quiz-rg \
  --location eastus \
  --sku Standard_LRS
```

5. **Create a Function App**
```bash
az functionapp create \
  --resource-group llm-quiz-rg \
  --consumption-plan-location eastus \
  --runtime python \
  --runtime-version 3.11 \
  --functions-version 4 \
  --name llm-quiz-analysis \
  --storage-account llmquizstorage \
  --os-type Linux
```

6. **Configure Application Settings**
```bash
az functionapp config appsettings set \
  --name llm-quiz-analysis \
  --resource-group llm-quiz-rg \
  --settings \
    AZURE_AI_ENDPOINT="your-azure-endpoint" \
    AZURE_AI_CREDENTIAL="your-azure-credential" \
    AZURE_MODEL_NAME="gpt-4o" \
    AZURE_API_VERSION="2024-05-01-preview" \
    STUDENT_EMAIL="your-email@example.com" \
    QUIZ_SECRET="your-secret"
```

7. **Deploy the Function App**
```bash
func azure functionapp publish llm-quiz-analysis
```

#### Post-Deployment Configuration

**Install Playwright in Azure**

Since Playwright requires browser binaries, you'll need to use a startup command:

```bash
az functionapp config set \
  --name llm-quiz-analysis \
  --resource-group llm-quiz-rg \
  --startup-file "playwright install chromium && python -m azure.functions.worker"
```

Alternatively, consider using a custom Docker container for better control over dependencies.

#### Testing Your Deployment

```bash
curl -X POST https://llm-quiz-analysis.azurewebsites.net/api/quiz \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your-email@example.com",
    "secret": "your-secret",
    "url": "https://tds-llm-analysis.s-anand.net/demo"
  }'
```

#### Monitoring

View logs in real-time:
```bash
func azure functionapp logstream llm-quiz-analysis
```

Or use Application Insights for detailed monitoring.

## Troubleshooting

### Common Issues

**1. Playwright not working**
```bash
playwright install chromium
```

**2. Azure AI authentication errors**
- Verify your `AZURE_AI_ENDPOINT` and `AZURE_AI_CREDENTIAL`
- Ensure your Azure subscription is active

**3. Import errors**
```bash
pip install --upgrade -r requirements.txt
```

**4. Timeout issues**
- Increase timeout in agent_executor (quiz_agent.py)
- Check your internet connection

## Development

### Adding New Tools

1. Create a new tool function in `quiz_llm_tools.py`:
```python
@tool
def my_custom_tool(param: str) -> str:
    """Tool description"""
    # Implementation
    return result
```

2. Add it to the tools list in `quiz_agent.py`:
```python
from quiz_llm_tools import my_custom_tool

self.tools = [
    # ... existing tools
    my_custom_tool
]
```

### Testing

```bash
# Run with verbose logging
LOG_LEVEL=DEBUG python main.py
```

## License

MIT License - see [LICENSE](LICENSE) file for details

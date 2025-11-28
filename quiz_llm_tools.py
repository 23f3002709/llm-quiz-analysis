"""
Custom LangChain tools for quiz solving
Includes tools for web scraping, data extraction, analysis, and submission
"""
import os
import base64
import json
import logging
import math
from typing import Dict, Any, Optional, Union
from io import BytesIO, StringIO
import asyncio

import httpx
import pandas as pd
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader
from langchain_core.tools import tool

# Optional imports with graceful fallback
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-GUI backend
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

logger = logging.getLogger(__name__)


# ============================================================================
# Helper Functions
# ============================================================================

def _extract_clean_text(soup: BeautifulSoup) -> str:
    """
    Extract clean text from a BeautifulSoup object.
    Removes scripts, styles, and normalizes whitespace.

    Args:
        soup: BeautifulSoup object

    Returns:
        Clean text content
    """
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()

    # Get text content
    text = soup.get_text()

    # Clean up whitespace
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)

    return text


# ============================================================================
# Web Scraping and Data Fetching Tools
# ============================================================================

@tool
def fetch_webpage_tool(url: str) -> str:
    """
    Fetch a webpage and return its HTML content.
    Use this for static HTML pages that don't require JavaScript execution.

    Args:
        url: The URL to fetch

    Returns:
        HTML content as string
    """
    try:
        logger.info(f"Fetching webpage: {url}")
        response = httpx.get(url, timeout=30.0, follow_redirects=True)
        response.raise_for_status()

        # Parse with BeautifulSoup and extract clean text
        soup = BeautifulSoup(response.text, 'html.parser')
        text = _extract_clean_text(soup)

        logger.info(f"Successfully fetched {len(text)} characters from {url}")
        return text

    except Exception as e:
        logger.error(f"Error fetching webpage {url}: {str(e)}")
        return f"Error fetching webpage: {str(e)}"


@tool
def scrape_with_javascript_tool(url: str) -> str:
    """
    Fetch and render a webpage with JavaScript execution using Playwright.
    Use this when the page requires DOM execution or JavaScript rendering.

    Args:
        url: The URL to scrape

    Returns:
        Rendered HTML content as string
    """
    if not PLAYWRIGHT_AVAILABLE:
        return "Error: Playwright is not installed. Run: pip install playwright && playwright install chromium"

    try:
        logger.info(f"Scraping with JavaScript: {url}")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Navigate and wait for page to load
            page.goto(url, wait_until="networkidle", timeout=30000)

            # Wait for dynamic content
            page.wait_for_timeout(2000)

            # Get the rendered HTML content
            content = page.content()

            browser.close()

        # Parse with BeautifulSoup and extract clean text
        soup = BeautifulSoup(content, 'html.parser')
        text = _extract_clean_text(soup)

        logger.info(f"Successfully scraped {len(text)} characters from {url}")
        return text

    except Exception as e:
        logger.error(f"Error scraping with JavaScript {url}: {str(e)}")
        return f"Error scraping with JavaScript: {str(e)}"


@tool
def download_file_tool(url: str) -> str:
    """
    Download a file from a URL and save it locally.
    Returns the local file path.

    Args:
        url: URL of the file to download

    Returns:
        Local file path where the file was saved
    """
    try:
        logger.info(f"Downloading file from: {url}")

        response = httpx.get(url, timeout=60.0, follow_redirects=True)
        response.raise_for_status()

        # Determine filename from URL or Content-Disposition header
        filename = url.split('/')[-1].split('?')[0]
        if 'content-disposition' in response.headers:
            content_disp = response.headers['content-disposition']
            if 'filename=' in content_disp:
                filename = content_disp.split('filename=')[1].strip('"')

        # Save to downloads directory
        downloads_dir = os.path.join(os.getcwd(), 'downloads')
        os.makedirs(downloads_dir, exist_ok=True)

        file_path = os.path.join(downloads_dir, filename)

        with open(file_path, 'wb') as f:
            f.write(response.content)

        logger.info(f"File downloaded successfully to: {file_path}")
        return file_path

    except Exception as e:
        logger.error(f"Error downloading file from {url}: {str(e)}")
        return f"Error downloading file: {str(e)}"


# ============================================================================
# Data Extraction Tools
# ============================================================================

@tool
def extract_data_from_pdf_tool(file_path: str) -> str:
    """
    Extract text and tables from a PDF file.

    Args:
        file_path: Path to the PDF file

    Returns:
        Extracted text content from all pages
    """
    try:
        logger.info(f"Extracting data from PDF: {file_path}")

        reader = PdfReader(file_path)
        num_pages = len(reader.pages)

        extracted_text = f"PDF has {num_pages} pages\n\n"

        for i, page in enumerate(reader.pages, 1):
            text = page.extract_text()
            extracted_text += f"=== Page {i} ===\n{text}\n\n"

        logger.info(f"Successfully extracted {len(extracted_text)} characters from PDF")
        return extracted_text

    except Exception as e:
        logger.error(f"Error extracting data from PDF {file_path}: {str(e)}")
        return f"Error extracting PDF data: {str(e)}"


# ============================================================================
# Data Analysis Tools
# ============================================================================

@tool
def analyze_data_tool(data_description: str) -> str:
    """
    Analyze data based on the description provided.
    This can parse CSV data, JSON data, or perform analysis on structured data.

    Args:
        data_description: JSON string containing 'data' and 'operation' fields.
            - data: Can be CSV string, JSON string, or file path
            - operation: Type of analysis (sum, mean, count, filter, sort, etc.)
            - column: Column name for operation (if applicable)
            - condition: Filter condition (if applicable)

    Returns:
        Result of the analysis as string
    """
    try:
        logger.info("Analyzing data")

        # Parse the input
        params = json.loads(data_description)
        data_input = params.get('data', '')
        operation = params.get('operation', 'describe')
        column = params.get('column')
        condition = params.get('condition')

        # Load data into DataFrame
        df = None

        # Try to detect data format
        if data_input.endswith('.csv') or os.path.isfile(data_input):
            # File path
            if data_input.endswith('.csv'):
                df = pd.read_csv(data_input)
            elif data_input.endswith('.json'):
                df = pd.read_json(data_input)
            elif data_input.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(data_input)
        elif data_input.startswith('[') or data_input.startswith('{'):
            # JSON string
            df = pd.read_json(BytesIO(data_input.encode()))
        else:
            # Try CSV string
            df = pd.read_csv(StringIO(data_input))

        if df is None or df.empty:
            return "Error: Could not load data"

        # Perform requested operation
        result = None

        if operation == 'sum' and column:
            result = df[column].sum()
        elif operation == 'mean' and column:
            result = df[column].mean()
        elif operation == 'count':
            result = len(df)
        elif operation == 'describe':
            result = df.describe().to_string()
        elif operation == 'columns':
            result = df.columns.tolist()
        elif operation == 'head':
            result = df.head(10).to_string()
        elif operation == 'filter' and condition:
            # Simple filtering (this is basic, can be enhanced)
            filtered_df = df.query(condition)
            result = filtered_df.to_string()
        elif operation == 'aggregate':
            # Custom aggregation
            result = df.agg(params.get('agg_func', 'sum')).to_string()
        else:
            result = f"Data shape: {df.shape}\nColumns: {df.columns.tolist()}\n\n{df.head().to_string()}"

        logger.info(f"Analysis completed: {operation}")
        return str(result)

    except Exception as e:
        logger.error(f"Error analyzing data: {str(e)}")
        return f"Error analyzing data: {str(e)}"


@tool
def execute_calculation_tool(expression: str) -> str:
    """
    Execute a mathematical calculation or Python expression safely.

    Args:
        expression: Mathematical expression to evaluate (e.g., "2 + 2", "sum([1,2,3])")

    Returns:
        Result of the calculation
    """
    try:
        logger.info(f"Executing calculation: {expression}")

        # Safe evaluation using restricted globals
        allowed_names = {
            'abs': abs, 'round': round, 'min': min, 'max': max,
            'sum': sum, 'len': len, 'int': int, 'float': float,
            'pow': pow, 'divmod': divmod,
        }

        # Also allow math functions
        for name in dir(math):
            if not name.startswith('_'):
                allowed_names[name] = getattr(math, name)

        result = eval(expression, {"__builtins__": {}}, allowed_names)

        logger.info(f"Calculation result: {result}")
        return str(result)

    except Exception as e:
        logger.error(f"Error executing calculation: {str(e)}")
        return f"Error executing calculation: {str(e)}"


# ============================================================================
# Visualization Tools
# ============================================================================

@tool
def create_visualization_tool(viz_params: str) -> str:
    """
    Create a data visualization (chart/graph) and return as base64-encoded image.

    Args:
        viz_params: JSON string with visualization parameters:
            - type: Type of chart (bar, line, scatter, pie, etc.)
            - data: Data to visualize (JSON or CSV string)
            - x_column: Column for x-axis
            - y_column: Column for y-axis
            - title: Chart title

    Returns:
        Base64-encoded image URI (data:image/png;base64,...)
    """
    if not MATPLOTLIB_AVAILABLE:
        return "Error: Matplotlib is not installed. Run: pip install matplotlib"

    try:
        logger.info("Creating visualization")

        params = json.loads(viz_params)
        chart_type = params.get('type', 'bar')
        data_input = params.get('data', '')
        x_col = params.get('x_column')
        y_col = params.get('y_column')
        title = params.get('title', 'Chart')

        # Load data
        if data_input.startswith('[') or data_input.startswith('{'):
            df = pd.read_json(BytesIO(data_input.encode()))
        else:
            df = pd.read_csv(StringIO(data_input))

        # Create plot
        fig, ax = plt.subplots(figsize=(10, 6))

        if chart_type == 'bar':
            df.plot(kind='bar', x=x_col, y=y_col, ax=ax)
        elif chart_type == 'line':
            df.plot(kind='line', x=x_col, y=y_col, ax=ax)
        elif chart_type == 'scatter':
            df.plot(kind='scatter', x=x_col, y=y_col, ax=ax)
        elif chart_type == 'pie':
            df.set_index(x_col)[y_col].plot(kind='pie', ax=ax)
        else:
            df.plot(ax=ax)

        ax.set_title(title)
        plt.tight_layout()

        # Save to bytes buffer
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        plt.close()

        # Encode to base64
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        data_uri = f"data:image/png;base64,{img_base64}"

        logger.info("Visualization created successfully")
        return data_uri

    except Exception as e:
        logger.error(f"Error creating visualization: {str(e)}")
        return f"Error creating visualization: {str(e)}"


# ============================================================================
# Answer Submission Tool
# ============================================================================

@tool
def submit_answer_tool(submission_data: str) -> str:
    """
    Submit an answer to the quiz endpoint.

    Args:
        submission_data: JSON string containing:
            - submit_url: URL to submit the answer to
            - email: Student email
            - secret: Student secret
            - url: Quiz URL
            - answer: The answer (can be number, string, boolean, JSON object, or base64 URI)

    Returns:
        Response from the submission endpoint
    """
    try:
        logger.info("Submitting answer")

        params = json.loads(submission_data)
        submit_url = params.get('submit_url')
        email = params.get('email')
        secret = params.get('secret')
        quiz_url = params.get('url')
        answer = params.get('answer')

        if not all([submit_url, email, secret, quiz_url]):
            return "Error: Missing required submission parameters"

        # Prepare payload
        payload = {
            "email": email,
            "secret": secret,
            "url": quiz_url,
            "answer": answer
        }

        # Check payload size (must be under 1MB)
        payload_json = json.dumps(payload)
        payload_size = len(payload_json.encode('utf-8'))

        if payload_size > 1_000_000:
            return f"Error: Payload size ({payload_size} bytes) exceeds 1MB limit"

        logger.info(f"Submitting to {submit_url}")
        logger.info(f"Answer: {answer}")

        # Submit
        response = httpx.post(
            submit_url,
            json=payload,
            timeout=30.0
        )

        response_data = response.json()

        logger.info(f"Submission response: {response_data}")

        # Format response
        correct = response_data.get('correct', False)
        reason = response_data.get('reason', '')
        next_url = response_data.get('url', '')

        result = f"Submission result: {'CORRECT' if correct else 'INCORRECT'}\n"
        if reason:
            result += f"Reason: {reason}\n"
        if next_url:
            result += f"Next quiz URL: {next_url}\n"

        return result

    except Exception as e:
        logger.error(f"Error submitting answer: {str(e)}")
        return f"Error submitting answer: {str(e)}"


# ============================================================================
# Export tools for agent
# ============================================================================

# Create tool list for easy import
all_tools = [
    fetch_webpage_tool,
    scrape_with_javascript_tool,
    download_file_tool,
    extract_data_from_pdf_tool,
    analyze_data_tool,
    execute_calculation_tool,
    create_visualization_tool,
    submit_answer_tool
]

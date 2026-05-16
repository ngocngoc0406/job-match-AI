# NCKH Job Matching System

## Quick Start

1. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```

2. **Ensure `merged_jobs.xlsx` is in the root directory**

3. **Run the app:**
   ```
   python main.py
   ```
   or
   ```
   python web/app.py
   ```

4. **Open browser:** http://127.0.0.1:5000

## Features
- CV upload & skill extraction
- Job matching with knowledge graph
- AI Interview practice
- Salary estimation
- Job search & dashboard

## Troubleshooting
- **SyntaxError in web/app.py**: Delete lines around 467-470 with backslashes, ensure proper indentation
- **merged_jobs.xlsx not found**: Place Excel file in project root
- **Module not found**: Run `pip install -r requirements.txt`

Server ready at http://127.0.0.1:5000

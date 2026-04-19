# OptimaCV Job Aggregator — User Guide

Welcome to **OptimaCV**, your advanced stealth job collection system. This guide will help you set up and run the application successfully.

## 📋 Prerequisites

Before running the application, ensure you have the following:

1.  **MySQL Database**: A running MySQL instance (local or remote).
2.  **Gemini API Key**: An API key from [Google AI Studio](https://aistudio.google.com/) to enable AI filtering of jobs.
3.  **Environment Setup**: You must configure your `.env` file with these credentials.

## 🚀 Getting Started

### 1. Configure the Environment
Create a file named `.env` in the same folder as the application (if it doesn't exist) and add the following:

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASS=your_password
DB_NAME=jobs
GEMINI_API_KEY=your_gemini_api_key_here
```

### 2. Launch the Application
- **Double-click `OptimaCV.exe`** (in the `dist` folder after building).
- The app will initialize the engine and open a native desktop window.
- Follow the onboarding steps to reach the dashboard.

### 3. First Run (Playwright)
The first time you run the scraper, it may need to download the Playwright browser binaries. This happens automatically in the background, but ensure you have an active internet connection.

## 🛠️ Build from Source (Developers Only)

If you made changes to the code and want to create a new `.exe`:

1.  Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    pip install pyinstaller
    ```
2.  Run the build script:
    ```bash
    python build_windows.py
    ```
3.  Find your new executable in the `dist/` folder.

## ❓ Troubleshooting

-   **App won't start**: Check if another instance of Streamlit is running on port 8501.
-   **Database Error**: Ensure your MySQL server is running and the credentials in `.env` are correct.
-   **No jobs found**: Verify your Gemini API key and internet connection. Check `logs/scraper.log` for detailed system output.

---
*Built with ❤️ for professional job hunting.*

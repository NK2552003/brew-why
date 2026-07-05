# Contributing to brew-why

First off, thank you for considering contributing to `brew-why`! It's people like you that make open source tools great.

## 💻 Development Setup

1. **Fork and Clone the Repository:**
   ```bash
   git clone https://github.com/yourusername/brew-why.git
   cd brew-why
   ```

2. **Set up a Virtual Environment:**
   We recommend using `venv` to keep your development environment isolated.
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies in editable mode:**
   ```bash
   pip install -e .
   ```

You can now run `brew-why` directly from your terminal, and any changes you make to the source code in `src/brew_why` will be reflected immediately!

## 🏗️ Architecture Overview
*   **`cli.py`**: The Typer application and command router. If you are adding a new CLI command, add it here.
*   **`core.py`**: The business logic, caching, and threading engine. If you need to manipulate data from Homebrew, do it here.
*   **`brew.py`**: Subprocess abstraction for communicating with the actual `brew` CLI tool.
*   **`display.py`**: Rich rendering components (Tables, Panels, Trees).
*   **`tui.py`**: The interactive Textual dashboard.

## 🐛 Submitting Bugs
If you find a bug, please create an Issue and include:
*   Your macOS version.
*   Your Python version.
*   The exact command you ran.
*   The full output (run the command with the `--debug` flag to get a traceback!).

## ✨ Submitting Pull Requests
1. Create a new branch (`git checkout -b feature/AmazingFeature`).
2. Make your changes.
3. Test your changes locally to ensure the CLI still runs and parses Homebrew outputs correctly.
4. Commit your changes (`git commit -m 'Add some AmazingFeature'`).
5. Push to the branch (`git push origin feature/AmazingFeature`).
6. Open a Pull Request.

Happy coding! 🚀

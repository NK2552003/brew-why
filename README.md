<div align="center">
  <h1>🍺 brew-why</h1>
  <p><strong>A beautiful, fast CLI to explain why your Homebrew dependencies are installed and figure out what is safe to remove.</strong></p>
  
  <p>
    <img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="Python Version">
    <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
    <img src="https://img.shields.io/badge/maintained-yes-brightgreen.svg" alt="Maintained">
  </p>
</div>

---

## 🤔 The Problem
Over the years, you've run `brew install x` dozens of times. Your Mac is getting full, and when you type `brew list`, you see hundreds of packages like `icu4c`, `pcre2`, or `libvmaf`. 
*Why are they there? Are they safe to delete? How much space are they taking?*

## 💡 The Solution
`brew-why` parses your entire Homebrew dependency graph and presents it in a beautiful, human-readable terminal UI. It categorizes your packages, highlights orphans, audits for security updates, and provides a full interactive dashboard to manage your system.

---

## ✨ Features
- **📊 Overview Tables:** See exactly which packages you installed vs. which were pulled in as dependencies.
- **🧹 Orphan Detection:** Identifies packages that are completely safe to remove and calculates exactly how much disk space you will recover.
- **🏋️ Heaviest Packages:** Instantly rank the largest packages in your Homebrew Cellar.
- **🌳 Reverse Trees:** See exactly what depends on a specific package using visual graphs.
- **🛡️ Security Audits:** Automatically highlights outdated packages that need a `brew upgrade`.
- **💻 Interactive Dashboard:** A full-screen, responsive Textual TUI to browse your environment.

---

## 🚀 Installation

The recommended way to install `brew-why` is using `pipx` (to keep the dependencies isolated from your system Python).

```bash
# 1. Install pipx if you don't have it
brew install pipx
pipx ensurepath

# 2. Install brew-why
pipx install git+https://github.com/nk2552003/brew-why.git
```

Alternatively, you can clone the repository and run the local install script:
```bash
git clone https://github.com/nk2552003/brew-why.git
cd brew-why
./install.sh
```

---

## 📚 Usage

### 1. The Interactive Dashboard (Recommended)
Launch the full-screen interactive Textual interface:
```bash
brew-why dashboard
```

### 2. Dependency Overview
Print a categorized summary of all your packages directly to standard out:
```bash
brew-why overview
```

### 3. Deep-dive into a single package
Find out exactly why a specific package is on your system:
```bash
brew-why explain <package_name>
# Example: brew-why explain openssl
```

### 4. Find the Disk Space Hogs
List the top 15 largest packages taking up space on your Mac:
```bash
brew-why heaviest
```

### 5. Reverse Dependency Trees
Find out every package that traces its lineage back to a specific library:
```bash
brew-why reverse-tree <package_name>
```

### 6. Security Audits
List all user-installed packages (and their dependencies) that are currently outdated:
```bash
brew-why audit
```

---

## 🛠️ Built With
- **[Typer](https://typer.tiangolo.com/):** For robust, typed CLI routing.
- **[Rich](https://rich.readthedocs.io/):** For beautiful console rendering (tables, panels, spinners).
- **[Textual](https://textual.textualize.io/):** For the interactive TUI dashboard.

---

## 🤝 Contributing
Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.
Please see the [CONTRIBUTING.md](CONTRIBUTING.md) file for more details.

## 📝 License
Distributed under the MIT License. See [LICENSE](LICENSE) for more information.

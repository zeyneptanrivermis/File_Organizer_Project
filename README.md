# Smart File Organizer v2.0

Smart File Organizer is a modern desktop automation tool that helps you organize your Downloads folder within seconds. It automatically categorizes files by type, such as Images, Documents, Code Files, Videos, and more, while also providing detailed organization reports.

---

## Key Features

- ** Organize Instantly:** Scans all existing files with a single click and moves them into categorized folders based on their file types.
- ** Automatic Watcher:** Runs in the background and detects newly added files in real time, organizing them automatically.
- ** Visual Reporting:** Provides ASCII bar chart reports inside the application interface, showing both overall system statistics and current folder status.
- ** Smart Naming:** Cleans special characters from filenames and creates unique names instead of overwriting files with the same name.
- ** Modern Interface:** Offers a simple, dark-mode supported desktop UI for a more user-friendly experience.

---

##  How to Use

### Method 1: Direct Usage (Recommended)

To use the application without installing Python or any additional software:

1. Go to the **Releases** section on the right side of this repository.
2. Download the latest `Smart_File_Organizer_v2.exe` file.
3. Run the executable file.

> **Note:** Windows Defender may show an "Unknown Publisher" warning.  
> Click **More Info** and then **Run Anyway** to start the application.

---

### Method 2: Developer / Source Code Mode

If you want to run or improve the project from the source code:

1. Clone the repository:

```bash
git clone https://github.com/TNNladie/File_Organizer_Project.git
cd File_Organizer_Project
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the application:

```bash
python app_gui.py
```

---

##  Configuration

The program targets your system's **Downloads folder** by default.

You can customize the settings using the `config.json` file in the project root directory.

### config.json Options

- **`file_extensions`** - Defines which file extensions should be moved to which category folders
- **`source_directory`** - Defines the main folder path to be scanned (by default, represents the system Downloads folder)

Example `config.json`:

```json
{
  "source_directory": "C:/Users/YourUsername/Downloads",
  "file_extensions": {
    "Images": [".jpg", ".png", ".gif", ".bmp", ".svg"],
    "Documents": [".pdf", ".docx", ".txt", ".xlsx"],
    "Videos": [".mp4", ".avi", ".mkv", ".mov"],
    "Code Files": [".py", ".js", ".java", ".cpp", ".html"],
    "Archives": [".zip", ".rar", ".7z", ".tar"]
  }
}
```

---

##  Technologies Used

- **Python** - Core programming language
- **CustomTkinter** - Modern desktop GUI with dark mode support
- **Watchdog** - Real-time file system monitoring
- **PyInstaller** - Packaging the application as a single `.exe` file

---

##  System Requirements

- **Operating System:** Windows 10 or higher
- **Python Version:** 3.8+ (if running from source)
- **Disk Space:** Minimal (less than 100 MB)
- **RAM:** Minimal requirements

---

##  Project Structure

```
File_Organizer_Project/
├── app_gui.py              # Main GUI application file
├── file_organizer.py       # Core file organization logic
├── config.json             # Configuration file
├── requirements.txt        # Python dependencies
├── README.md               # Documentation
└── .gitignore             # Git ignore file
```

---

##  Use Cases

- **Clean Downloads Folder** - Automatically organize cluttered downloads
- **Bulk File Organization** - Sort large amounts of mixed file types
- **Real-time Monitoring** - Keep your folder organized as new files arrive
- **Personal Productivity** - Save time on manual file management
- **Desktop Cleanup** - Organize any directory on your system

---

##  Example Report

The application generates ASCII bar charts showing:

```
 Downloads Folder Statistics

Images    ████████████░░░░░░░  45%
Documents ██████████░░░░░░░░░░ 30%
Videos    ████░░░░░░░░░░░░░░░░ 15%
Archives  ██░░░░░░░░░░░░░░░░░░  8%
Code      ░░░░░░░░░░░░░░░░░░░░  2%
```

---

##  Privacy & Security

- The application works **entirely offline**
- No data is sent to external servers
- All file operations are performed locally on your system
- No tracking or telemetry

---

##  Future Improvements

- [ ] Support for macOS and Linux
- [ ] Cloud storage integration (Google Drive, OneDrive)
- [ ] Custom category creation via GUI
- [ ] Undo/Restore functionality
- [ ] Scheduled organization tasks
- [ ] File preview feature
- [ ] Multi-language support

---

##  License

This project was developed for **educational and personal productivity purposes**.


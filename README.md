# Data Table Manager

A powerful desktop application for managing comic/magazine data with intelligent parsing, table management, and multiple export formats.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![PyQt6](https://img.shields.io/badge/GUI-PyQt6-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## Features

### 🎯 Core Functionality
- **7-Column Data Management** - websign, author, title, group, show, magazine, origin
- **Intelligent Data Parsing** - Automatically extracts structured data from text input
- **Real-time Duplicate Detection** - Highlights duplicate websign values
- **Three-State Sorting System** - Ascending, descending, and original order
- **Built-in ZIP Image Viewer** - View images directly from ZIP archives
- **Image Operations** - Delete and stitch images with undo support

### 📁 File Format Support
- **TXT** - Human-readable text format
- **XLSX** - Excel spreadsheet format
- **JSON** - Structured data interchange format

### 🖥️ User Interface
- **Modern GUI** - Built with PyQt6
- **Enhanced Table Widget** - Custom sorting and visual features
- **Context Menus** - Right-click operations for quick actions
- **Keyboard Shortcuts** - Ctrl+F for search, Delete for row removal

### 🔧 Advanced Features
- **Web Data Fetching** - Automatically fetch data from configured websites
- **Configuration Management** - Persistent settings for websites and library paths
- **Asynchronous Operations** - Non-blocking UI for long-running tasks
- **Comprehensive Error Handling** - User-friendly error messages

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Step-by-Step Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/data-table-manager.git
   cd data-table-manager
   ```

2. **Create a virtual environment (recommended)**
    ```bash
    python -m venv venv
    # On Windows:
    venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    ```

3. **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

### Starting the Application
    ```bash
    python main.py
    ```

### Basic Workflow

1. **Import Data**
- Use `File → Import` to load data from TXT, XLSX, or JSON files
- Or use the insert dialog to add individual entries

2. **Data Entry Formats**
    ```text
    123456 (Show Info) [Group Name (Author Name)] Title Text (Magazine Name)
    ```

3. **Table Operations**
- Sort columns by clicking headers
- Use right-click context menu for quick actions
- Search and filter using `Ctrl+F` or the search dialog

4. **Export Data**
- Use `File → Save` and choose your preferred format
- Supported formats: TXT, XLSX, JSON

### Keyboard Shortcuts
- `Ctrl+F` - Open search dialog
- `Delete` - Delete selected rows
- `Enter` in insert dialog - Confirm input

## Project Structure
    ```text
    data_table_manager/
    ├── main.py                 # Application entry point
    ├── models/                 # Data models and business logic
    │   ├── config_manager.py   # Configuration management
    │   ├── data_parser.py      # Intelligent text parsing
    │   └── zip_image_manager.py # ZIP image operations
    ├── views/                  # User interface components
    │   ├── main_window.py      # Main application window
    │   ├── dialogs.py          # Various dialogs (insert, search)
    │   ├── image_viewer.py     # ZIP image viewer
    │   └── enhanced_table.py   # Enhanced table widget
    ├── controllers/            # Application controllers
    │   ├── file_io.py          # File operations (TXT, XLSX, JSON)
    │   ├── table_controller.py # Table data management
    │   ├── web_controller.py   # Web and settings control
    │   ├── state_manager.py    # UI state management
    │   └── table_visual_manager.py # Table visual features
    └── utils/                  # Utility functions
        ├── file_locator.py     # File search utilities
        ├── user_agents.py      # Random User-Agent generation
        └── helpers.py          # Helper functions
    ```

## Configuration
- The application automatically creates a `config.ini` file with the following sections:
- **WebSettings** - Configure JM and distribution websites
- **LibSettings** - Set library path for ZIP files
- **ViewSettings** - Adjust slide show speed and other UI preferences
- **WindowState** - Remember window size and position

## Development

### Code Style
- Follow PEP 8 guidelines
- Use type hints where possible
- Write docstrings for all public methods

### Adding New Features
- 1. Follow the existing MVC architecture pattern
- 2. Add tests for new functionality
- 3. Update documentation accordingly

### Contributing
- We welcome contributions! Please feel free to submit pull requests, report bugs, or suggest new features.
- 1. Fork the repository
- 2. Create a feature branch (`git checkout -b feature/amazing-feature`)
- 3. Commit your changes (`git commit -m 'Add some amazing feature'`)
- 4. Push to the branch (`git push origin feature/amazing-feature`)
- 5. Open a Pull Request

### License
- This project is licensed under the MIT License - see the LICENSE file for details.

### Support
- If you encounter any issues or have questions:
- 1. Check the Issues page
- 2. Create a new issue with detailed description
- 3. Provide steps to reproduce the problem

### Acknowledgments
- Built with PyQt6 for the GUI
- Uses pandas for Excel file handling
- BeautifulSoup for web scraping capabilities
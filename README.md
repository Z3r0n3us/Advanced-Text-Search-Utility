# Advanced Text Search Utility

## Description

The Advanced Text Search Utility is a powerful, interactive command-line tool designed for efficient and flexible searching across multiple text files. It combines the functionality of grep, awk, and sed with additional features like fuzzy matching, parallel processing, and result filtering.

## Features

- Simple and case-insensitive searches
- Multiple term searches
- Regular expression support
- Field extraction using AWK
- Search and replace using SED
- Fuzzy matching
- File type filtering
- Parallel processing for faster searches
- Interactive result filtering
- Export results in various formats (txt, json, csv)
- Search history and command repetition
- Detailed search statistics

## Installation

1. Clone this repository:
it clone https://github.com/yourusername/advanced-text-search.git
cd advanced-text-search



2. Create a virtual environment (optional but recommended):
python -m venv venv
source venv/bin/activate # On Windows, use venv\Scripts\activate



3. Install the required packages:
pip install -r requirements.txt



## Usage

Run the script using Python:

python text_search.py


Follow the interactive prompts to:
1. Specify the file pattern to search
2. Choose search options
3. Execute the search
4. Filter, save, or perform new searches on the results

## Examples

Here are some example use cases:

1. Search for a simple term in all text files:
   - File pattern: `*.txt`
   - Search option: Simple Search
   - Term: "example"

2. Perform a case-insensitive search for multiple terms:
   - File pattern: `*.log`
   - Search option: Case-Insensitive Search
   - Terms: "error,warning,critical"

3. Use regular expressions to find email addresses:
   - File pattern: `*.md`
   - Search option: Regular Expression Search
   - Regex: `\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b`

4. Extract specific fields from log files:
   - File pattern: `app.log`
   - Search option: Extract Specific Field (AWK)
   - Pattern: `$3 == "ERROR"`
   - Action: `{print $1, $2, $4}`

## Contributing

Contributions to the Advanced Text Search Utility are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
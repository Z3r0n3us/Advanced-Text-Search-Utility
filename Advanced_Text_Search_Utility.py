import os
import subprocess
import textwrap
import re
import glob
import mmap
import readline
import atexit
import colorama
from colorama import Fore, Style
import json
import csv
from tqdm import tqdm
import concurrent.futures
from fuzzywuzzy import fuzz
import configparser

colorama.init(autoreset=True)

HISTORY_FILE = os.path.expanduser('~/.text_search_history')
CONFIG_FILE = os.path.expanduser('~/.text_search_config')

def setup_history():
    if os.path.exists(HISTORY_FILE):
        readline.read_history_file(HISTORY_FILE)
    atexit.register(readline.write_history_file, HISTORY_FILE)

def load_config():
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
    return config

def save_config(config):
    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)

def complete_path(text, state):
    if '~' in text:
        text = os.path.expanduser(text)
    if os.path.isdir(text):
        text += '/'
    return (glob.glob(text + '*') + [None])[state]

def run_command(command, preview=False):
    try:
        if preview:
            command += " | head -n 2"
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"An error occurred: {e}\n{e.stderr}"

def build_grep_command(file_pattern, options):
    command = f"grep --color=always"
    for opt in options:
        if opt['type'] == 'simple':
            command += f" {opt['option']} '{opt['term']}'"
        elif opt['type'] == 'multiple':
            terms = "|".join(opt['terms'])
            command += f" -E '{terms}'"
        elif opt['type'] == 'exclude':
            command += f" --exclude-pattern='{opt['term']}'"
        elif opt['type'] == 'regex':
            command += f" -P '{opt['term']}'"
    if 'show_line_numbers' in options:
        command += " -n"
    if 'context_lines' in options:
        command += f" -C {options['context_lines']}"
    command += f" {file_pattern}"
    return command

def build_awk_command(file_pattern, pattern, action):
    return f"awk '{pattern} {action}' {file_pattern}"

def build_sed_command(file_pattern, search_term, replace_term):
    return f"sed 's/{search_term}/{replace_term}/g' {file_pattern}"

def print_example(example):
    print("\nExample:")
    print(textwrap.indent(example, "  "))

def preview_file(file_pattern):
    print(f"\nPreview of {file_pattern}:")
    print(run_command(f"head -n 5 {file_pattern}"))

def search_large_file(file_path, pattern):
    with open(file_path, 'rb', 0) as file, mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as s:
        for line in iter(s.readline, b""):
            if re.search(pattern.encode(), line):
                yield line.decode().strip()

def fuzzy_search(file_path, term, threshold=80):
    results = []
    with open(file_path, 'r') as file:
        for line in file:
            if fuzz.partial_ratio(term, line) >= threshold:
                results.append(line.strip())
    return results

def search_file(file_path, command):
    result = run_command(f"{command} '{file_path}'")
    return file_path, result

def parallel_search(file_pattern, command):
    files = glob.glob(file_pattern)
    results = {}
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_file = {executor.submit(search_file, file, command): file for file in files}
        for future in tqdm(concurrent.futures.as_completed(future_to_file), total=len(files), desc="Searching files"):
            file = future_to_file[future]
            try:
                file_path, result = future.result()
                results[file_path] = result
            except Exception as exc:
                print(f'{file} generated an exception: {exc}')
    return results

def search_within_results(results):
    search_term = input("Enter the term to search within the results: ")
    filtered_results = {}
    for file, content in results.items():
        filtered_content = "\n".join([line for line in content.split("\n") if search_term.lower() in line.lower()])
        if filtered_content:
            filtered_results[file] = filtered_content
    return filtered_results

def get_search_options(file_pattern, config):
    options = []
    show_line_numbers = False
    context_lines = 0
    while True:
        print("\nChoose a search option to add:")
        print("1. Simple Search")
        print("2. Case-Insensitive Search")
        print("3. Search for Multiple Terms")
        print("4. Extract Specific Field (AWK)")
        print("5. Search and Replace (SED)")
        print("6. Regular Expression Search")
        print("7. Exclude Pattern")
        print("8. Show Line Numbers")
        print("9. Show Context Lines")
        print("10. Fuzzy Search")
        print("11. Filter by File Type")
        print("12. Finish and Execute Search")
        
        choice = input("Enter your choice (1-12): ")
        
        if choice == '1':
            print_example("Simple Search:\nFinds lines containing an exact match of the search term.")
            term = input("Enter the term to search for: ")
            options.append({'type': 'simple', 'option': '', 'term': term})
        elif choice == '2':
            print_example("Case-Insensitive Search:\nFinds lines containing the search term, ignoring case.")
            term = input("Enter the term to search for (case-insensitive): ")
            options.append({'type': 'simple', 'option': '-i', 'term': term})
        elif choice == '3':
            print_example("Search for Multiple Terms:\nFinds lines containing any of the specified terms.")
            terms = input("Enter the terms to search for, separated by commas: ").split(',')
            options.append({'type': 'multiple', 'terms': terms})
        elif choice == '4':
            print_example("Extract Specific Field (AWK):\nUses AWK to extract specific parts of lines that match a pattern.")
            pattern = input("Enter the pattern to search for: ")
            action = input("Enter the action to perform (e.g., '{print $1}' to print the first field): ")
            return build_awk_command(file_pattern, pattern, action)
        elif choice == '5':
            print_example("Search and Replace (SED):\nUses SED to replace occurrences of a term with another term.")
            search_term = input("Enter the term to search for: ")
            replace_term = input("Enter the term to replace it with: ")
            return build_sed_command(file_pattern, search_term, replace_term)
        elif choice == '6':
            print_example("Regular Expression Search:\nUses Perl-compatible regular expressions for advanced pattern matching.")
            regex = input("Enter the regular expression: ")
            options.append({'type': 'regex', 'term': regex})
        elif choice == '7':
            print_example("Exclude Pattern:\nExcludes lines that match the specified pattern.")
            exclude_pattern = input("Enter the pattern to exclude: ")
            options.append({'type': 'exclude', 'term': exclude_pattern})
        elif choice == '8':
            show_line_numbers = True
            print("Line numbers will be shown in the output.")
        elif choice == '9':
            context_lines = int(input("Enter the number of context lines to show: "))
        elif choice == '10':
            print_example("Fuzzy Search:\nFinds approximate matches using fuzzy string matching.")
            term = input("Enter the term for fuzzy search: ")
            threshold = int(input("Enter the similarity threshold (0-100): "))
            return lambda file: fuzzy_search(file, term, threshold)
        elif choice == '11':
            print_example("Filter by File Type:\nLimit the search to specific file types.")
            file_types = input("Enter file extensions to include, separated by commas (e.g., txt,py,md): ")
            file_pattern = f"*.{{{','.join(file_types.split(','))}}}"
            print(f"File pattern updated to: {file_pattern}")
        elif choice == '12':
            if options:
                if show_line_numbers:
                    options.append('show_line_numbers')
                if context_lines > 0:
                    options.append({'context_lines': context_lines})
                return build_grep_command(file_pattern, options)
            else:
                print("No search options selected. Please select at least one option.")
        else:
            print("Invalid choice. Please select a number between 1 and 12.")

def export_results(results, format, filename):
    if format == 'json':
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
    elif format == 'csv':
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['File', 'Results'])
            for file, result in results.items():
                writer.writerow([file, result])
    else:
        with open(filename, 'w') as f:
            for file, result in results.items():
                f.write(f"File: {file}\n")
                f.write(result)
                f.write("\n\n")

def print_statistics(results):
    total_matches = sum(len(result.split('\n')) for result in results.values())
    unique_matches = len(set(line for result in results.values() for line in result.split('\n')))
    print(f"\nSearch Statistics:")
    print(f"Total matches: {total_matches}")
    print(f"Unique matches: {unique_matches}")
    print(f"Files with matches: {len(results)}")


def main():
    setup_history()
    config = load_config()
    print("Welcome to the Advanced Text Search Utility!")
    
    # Set up tab completion for file paths
    readline.set_completer_delims(' \t\n;')
    readline.parse_and_bind("tab: complete")
    readline.set_completer(complete_path)
    
    file_pattern = input("Enter the file name or pattern to search (e.g., *.txt for all text files): ")
    
    # Reset completer after getting file pattern
    readline.set_completer(None)
    
    matching_files = glob.glob(file_pattern)
    if not matching_files:
        print("No matching files found. Please provide a valid file name or pattern.")
        return
    
    preview_file(file_pattern)

    search_history = []

    while True:
        command = get_search_options(file_pattern, config)
        
        print("\nPreview of search results:")
        preview = run_command(command, preview=True)
        print(preview)
        
        confirm = input("\nDo you want to execute this search? (y/n): ").lower()
        if confirm == 'y':
            print("\nSearching files...")
            results = parallel_search(file_pattern, command)
            
            print("\nSearch Results Summary:")
            for file, result in results.items():
                match_count = len(result.split('\n'))
                print(f"{file}: {match_count} matches")
            
            print_statistics(results)
            
            search_history.append(command)
            
            while True:
                action = input("\nWhat would you like to do next? (filter/save/new/quit): ").lower()
                if action == 'filter':
                    results = search_within_results(results)
                    print("\nFiltered Results Summary:")
                    for file, result in results.items():
                        match_count = len(result.split('\n'))
                        print(f"{file}: {match_count} matches")
                    print_statistics(results)
                elif action == 'save':
                    format = input("Enter the export format (txt/json/csv): ").lower()
                    output_file = input("Enter the name of the output file: ")
                    export_results(results, format, output_file)
                    print(f"Results saved to {output_file}")
                elif action == 'new':
                    break
                elif action == 'quit':
                    print("Thank you for using the Advanced Text Search Utility. Goodbye!")
                    return
                else:
                    print("Invalid action. Please choose filter, save, new, or quit.")
        
        another = input("\nDo you want to perform another search? (y/n): ").lower()
        if another != 'y':
            print("Thank you for using the Advanced Text Search Utility. Goodbye!")
            break
        
        history_option = input("Do you want to use a previous search from history? (y/n): ").lower()
        if history_option == 'y':
            print("\nSearch History:")
            for i, cmd in enumerate(search_history):
                print(f"{i+1}. {cmd}")
            history_choice = int(input("Enter the number of the search to repeat: ")) - 1
            if 0 <= history_choice < len(search_history):
                command = search_history[history_choice]
                print("\nRepeating search...")
                results = parallel_search(file_pattern, command)
                print("\nSearch Results Summary:")
                for file, result in results.items():
                    match_count = len(result.split('\n'))
                    print(f"{file}: {match_count} matches")
                print_statistics(results)
            else:
                print("Invalid choice. Continuing with a new search.")

if __name__ == "__main__":
    main()
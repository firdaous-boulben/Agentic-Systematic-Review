import os
import argparse

# Directories and files to ignore
IGNORE = {
    ".git",
    ".gitignore",
    ".env",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    ".idea",
    ".vscode",
    "dist",
    "build",
    ".pytest_cache",
    "tests",
    "data"
}

def display_tree(root, prefix="", show_files=True):
    try:
        entries = sorted(
            os.listdir(root),
            key=lambda x: (not os.path.isdir(os.path.join(root, x)), x.lower())
        )
    except PermissionError:
        return

    entries = [
        entry for entry in entries
        if entry not in IGNORE
    ]

    if not show_files:
        entries = [
            entry for entry in entries
            if os.path.isdir(os.path.join(root, entry))
        ]

    for index, entry in enumerate(entries):
        path = os.path.join(root, entry)
        is_last = index == len(entries) - 1

        connector = "└── " if is_last else "├── "
        print(prefix + connector + entry)

        if os.path.isdir(path):
            extension = "    " if is_last else "│   "
            display_tree(path, prefix + extension, show_files)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Display project architecture as a tree"
    )

    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Project root directory"
    )

    parser.add_argument(
        "--dirs-only",
        action="store_true",
        help="Display directories only"
    )

    args = parser.parse_args()

    root = os.path.abspath(args.path)

    print(os.path.basename(root) + "/")
    display_tree(root, show_files=not args.dirs_only)

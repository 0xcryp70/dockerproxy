# File: commit_msg_generator.py
#!/usr/bin/env python3

import os
import sys
import subprocess
from openai import OpenAI


def main():
    # Retrieve OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)

    # Get staged diff
    raw_diff = subprocess.check_output(["git", "diff", "--cached"]).decode("utf-8", errors="ignore")
    if not raw_diff.strip():
        print("No staged changes detected. Nothing to commit.", file=sys.stderr)
        sys.exit(0)

    # If the diff is too large, fall back to a summary (diffstat)
    max_chars = 10_000  # adjust threshold as needed
    if len(raw_diff) > max_chars:
        summary = subprocess.check_output(["git", "diff", "--cached", "--stat"]).decode("utf-8", errors="ignore")
        prompt = (
            "The staged diff is too large to process directly. "
            "Use the following summary of changes to craft a concise Git commit message:\n\n"
            f"{summary}\n\nCommit message:"
        )
    else:
        prompt = (
            "Write a concise, descriptive Git commit message summarizing the following diff:\n\n"
            f"{raw_diff}\n\nCommit message:"
        )

    # Call OpenAI API
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a Git assistant that crafts clear, concise commit messages."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.2
        )
    except Exception as e:
        print(f"OpenAI API error: {e}", file=sys.stderr)
        sys.exit(1)

    commit_msg = response.choices[0].message.content.strip()
    with open(sys.argv[1], "w") as msg_file:
        msg_file.write(commit_msg + "\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <path-to-commit-msg-file>", file=sys.stderr)
        sys.exit(1)
    main()


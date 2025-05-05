# File: commit_msg_generator.py
#!/usr/bin/env python3

import os
import sys
import subprocess
import openai

def main():
    # Retrieve OpenAI API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)
    openai.api_key = api_key

    # Get staged diff
    diff = subprocess.check_output(["git", "diff", "--cached"]).decode("utf-8")
    if not diff.strip():
        print("No staged changes detected. Nothing to commit.")
        sys.exit(0)

    # Build prompt for ChatGPT
    prompt = (
        "Write a concise, descriptive Git commit message summarizing the following diff."
        f"\n\n{diff}\n\nCommit message:"
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a Git assistant that crafts clear, concise commit messages."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.2,
        )
    except Exception as e:
        print(f"OpenAI API error: {e}", file=sys.stderr)
        sys.exit(1)

    commit_msg = response.choices[0].message.content.strip()

    # Write the generated message into the commit-msg file
    with open(sys.argv[1], "w") as msg_file:
        msg_file.write(commit_msg + "\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <path-to-commit-msg-file>", file=sys.stderr)
        sys.exit(1)
    main()

# File: .git/hooks/prepare-commit-msg
#!/bin/sh
# Git hook to auto-generate a commit message using ChatGPT
# Arguments: $1 = commit message file, $2 = commit source

# Skip generation for merges or if message is already provided
if [ "$2" = "merge" ] || [ "$2" = "message" ]; then
  exit 0
fi

# Call the Python script to generate and write the message
python3 commit_msg_generator.py "$1"


#!/usr/bin/env python3
"""Fix song_a_in_song_b detection by removing restrictive condition."""

with open("ui/app.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Fix line 2408: Remove len(embeddings_manip) > 1 condition
for i, line in enumerate(lines):
    if i == 2407:  # Line 2408 (0-indexed is 2407)
        # Replace the condition
        if "if scenario_type == 'song_a_in_song_b' and len(embeddings_manip) > 1:" in line:
            lines[i] = "    if scenario_type == 'song_a_in_song_b':\n"
            print(f"✓ Fixed line {i+1}: Removed len(embeddings_manip) > 1 condition")
            break

with open("ui/app.py", "w", encoding="utf-8") as f:
    f.writelines(lines)

print("✓ Fix applied successfully!")

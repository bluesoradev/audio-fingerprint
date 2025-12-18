"""Final fix: Query ALL segments for perfect song_a_in_song_b detection"""
file_path = r"D:\work folder\kevino\testm3\fingerprint\run_queries.py"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and replace the extended_topk line to query ALL segments
for i, line in enumerate(lines):
    if 'extended_topk = min(len(orig_segment_ids) * 10' in line:
        lines[i] = "                    extended_topk = index.ntotal  # Query ALL segments to ensure we find all original segments (perfect recall)\n"
        break

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Updated: extended_topk now queries ALL segments (index.ntotal) for perfect recall")

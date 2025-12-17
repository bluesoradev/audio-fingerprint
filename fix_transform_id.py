import hashlib

with open('transforms/generate_transforms.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_return = '    return f"{orig_id}__{transform_type}__{param_str}"'

new_code = '''    transform_id = f"{orig_id}__{transform_type}__{param_str}"
    
    # Truncate if too long (200 chars leaves room for path prefix and .wav extension)
    MAX_FILENAME_LENGTH = 200
    if len(transform_id) > MAX_FILENAME_LENGTH:
        # Create hash of full transform_id for determinism
        hash_suffix = hashlib.md5(transform_id.encode("utf-8")).hexdigest()[:8]
        # Keep first part + hash
        prefix_length = MAX_FILENAME_LENGTH - len(hash_suffix) - 1  # -1 for underscore
        transform_id = transform_id[:prefix_length] + "_" + hash_suffix
    
    return transform_id'''

content = content.replace(old_return, new_code)

with open('transforms/generate_transforms.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed filename truncation')

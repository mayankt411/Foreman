import sys, os
filepath = sys.argv[1]
hex_data = sys.argv[2]
os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
with open(filepath, 'wb') as f:
    f.write(bytes.fromhex(hex_data))
print(f'Successfully wrote {filepath}')

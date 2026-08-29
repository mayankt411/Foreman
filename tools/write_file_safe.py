import sys, os, base64
filepath = sys.argv[1]
b64_data = sys.argv[2]
os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
with open(filepath, 'wb') as f:
    f.write(base64.b64decode(b64_data))
print(f'Successfully wrote {filepath}')

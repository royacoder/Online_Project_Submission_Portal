import bcrypt

# The hash from schema.sql
phash = "$2y$10$eOPEo8Zq2sE5q1.0nO.7HOS7b7eO8/9U1wN4S590fO9aJ0W3xNyeG"
password = "admin123"

try:
    # Try directly
    result = bcrypt.checkpw(password.encode('utf-8'), phash.encode('utf-8'))
    print(f"Direct check result: {result}")
except Exception as e:
    print(f"Direct check error: {e}")

# Try with $2b$ replacement
try:
    new_hash = phash.replace('$2y$', '$2b$')
    result = bcrypt.checkpw(password.encode('utf-8'), new_hash.encode('utf-8'))
    print(f"Modified check result ($2b$): {result}")
except Exception as e:
    print(f"Modified check error: {e}")

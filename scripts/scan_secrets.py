import re
from pathlib import Path

patterns = [
    re.compile(r'sbp_[a-zA-Z0-9_-]+'),
    re.compile(r'eyJh[a-zA-Z0-9_\-\.]{50,}'),
    re.compile(r'AIza[a-zA-Z0-9_\-]{35}'),
    re.compile(r'SUPABASE_SERVICE_ROLE_KEY\s*=\s*["\'][^"\']+["\']')
]

matches_found = []
for p in Path('.').rglob('*'):
    if any(part in p.parts for part in ['.git', 'node_modules', '.pytest_cache', '__pycache__', 'dist', 'backups']):
        continue
    if p.is_file() and p.suffix in ['.py', '.js', '.jsx', '.json', '.md', '.sql', '.env']:
        try:
            content = p.read_text(encoding='utf-8', errors='ignore')
            for pat in patterns:
                matches = pat.findall(content)
                for m in matches:
                    if any(ign in m.lower() for ign in ['placeholder', 'your-', '<your', 'example', 'dummy']):
                        continue
                    matches_found.append((str(p), m[:15] + "..."))
        except Exception:
            pass

print(f"Secret scan completed. Found {len(matches_found)} suspicious tokens.")
for path, token_snippet in matches_found:
    print(f"  {path}: {token_snippet}")


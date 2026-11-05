# -*- coding: utf-8 -*-
import json

with open(r'C:\Users\modim\Code\Portfolio\index.html', encoding='utf-8') as f:
    content = f.read()

i1 = content.find('const challenges = [')
i2 = content.find(';\n\n// Sidebar')
data = json.loads(content[i1 + len('const challenges = '):i2])

print(f"Total challenges in HTML: {len(data)}\n")
for idx, c in enumerate(data, 1):
    fl = c['flag'] if c['flag'] else "(No flag)"
    print(f"{idx:02d}. [{c['event']}] [{c['category']}] {c['title']} -> {fl}")


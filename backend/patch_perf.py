import os
import glob
import re

for path in glob.glob('app/**/*.py', recursive=True):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if '[PERF' in content:
        # replace `print(f"[PERF...")` with:
        # with open("perf.log", "a") as f_log: f_log.write(f"[PERF...\n")
        # print(...)
        def replacer(match):
            print_stmt = match.group(0)
            inner_str = match.group(1) # f"[PERF...]"
            return f'with open("perf.log", "a") as f_log: f_log.write({inner_str} + "\\n")\n            {print_stmt}'
        
        new_content = re.sub(r'print\((f"\[PERF.*?")\)', replacer, content)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)

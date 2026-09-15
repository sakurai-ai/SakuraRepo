with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Let's find the exact block and replace it
import re

# Find everything between console.print(r""" and """)
pattern = r'console\.print\(r"""\n(.*?)"""\)'
match = re.search(pattern, content, flags=re.DOTALL)
if match:
    old_art = match.group(1)
    
    # Let's rebuild it cleanly
    new_art = old_art.replace('[#fcd1d7]', '').replace('[/#fcd1d7]', '')
    
    lines = new_art.split('\n')
    
    final_lines = []
    final_lines.append("[#fcd1d7]")
    
    for line in lines:
        if 'by sakuraidev' in line:
            line = line.replace('[#c3829e]', '').replace('[/#c3829e]', '')
            final_lines.append(f"             [#c3829e]by sakuraidev v1.0.0[/#c3829e]")
        elif '__' in line or '\/' in line or '`' in line or '/_/' in line:
            # this is part of YummyDL
            final_lines.append(f"[white]{line}[/white]")
        elif '⣿' in line or '⢈' in line or '⠀' in line:
            # Anime girl
            final_lines.append(line)
        else:
            final_lines.append(line)
            
    final_lines.append("[/#fcd1d7]")
    
    new_block = 'console.print(r"""\n' + '\n'.join(final_lines) + '\n""")'
    content = content[:match.start()] + new_block + content[match.end():]
    
    with open('main.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Success")
else:
    print("Failed to find pattern")

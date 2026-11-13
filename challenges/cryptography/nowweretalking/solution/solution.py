from pathlib import Path

report = Path("../dist/report_core1")

lines = report.read_text().splitlines()

header_index = next(i for i, line in enumerate(lines) if line.strip().startswith("sample"))

headers = lines[header_index].strip().split()
core1_index = headers.index("core1%")

core1_values = [
    int(line.split()[core1_index])
    for line in lines[header_index + 1:]
    if line.strip()
]

for i in range(len(core1_values)):
    core1_values[i] = 0 if core1_values[i] > 50 else 1
    
flag = "".join(
    chr(int("".join(map(str, core1_values[i:i+8])), 2))
    for i in range (0, len(core1_values), 8)
)

print(flag)

report = Path("../dist/report_core2")

lines = report.read_text().splitlines()

header_index = next(i for i, line in enumerate(lines) if line.strip().startswith("sample"))

headers = lines[header_index].strip().split()
core2_index = headers.index("core2%")

core2_values = [
    int(line.split()[core2_index])
    for line in lines[header_index + 1:]
    if line.strip()
]

for i in range(len(core2_values)):
    core2_values[i] = 0 if core2_values[i] > 50 else 1
    
flag = "".join(
    chr(int("".join(map(str, core2_values[i:i+8])), 2))
    for i in range (0, len(core2_values), 8)
)

print(flag)
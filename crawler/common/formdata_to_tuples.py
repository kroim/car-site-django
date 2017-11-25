lines = []
while(True):
    line = raw_input()
    if line == '':
        break
    lines.append(line.strip())

for line in lines:
    arr = line.split(':')
    print "('" + arr[0] + "','" + arr[1] + "'),"
import random

msg = ''
with open('../challenge.yml', 'r') as f:
    lines = f.readlines()
    for line in lines:
        if 'flag{' in line:
            msg = line.split(' ')[-1].strip()
            break
msg = msg[5:-1] # Remove flag wrapper

codewords = []
for char in msg:
    d = [int(bit) for bit in bin(ord(char))[2:].zfill(8)]
    d1 = d[:4]
    d2 = d[4:]

    p1 = d1[0] + d1[1] + d1[3] + 1
    p2 = d1[0] + d1[2] + d1[3] + 1
    p3 = d1[1] + d1[2] + d1[3] + 1

    codewords.append(f'{p1 % 2}{p2 % 2}{d1[0]}{p3 % 2}{d1[1]}{d1[2]}{d1[3]}')

    p1 = d2[0] + d2[1] + d2[3] + 1
    p2 = d2[0] + d2[2] + d2[3] + 1
    p3 = d2[1] + d2[2] + d2[3] + 1

    codewords.append(f'{p1 % 2}{p2 % 2}{d2[0]}{p3 % 2}{d2[1]}{d2[2]}{d2[3]}')

print('WORD SIZE: 7\nDATA PER WORD: 4\nPARITY MODE: ODD')
random.seed(43)
for codeword in codewords:
    if random.choice([True, False]):
        bit_to_flip = random.randint(0, 6)
        codeword = codeword[:bit_to_flip] + str(1 - int(codeword[bit_to_flip])) + codeword[bit_to_flip + 1:]
    print(codeword)


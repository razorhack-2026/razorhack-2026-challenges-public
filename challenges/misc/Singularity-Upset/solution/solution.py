codewords = []
for line in open('../dist/msg.txt').readlines():
    if line.startswith('0') or line.startswith('1'):
        codewords.append(line)

decoded = []
for codeword in codewords:
    bits = [int(bit) for bit in codeword.strip()]
    s1 = (bits[0] + bits[2] + bits[4] + bits[6]) % 2 == 0
    s2 = (bits[1] + bits[2] + bits[5] + bits[6]) % 2 == 0
    s3 = (bits[3] + bits[4] + bits[5] + bits[6]) % 2 == 0
    syndrome = s1 | (s2 << 1) | (s3 << 2)

    if syndrome:
        bits[syndrome - 1] = 1 - bits[syndrome - 1]

    decoded.append(int(''.join(str(bit) for bit in bits[2:3] + bits[4:]), 2))

for i in range(0, len(decoded), 2):
    print(chr((decoded[i] << 4) | decoded[i + 1]), end='')

print()

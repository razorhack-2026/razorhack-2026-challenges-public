constants_a = [101, 118, 101, 114, 121, 111, 110, 101, 32, 105, 115, 32, 97, 108, 119, 97, 121, 115, 32, 99, 111, 110, 110, 101, 99, 116, 101, 100] 
constants_b = [18, 30, 81, 6, 38, 27, 6, 86, 127, 1, 64, 67, 10, 51, 30, 84, 38, 4, 19, 1, 91, 29, 29, 86, 14, 22, 84, 29]

assert len(constants_a) == len(constants_b)

xor = [a ^ b for a, b in zip(constants_a, constants_b)]

flag = ''.join(chr(x) for x in xor)
print(f'flag{{{flag}}}')



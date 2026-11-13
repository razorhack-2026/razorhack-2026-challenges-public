from Crypto.Util import number
import yaml
import random

def evaluatePN(coefficients, x, p):
    result = 0
    for i in range(len(coefficients)):
        result += coefficients[i] * pow(x, i, p)
        result %= p
    return result

random.seed(42)

with open('../challenge.yml','r') as f:
    challenge = yaml.safe_load(f)
flag = challenge['flags'][0]

threshold = 5
totalShares = 9
# p = number.getPrime(256)
p = int('a105db01c4ca6f21c129479c720f425a4b20ec314b326ee6080079cbadcb4b71', 16)
coeffs = [int.from_bytes(flag.encode(), 'big')] + [random.randrange(0 if _ != threshold - 2 else 1, p) for _ in range(threshold - 1)]
shares = [(i, hex(evaluatePN(coeffs, i, p))) for i in range(1, totalShares + 1)]

print(f'Threshold: {threshold}')
print(f'Modulus: {hex(p)}')
for i, share in shares:
    print(f'{i}, {share}')

# print(f'polynomial: {coeffs[0]} + {coeffs[1]}*x + {coeffs[2]}*x^2 + {coeffs[3]}*x^3 + {coeffs[4]}*x^4')
# print(int.from_bytes(flag.encode(), 'big'))

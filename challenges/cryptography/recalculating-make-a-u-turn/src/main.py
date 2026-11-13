import yaml
import random

random.seed(42)
p = 257

def evaluatePN(coefficients, x):
    result = 0
    for i, coeff in enumerate(coefficients):
        result += (coeff * (x ** i)) % p
    return result % p

# Extract flag from challenge.yml
with open('../challenge.yml', 'r') as f:
    challenge_data = yaml.safe_load(f)
    flag = challenge_data.get('flags')[0]

flightPlan = open('flight_plan.txt', 'r').read().strip().replace('$$flag$$', flag)
planBlocks = [flightPlan[i:i+8] for i in range(0, len(flightPlan), 8)]

codewords = []
for block in planBlocks:
    if len(block) < 8:
        block = block.ljust(8, '\x00')  # Pad with null bytes if block is less than 8 characters
    codeword = [0] * 12
    terms = []
    for i, char in enumerate(block):
        terms.append(ord(char))
    for x in range(1, 13):
        y = evaluatePN(terms, x)
        codeword[x - 1] = f'{y:03x}'

    # Corrupt the codeword with some erasures
    numErasures = random.choices([0, 1, 2, 3, 4], weights=[5, 5, 10, 20, 60])[0]
    erasureIndices = random.sample(range(12), numErasures)
    for idx in erasureIndices:
        codeword[idx] = '???'  # Mark as erasure    
    codewords.append(''.join(codeword))

print('\n'.join(codewords))
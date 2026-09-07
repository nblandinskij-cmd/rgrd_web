import re

def extract_numbers(text):
    words = re.findall(r'\S+', text)
    result = []
    for word in words:
        if ':' in word:
            continue
        nums = re.findall(r'\d+(?:\.\d+)?', word)
        for n in nums:
            result.append(float(n))
    return result
# Sample 3: While Loops (Factorial and Summation)
n = 5
fact = 1
curr = 1

while curr <= n:
    fact = fact * curr
    curr = curr + 1

print("Factorial of 5:", fact)

total = 0
i = 1
while i <= 10:
    total = total + i
    i = i + 1

print("Sum 1..10:", total)

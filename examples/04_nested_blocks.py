# Sample 4: Nested Loops and Conditions
row = 1
even_count = 0
odd_count = 0

while row <= 3:
    col = 1
    while col <= 3:
        product = row * col
        if product % 2 == 0:
            even_count = even_count + 1
        else:
            odd_count = odd_count + 1
        col = col + 1
    row = row + 1

print("Even products:", even_count)
print("Odd products:", odd_count)

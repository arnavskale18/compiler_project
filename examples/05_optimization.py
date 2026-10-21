# Sample 5: Optimization Benchmark (Constant Folding & DCE)
# In this program, expressions involving literals are folded at compile time
a = 100 + 200 * 3
b = 50 // 2
is_always_true = 10 > 5 and 20 == 20

# Constant conditional branch simplification:
if 10 > 5:
    res = a + b
else:
    res = 0

print("Optimized folded result:", res)
print("Always true condition:", is_always_true)

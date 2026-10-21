# Sample 2: Conditionals (if / elif / else)
score = 85

if score >= 90:
    grade = "A"
    print("Excellent work!")
elif score >= 80:
    grade = "B"
    print("Good job!")
elif score >= 70:
    grade = "C"
    print("Satisfactory")
else:
    grade = "F"
    print("Needs improvement")

print("Final Grade:", grade)
is_pass = score >= 60 and not (score < 50)
print("Passed:", is_pass)


a = 1*1
b = 1.0000000001*1

print(a == b)  # False
print(abs(a - b) < 1e-9)  # True
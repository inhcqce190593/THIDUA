def auto_assign(classes, weeks):
    assigned = []
    for i in range(weeks):
        assigned.append(classes[i % len(classes)])
    return assigned

# Danh sách lớp theo khối
khoi_10 = [f"10A{i}" for i in range(1, 21)]
khoi_11 = [f"11A{i}" for i in range(1, 20)]
khoi_12 = [f"12A{i}" for i in range(1, 18)]

weeks = 34

print("Phân công khối 10:")
print(auto_assign(khoi_10, weeks))

print("Phân công khối 11:")
print(auto_assign(khoi_11, weeks))

print("Phân công khối 12:")
print(auto_assign(khoi_12, weeks))

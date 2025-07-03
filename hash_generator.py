from werkzeug.security import generate_password_hash

doctors = {
    "Dr. Richard James": "rahasia123",
    "Dr. Emily Larson": "rahasia124",
    "Dr. Sarah Patel": "rahasia125",
    "Dr. Christopher Lee": "rahasia126",
    "Dr. Jennifer Garcia": "rahasia127",
    "Dr. Alex Morgan": "rahasia128"
}

for name, password in doctors.items():
    hashed = generate_password_hash(password)
    print(f"{name} | Password: {password} | Hashed: {hashed}")

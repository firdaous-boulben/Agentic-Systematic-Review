from agents.protocol_agent import generate_protocol
import json

topic = "Artificial Intelligence for Cybersecurity Threat Detection"

# Generate protocol
protocol = generate_protocol(topic)

# Display results
print("\n========== REVIEW PROTOCOL ==========\n")

print(json.dumps(
    protocol,
    indent=4,
    ensure_ascii=False
))
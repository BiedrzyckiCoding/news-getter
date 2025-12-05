from transformers import pipeline

def analyze_tone(text):
    # Load a zero-shot classification pipeline
    # "facebook/bart-large-mnli" is excellent for understanding relationships between labels and text
    classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

    # Define the potential tones you want to measure
    candidate_labels = ["Professional", "Sarcastic", "Urgent", "Sympathetic", "Angry", "Objective", "Humorous", "Critical", "Optimistic", "Pessimistic"]

    # Run the classification
    result = classifier(text, candidate_labels)

    return result

# Your 300-word article string
article = """
I cannot believe we are still discussing this issue. It is absolutely fantastic that 
we have wasted three weeks on a problem that could have been solved by a single email. 
Truly, top-tier management at work here.
"""

analysis = analyze_tone(article)

# Pretty print the results
print(f"Top Tone: {analysis['labels'][0]}")
print(f"Confidence: {analysis['scores'][0]:.4f}")

print("\nFull Breakdown:")
for label, score in zip(analysis['labels'], analysis['scores']):
    print(f"- {label}: {score:.4f}")
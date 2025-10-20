import re
import json
import os

def load_json_answers(json_file):
    """Load answers from the JSON file."""
    with open(json_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def find_reference_question(json_answers):
    """Find the reference question about marginal benefit."""
    for item in json_answers:
        if "marginal benefit John gets from eating" in item['question']:
            return item
    return None

def main():
    # File paths
    answers_file = os.path.join(os.path.dirname(__file__), "ktvm111_questions_output.json")
    output_file = os.path.join(os.path.dirname(__file__), "exam_111.json")
    
    # Load answers from JSON
    print(f"Loading answers from {answers_file}...")
    json_answers = load_json_answers(answers_file)
    print(f"Loaded {len(json_answers)} questions from JSON")
    
    # Find the reference question
    reference_question = find_reference_question(json_answers)
    if reference_question:
        print(f"Found reference question: {reference_question['question'][:50]}...")
        print(f"Reference answer: {reference_question['metadata']['answer']}")
        
        # Create output with just the reference question
        output_data = [reference_question]
        
        # Write output to JSON file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=4, ensure_ascii=False)
        
        print(f"Wrote reference question to {output_file}")
        print(f"\nReference question used for answer: {reference_question['question'][:100]}...")
    else:
        print("Could not find reference question about marginal benefit")

if __name__ == "__main__":
    main()

import pandas as pd
import json
import re
import os
import sys

def split_student_name(student_name):
    # Updated to handle format "Name-StudentNumber"
    match = re.search(r'(.*?)-(\d+)', student_name)
    if match:
        return match.group(1).strip(), match.group(2)
    return student_name, ''  # Return original name and empty student number if pattern doesn't match

def process_data(input_file, output_file):
    try:
        # Read JSON file
        with open(input_file, 'r') as f:
            data = json.load(f)
            
        # Handle both single object and list of objects
        if not isinstance(data, list):
            data = [data]
            
        # Extract relevant information
        processed_data = []
        for entry in data:
            processed_data.append({
                'student_name': entry['student_name'],
                'score.percentage': entry['score']['percentage']
            })
            
        # Convert to DataFrame
        df = pd.DataFrame(processed_data)
        
        # Split student_name into name and student_number
        split_names = df['student_name'].apply(split_student_name)
        df['name'] = split_names.apply(lambda x: x[0])
        df['student_number'] = split_names.apply(lambda x: x[1])
        
        # Convert student_number to integer for proper numerical sorting
        df['student_number'] = pd.to_numeric(df['student_number'])
        
        # Select and reorder columns
        result_df = df[['name', 'student_number', 'score.percentage']]
        
        # Sort by student_number numerically
        result_df = result_df.sort_values('student_number', ascending=True)
        
        # Save to CSV
        result_df.to_csv(output_file, index=False)
        print(f"Processed data saved to {output_file}")
        
    except Exception as e:
        print(f"Error processing file: {str(e)}")

if __name__ == "__main__":
    # Get input file from environment variable or command line argument
    input_file = os.environ.get("INPUT_FILE")
    
    # If not set via environment variable, check command line arguments
    if not input_file and len(sys.argv) > 1:
        input_file = sys.argv[1]
    
    # Fallback to default if neither is provided
    if not input_file:
        input_file = "exam_results_20250408_074816.json"
        print(f"No input file specified. Using default: {input_file}")
    
    output_file = input_file.replace('.json', '.csv')
    print(f"Processing file: {input_file}")
    process_data(input_file, output_file) 
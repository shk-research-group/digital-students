#!/usr/bin/env python3
import json
import os
import glob
import pandas as pd
import argparse
from pathlib import Path

def load_results_files(pattern=None):
    """Load all results files matching the pattern."""
    current_dir = Path(__file__).parent
    
    if pattern:
        result_files = list(current_dir.glob(f"exam_results*{pattern}*.json"))
    else:
        result_files = list(current_dir.glob("exam_results*.json"))
    
    if not result_files:
        print(f"No result files found matching pattern: {pattern if pattern else '*'}")
        return {}
    
    results_by_file = {}
    
    for file_path in sorted(result_files):
        try:
            with open(file_path, 'r') as f:
                results = json.load(f)
                
            # Extract exam name from the first result
            if results and 'exam_name' in results[0]:
                exam_name = results[0]['exam_name']
                timestamp = file_path.stem.split('_')[-1]
                key = f"{exam_name}_{timestamp}"
            else:
                key = file_path.stem
                
            results_by_file[key] = results
            print(f"Loaded {len(results)} results from {file_path.name}")
            
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
    
    return results_by_file

def analyze_exam_results(results_by_file):
    """Analyze results and generate summary statistics."""
    summary_data = []
    
    for file_key, results in results_by_file.items():
        exam_name = results[0]['exam_name'] if results and 'exam_name' in results[0] else "Unknown"
        total_students = len(results)
        
        # Calculate statistics
        scores = [r.get('score', {}).get('percentage', 0) for r in results if r.get('score')]
        times = [r.get('time_taken', {}).get('minutes', 0) for r in results if r.get('time_taken')]
        
        # Count errors
        error_count = sum(1 for r in results if r.get('status') == 'error')
        
        if scores:
            avg_score = sum(scores) / len(scores)
            max_score = max(scores)
            min_score = min(scores)
            pass_rate = sum(1 for s in scores if s >= 50) / len(scores) * 100
        else:
            avg_score = max_score = min_score = pass_rate = 0
            
        if times:
            avg_time = sum(times) / len(times)
            max_time = max(times)
            min_time = min(times)
        else:
            avg_time = max_time = min_time = 0
        
        # Add to summary data
        summary_data.append({
            'File': file_key,
            'Exam': exam_name,
            'Students': total_students,
            'Errors': error_count,
            'Avg Score': round(avg_score, 1),
            'Max Score': round(max_score, 1),
            'Min Score': round(min_score, 1),
            'Pass Rate %': round(pass_rate, 1),
            'Avg Time (min)': round(avg_time, 1),
            'Max Time (min)': round(max_time, 1),
            'Min Time (min)': round(min_time, 1)
        })
    
    return summary_data

def create_detailed_report(results_by_file, output_file=None):
    """Create a detailed report of student performance across exams."""
    # Extract all unique student names
    all_students = set()
    for results in results_by_file.values():
        for result in results:
            if 'student_name' in result:
                all_students.add(result['student_name'])
    
    # Create a dictionary to hold score data per student per exam
    student_scores = {student: {} for student in all_students}
    
    # Fill in the scores
    for file_key, results in results_by_file.items():
        for result in results:
            student = result.get('student_name')
            if student and student in student_scores:
                score = result.get('score', {}).get('percentage', 0)
                student_scores[student][file_key] = score
    
    # Convert to a DataFrame for easier analysis
    df = pd.DataFrame.from_dict(student_scores, orient='index')
    
    # Sort by student name
    df = df.sort_index()
    
    # Add summary columns
    if not df.empty:
        df['Average'] = df.mean(axis=1, numeric_only=True)
        df['Min'] = df.min(axis=1, numeric_only=True)
        df['Max'] = df.max(axis=1, numeric_only=True)
    
    # Save to CSV if output file specified
    if output_file:
        df.to_csv(output_file)
        print(f"Detailed report saved to {output_file}")
    
    return df

def compare_answers(results_by_file):
    """Compare answer patterns across different exams."""
    wrong_answer_analysis = {}
    
    for file_key, results in results_by_file.items():
        wrong_answers_count = {}
        
        for result in results:
            for wrong_q in result.get('wrong_answers', []):
                if wrong_q not in wrong_answers_count:
                    wrong_answers_count[wrong_q] = 0
                wrong_answers_count[wrong_q] += 1
        
        # Sort by frequency
        sorted_wrong = sorted(wrong_answers_count.items(), key=lambda x: x[1], reverse=True)
        
        # Calculate percentage
        total_students = len(results)
        wrong_answer_analysis[file_key] = [
            {
                'question': q, 
                'wrong_count': count, 
                'wrong_percent': round(count/total_students*100, 1)
            } 
            for q, count in sorted_wrong if total_students > 0
        ]
    
    return wrong_answer_analysis

def main():
    parser = argparse.ArgumentParser(description='Analyze exam results.')
    parser.add_argument('--pattern', help='Pattern to match result files (e.g., "ktqt" or "batch")')
    parser.add_argument('--output', help='Output file for detailed report (CSV)')
    args = parser.parse_args()
    
    # Load results files
    results_by_file = load_results_files(args.pattern)
    
    if not results_by_file:
        print("No results to analyze.")
        return
    
    # Analyze and display summary
    summary_data = analyze_exam_results(results_by_file)
    
    if summary_data:
        # Convert to DataFrame for nicer display
        summary_df = pd.DataFrame(summary_data)
        print("\n===== SUMMARY STATISTICS =====")
        print(summary_df.to_string(index=False))
    
    # Create detailed report
    output_file = args.output if args.output else None
    detailed_df = create_detailed_report(results_by_file, output_file)
    
    # Show wrong answer analysis
    wrong_answers = compare_answers(results_by_file)
    
    print("\n===== MOST COMMON WRONG ANSWERS =====")
    for file_key, wrong_data in wrong_answers.items():
        if wrong_data:
            print(f"\n{file_key} - Top 5 most difficult questions:")
            for i, item in enumerate(wrong_data[:5]):
                print(f"  {i+1}. Question {item['question']}: Wrong in {item['wrong_count']} cases ({item['wrong_percent']}%)")

if __name__ == "__main__":
    main() 
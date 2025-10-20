import json
from collections import Counter
from typing import List, Dict
import statistics

def load_exam_data(filename: str) -> List[Dict]:
    """Load exam data from JSON file."""
    with open(filename, 'r') as f:
        return json.load(f)

def analyze_wrong_answers(exam_data: List[Dict]) -> Dict:
    """Analyze wrong answers across all exams."""
    # Count wrong answers for each question
    wrong_answer_counts = Counter()
    total_students = len(exam_data)
    
    for exam in exam_data:
        wrong_answers = exam.get('wrong_answers', [])
        wrong_answer_counts.update(wrong_answers)
    
    # Convert to dictionary with percentages
    wrong_answer_stats = {
        question: {
            'count': count,
            'percentage': (count / total_students) * 100
        }
        for question, count in wrong_answer_counts.items()
    }
    
    return wrong_answer_stats

def get_most_missed_questions(wrong_answer_stats: Dict, top_n: int = 10) -> List[tuple]:
    """Get the most frequently missed questions."""
    sorted_questions = sorted(
        wrong_answer_stats.items(),
        key=lambda x: x[1]['count'],
        reverse=True
    )
    return sorted_questions[:top_n]

def calculate_statistics(exam_data: List[Dict]) -> Dict:
    """Calculate general statistics about the exams."""
    scores = [exam['score']['percentage'] for exam in exam_data]
    wrong_counts = [len(exam['wrong_answers']) for exam in exam_data]
    
    return {
        'average_score': statistics.mean(scores),
        'median_score': statistics.median(scores),
        'score_std_dev': statistics.stdev(scores) if len(scores) > 1 else 0,
        'avg_wrong_answers': statistics.mean(wrong_counts),
        'total_students': len(exam_data)
    }

def main():
    # Load the exam data
    try:
        exam_data = load_exam_data('exam_results_20250408_074816.json')
    except FileNotFoundError:
        print("Error: exam_results.json file not found!")
        return
    except json.JSONDecodeError:
        print("Error: Invalid JSON format in exam_results.json!")
        return

    # Analyze wrong answers
    wrong_answer_stats = analyze_wrong_answers(exam_data)
    
    # Get most missed questions
    most_missed = get_most_missed_questions(wrong_answer_stats)
    
    # Calculate general statistics
    stats = calculate_statistics(exam_data)
    
    # Print results
    print("\n=== Most Frequently Missed Questions ===")
    print("Question | Times Missed | Percentage of Students")
    print("-" * 45)
    for question, data in most_missed:
        print(f"   {question:2d}   |     {data['count']:3d}      |     {data['percentage']:6.2f}%")
    
    print("\n=== General Statistics ===")
    print(f"Total number of students: {stats['total_students']}")
    print(f"Average score: {stats['average_score']:.2f}%")
    print(f"Median score: {stats['median_score']:.2f}%")
    print(f"Score standard deviation: {stats['score_std_dev']:.2f}%")
    print(f"Average number of wrong answers: {stats['avg_wrong_answers']:.2f}")

if __name__ == "__main__":
    main() 
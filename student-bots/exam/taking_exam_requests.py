import json
import requests
import logging
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
import concurrent.futures

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExamTakerRequests:
    ROOT_PROMPT = "DoingExamNoVARK"
    
    def __init__(self, endpoint_url: str, student_name: str = "Stuart", exam_name: str = "General Knowledge"):
        """Initialize the ExamTaker with the endpoint URL."""
        self.endpoint_url = endpoint_url
        self.access_token = os.getenv('ACCESS_TOKEN')
        if not self.access_token:
            raise ValueError("ACCESS_TOKEN environment variable is not set")
        self.questions_data = None
        self.student_name = student_name
        self.exam_name = exam_name
        self.answers = []
        self.wrong_answers = []

    def load_questions(self, json_path: str) -> None:
        """Load questions from a JSON file."""
        try:
            with open(json_path, 'r') as f:
                self.questions_data = json.load(f)
            logger.info(f"Successfully loaded questions from {json_path}")
        except FileNotFoundError:
            logger.error(f"Questions file not found at {json_path}")
            raise
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON format in {json_path}")
            raise

    def format_question(self, question: Dict[str, Any], position: int) -> str:
        """Format the question with its position and options."""
        # Get position from metadata
        question_position = question.get('metadata', {}).get('question_position', position)
        
        # Add student bot prefix
        question_text = f"@student-bot #{self.student_name}\n\n"
        question_text += f"There are 50 questions. This is question {question_position}:\n\n{question.get('question', '')}"
        
        return question_text.strip()

    def send_question(self, question: Dict[str, Any], position: int) -> Optional[Dict[str, Any]]:
        """Send a single question with its image to the endpoint."""
        try:
            # Prepare the files dictionary for image upload
            files = {}
            if 'image_path' in question:
                image_path = Path(question['image_path'])
                if image_path.exists():
                    files['image'] = (image_path.name, open(image_path, 'rb'))
                else:
                    logger.warning(f"Image not found at {image_path}")

            # Format question
            formatted_question = self.format_question(question, position)

            # Prepare the question data
            data = {
                'root_prompt': self.ROOT_PROMPT,
                'text': formatted_question,
                'metadata': {
                    **question.get('metadata', {}),
                    'position': position,
                    'total_options': len(question.get('options', [])),
                    'exam_name': self.exam_name
                }
            }

            # Prepare headers
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Basic {self.access_token}'
            }

            # Send the request
            response = requests.post(
                self.endpoint_url,
                files=files,
                json=data,
                headers=headers
            )
            response.raise_for_status()
            
            # Close any opened files
            for file in files.values():
                file[1].close()

            return response.json()

        except requests.RequestException as e:
            logger.error(f"Failed to send question: {str(e)}")
            return None
        finally:
            # Ensure files are closed even if an error occurs
            for file in files.values():
                if hasattr(file, 'close'):
                    file[1].close()

    def format_all_questions(self) -> str:
        """Format all questions into a single text with the student prefix."""
        if not self.questions_data:
            raise ValueError("Questions not loaded. Call load_questions() first.")
        
        questions = self.questions_data.get('questions', [])
        
        # Add student bot prefix
        formatted_text = f"@student-bot #{self.student_name}\n\n"
        formatted_text += f"There are {len(questions)} questions. Please answer each with the letter of the correct option only.\n\n"
        
        for i, question in enumerate(questions):
            position = question.get('metadata', {}).get('question_position', i+1)
            formatted_text += f"Question {position}:\n{question.get('question', '')}\n\n"
        
        return formatted_text.strip()

    def send_all_questions(self) -> Optional[Dict[str, Any]]:
        """Send all questions in a single request to the endpoint."""
        try:
            # Format all questions together
            formatted_questions = self.format_all_questions()

            # Prepare the question data
            data = {
                'root_prompt': self.ROOT_PROMPT,
                'text': formatted_questions,
                'metadata': {
                    'exam_name': self.exam_name,
                    'total_questions': len(self.questions_data.get('questions', [])),
                    'student_name': self.student_name
                }
            }

            # Prepare headers
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Basic {self.access_token}'
            }

            # Send the request
            logger.info(f"Sending all questions for student {self.student_name}...")
            response = requests.post(
                self.endpoint_url,
                json=data,
                headers=headers
            )
            response.raise_for_status()

            return response.json()

        except requests.RequestException as e:
            logger.error(f"Failed to send questions: {str(e)}")
            return None

    def parse_answers(self, response_text: str) -> List[str]:
        """Parse the response text to extract letter answers."""
        # First check if the response is a comma-separated list of answers
        import re
        
        # Clean the response text of any leading/trailing whitespace
        clean_text = response_text.strip()
        
        # Try to match a comma-separated list of single letters (A-E)
        csv_pattern = re.compile(r'^([A-E],\s*)+[A-E]$')
        if csv_pattern.match(clean_text):
            # Split by comma and clean each answer
            answers = [ans.strip() for ans in clean_text.split(',')]
            logger.info(f"Parsed {len(answers)} answers from comma-separated list")
            return answers
        
        # Try to match a list of single letters with no commas (like "ABCDE")
        if all(c in 'ABCDE' for c in clean_text) and len(clean_text) > 0:
            answers = list(clean_text)
            logger.info(f"Parsed {len(answers)} answers from continuous string of letters")
            return answers
        
        # Try to extract answers in format like "1. A", "2. B", etc.
        answer_pattern = re.compile(r'(?:^|\n)(\d+)[.:)] *([A-E])', re.MULTILINE)
        matches = answer_pattern.findall(response_text)
        
        if matches:
            # Create a dictionary to hold question number -> answer
            answer_dict = {int(q): a for q, a in matches}
            
            # Get all questions from the original data
            questions = self.questions_data.get('questions', [])
            answers = []
            
            for i, question in enumerate(questions):
                position = question.get('metadata', {}).get('question_position', i+1)
                if position in answer_dict:
                    answers.append(answer_dict[position])
                else:
                    # If we can't find an answer for this position, add None
                    answers.append(None)
            
            logger.info(f"Parsed {len(answers)} answers from numbered format")
            return answers
        
        # Fallback: try to extract answers from each line
        lines = response_text.strip().split('\n')
        answers = []
        
        for line in lines:
            line = line.strip()
            if line and len(line) >= 1 and line[0] in 'ABCDE':
                answers.append(line[0])
        
        if answers:
            logger.info(f"Parsed {len(answers)} answers from line-by-line format")
            return answers
            
        # If nothing worked, log a warning and return empty list
        logger.warning(f"Could not parse answers from response: {response_text[:100]}...")
        return []

    def take_exam(self) -> dict:
        """Process all questions in a single request."""
        if not self.questions_data:
            raise ValueError("Questions not loaded. Call load_questions() first.")
            
        start_time = time.time()
        questions = self.questions_data.get('questions', [])
        total_questions = len(questions)
        correct_answers = 0
        
        # Send all questions at once
        result = self.send_all_questions()
        
        if result:
            response_text = result[0].get('json', {}).get('text', '')
            logger.info(f"Received response for student {self.student_name}")
            
            # Parse the answers from the response
            parsed_answers = self.parse_answers(response_text)
            
            # Match answers with expected answers
            for i, question in enumerate(questions):
                position = question.get('metadata', {}).get('question_position', i+1)
                expected_answer = question.get('metadata', {}).get('answer')
                
                # Get the actual answer if available in our parsed answers
                actual_answer = parsed_answers[i] if i < len(parsed_answers) else None
                
                self.answers.append({
                    "position": position,
                    "expected": expected_answer,
                    "actual": actual_answer
                })
                
                if actual_answer and expected_answer and actual_answer == expected_answer:
                    correct_answers += 1
                    logger.info(f"Student {self.student_name} - Question {position}: Correct! ({actual_answer})")
                else:
                    self.wrong_answers.append(position)
                    if not actual_answer:
                        logger.warning(f"Student {self.student_name} - Question {position}: No answer provided. Expected {expected_answer}")
                    else:
                        logger.warning(f"Student {self.student_name} - Question {position}: Wrong! Expected {expected_answer}, got {actual_answer}")
        else:
            logger.error(f"No response received for student {self.student_name}")
            # Mark all questions as wrong if no response
            for i, question in enumerate(questions):
                position = question.get('metadata', {}).get('question_position', i+1)
                self.wrong_answers.append(position)
        
        total_time = time.time() - start_time
        score_percentage = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
        
        result = {
            "total_questions": total_questions,
            "correct_answers": correct_answers,
            "score_percentage": round(score_percentage, 1),
            "total_time_seconds": round(total_time, 1),
            "total_time_minutes": round(total_time/60, 1)
        }
        
        logger.info(f"\n=== Exam Results - Student {self.student_name} ===")
        logger.info(f"Score: {correct_answers}/{total_questions} ({score_percentage:.1f}%)")
        logger.info(f"Time taken: {total_time:.1f} seconds ({total_time/60:.1f} minutes)")
        if self.wrong_answers:
            logger.info(f"Wrong answers on questions: {', '.join(map(str, sorted(self.wrong_answers)))}")
            
        return result

def process_student(endpoint_url: str, student_name: str, exam_name: str, questions_file: str) -> dict:
    result = {
        "student_name": student_name,
        "exam_name": exam_name,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "completed",
        "error": None,
        "answers": [],
        "wrong_answers": [],
        "score": None,
        "time_taken": None
    }
    
    exam_taker = ExamTakerRequests(endpoint_url, student_name, exam_name)
    try:
        # Load questions from the JSON file in the same directory
        current_dir = Path(__file__).parent
        questions_path = current_dir / questions_file
        exam_taker.load_questions(str(questions_path))
        
        # Process all questions and get results
        exam_results = exam_taker.take_exam()
        
        # Capture results
        result["answers"] = exam_taker.answers
        result["wrong_answers"] = sorted(exam_taker.wrong_answers) if exam_taker.wrong_answers else []
        result["score"] = {
            "total_questions": exam_results["total_questions"],
            "correct_answers": exam_results["correct_answers"],
            "percentage": exam_results["score_percentage"]
        }
        result["time_taken"] = {
            "seconds": exam_results["total_time_seconds"],
            "minutes": exam_results["total_time_minutes"]
        }
        
    except Exception as e:
        error_msg = f"Error during exam taking process for {student_name}: {str(e)}"
        logger.error(error_msg)
        result["status"] = "error"
        result["error"] = error_msg
    
    return result

def save_results(result: dict, run_timestamp: str):
    """Save exam results to a JSON file with proper formatting."""
    # Create filename with timestamp
    filename = f"exam_results_requests_{result['exam_name'].replace(' ', '_')}_{run_timestamp}.json"
    current_dir = Path(__file__).parent
    output_path = current_dir / filename
    
    # Load existing results if file exists
    existing_results = []
    if output_path.exists():
        with open(output_path, 'r') as f:
            existing_results = json.load(f)
    
    # Add new result
    existing_results.append(result)
    
    # Sort results by student name for better readability
    sorted_results = sorted(existing_results, key=lambda x: x["student_name"])
    
    with open(output_path, 'w') as f:
        json.dump(sorted_results, f, indent=2)
    
    logger.info(f"Results updated in {output_path}")

def main():
    # Default Configuration settings
    config = {
        # API endpoint configuration
        "endpoint_url": os.getenv("EXAM_ENDPOINT_URL", "https://n8n.khiemfle.com/webhook/139644a9-2fd6-4c59-ba4a-ecf406da70bb"),
        "root_prompt": os.getenv("EXAM_ROOT_PROMPT", "DoingExamNoVARKAllTests"),
        
        # Exam configuration
        "exam_name": os.getenv("EXAM_NAME", "ktqt_gemini_2_v1.1"),
        "questions_file": os.getenv("EXAM_QUESTIONS_FILE", "exam_ktqt.json"),
        
        # Execution configuration
        "max_workers": int(os.getenv("EXAM_MAX_WORKERS", "1")),
        
        # Student list - can be overridden with EXAM_STUDENTS env var (comma-separated)
        "student_names": os.getenv("EXAM_STUDENTS", "").split(",") if os.getenv("EXAM_STUDENTS") else 
        [
            # Full list of students
            "Ethan-15","Olivia-19","James-23","Sophia-27","Emily-31","Benjamin-35","Ava-39","Daniel-43",
            "William-47","Matthew-51","Charlotte-55","Isabella-59","Noah-63","Alexander-13","Henry-17",
            "Jack-21","Amelia-25","Lucas-29","Harper-33","Lily-37","Grace-41","Nathan-45","Jacob-49",
            "Ella-53","Scarlett-57","Violet-61","Samuel-16","Hazel-20","Madison-24","Oliver-28",
            "Riley-32","Natalie-36","Connor-40","Elijah-44","Ryan-48","Zachary-52","Zoe-56",
            "Hannah-60","Evelyn-14","Layla-18","Caleb-22","Dylan-26","Aria-30","Nora-34","Audrey-38",
            "Stella-42","Leo-46","Owen-50","Penelope-54","Ruby-58","Bella-62",
            "Brown-64", "Moore-65", "Lewis-66", "Rodriguez-67", "Gonzalez-68",
            "Garcia-69", "Anderson-70", "Martin-71", "Perez-72", "Young-73",
            "Ramirez-74", "Hill-75", "Nguyen-76", "Taylor-77", "Scott-78",
            "Thomas-79", "Ramirez-80", "Allen-81", "Davis-82", "Harris-83",
            "Thompson-84", "Lewis-85", "Lee-86", "Sanchez-87", "Wright-88",
            "Lopez-89", "Hill-90", "Martin-91", "Harris-92", "Taylor-93",
            "Johnson-94", "Williams-95", "Moore-96", "Thompson-97", "Scott-98",
            "Ramirez-99", "Thompson-100", "Walker-101", "Hernandez-102", "Nguyen-103",
            "Wright-104", "Johnson-105", "Flores-106", "Miller-107", "Johnson-108",
            "Hernandez-109", "Allen-110"
        ]
        # [
        #     # Default list of students
        #     "Ethan-15"
        # ]
        # [
        #     # Default list of students
        #     "Ethan-15", "Olivia-19", "James-23", "Sophia-27", "Emily-31"
        # ]
    }
    
    # Filter out empty student names (in case of trailing comma in env var)
    config["student_names"] = [name.strip() for name in config["student_names"] if name.strip()]
    
    # Log configuration for debugging
    logger.info("Starting with configuration:")
    for key, value in config.items():
        if key == "student_names":
            logger.info(f"  {key}: {len(value)} students")
        else:
            logger.info(f"  {key}: {value}")
    
    # Override ExamTaker.ROOT_PROMPT with config value
    ExamTakerRequests.ROOT_PROMPT = config["root_prompt"]
    
    # Generate a timestamp for this run in a readable format
    run_timestamp = time.strftime("%Y%m%d_%H%M%S")
    logger.info(f"\n=== Starting new exam run '{config['exam_name']}' at {run_timestamp} ===\n")
    
    # Determine max workers (limit by configuration and number of students)
    max_workers = min(len(config["student_names"]), config["max_workers"])
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Create a list of futures
        future_to_student = {
            executor.submit(
                process_student, 
                config["endpoint_url"], 
                student_name, 
                config["exam_name"],
                config["questions_file"]
            ): student_name
            for student_name in config["student_names"]
        }
        
        # Save results as they complete
        for future in concurrent.futures.as_completed(future_to_student):
            student_name = future_to_student[future]
            try:
                result = future.result()
                logger.info(f"Completed exam for {student_name}")
                # Save result immediately after student completes
                save_results(result, run_timestamp)
            except Exception as e:
                logger.error(f"Unexpected error for {student_name}: {str(e)}")
                error_result = {
                    "student_name": student_name,
                    "exam_name": config["exam_name"],
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "error",
                    "error": str(e),
                    "answers": [],
                    "wrong_answers": []
                }
                # Save error result immediately
                save_results(error_result, run_timestamp)
    
    logger.info(f"\n=== Completed exam run {run_timestamp} ===\n")

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
import os
import re
import json
import argparse
from typing import Dict, List, Any, Optional, Tuple
import PyPDF2

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Extracted text as a string
    """
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
    return text

def parse_questions(text: str) -> List[Dict[str, Any]]:
    """
    Parse the extracted text into question objects.
    
    Args:
        text: Extracted text from PDF
        
    Returns:
        List of question objects
    """
    # Regular expression to match question patterns
    # QN=1 (17143) The marginal benefit... followed by options a, b, c, d and an answer
    question_pattern = r'QN=(\d+)\s+\((\d+)\)(.*?)(?=QN=\d+\s+\(\d+\)|$)'
    
    questions = []
    question_id = 0
    
    for match in re.finditer(question_pattern, text, re.DOTALL):
        question_id += 1
        question_number = match.group(1)
        question_code = match.group(2)
        question_text = match.group(3).strip()
        
        # Find the answer (A, B, C, D) which is typically at the end of the right margin
        answer_match = re.search(r'([A-E])\s*$', question_text)
        answer = answer_match.group(1) if answer_match else ""
        
        # Remove the answer from the question text
        if answer_match:
            question_text = question_text[:answer_match.start()].strip()
        
        # Extract options
        options_pattern = r'([a-e])\.\s+(.*?)(?=[a-e]\.\s+|$)'
        options = re.findall(options_pattern, question_text, re.DOTALL)
        
        # Format options
        formatted_options = []
        for option_letter, option_text in options:
            formatted_options.append(f"{option_letter.upper()}. {option_text.strip()}")
        
        # Reconstruct question text with options
        question_stem = question_text.split('a.')[0].strip()
        full_question = question_stem + "\n" + "\n".join(formatted_options)
        
        question_obj = {
            "question": full_question,
            "metadata": {
                "question_id": f"q{question_id}",
                "question_position": question_id,
                "answer": answer
            }
        }
        
        questions.append(question_obj)
    
    return questions

def save_to_json(questions: List[Dict[str, Any]], output_path: str) -> None:
    """
    Save the parsed questions to a JSON file.
    
    Args:
        questions: List of question objects
        output_path: Path to save the JSON file
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(questions, f, indent=4, ensure_ascii=False)
    print(f"Saved {len(questions)} questions to {output_path}")

def main():
    parser = argparse.ArgumentParser(description='Extract test data from PDF files')
    parser.add_argument('pdf_path', help='Path to the PDF file')
    parser.add_argument('--output', '-o', default='questions.json', help='Output JSON file path')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.pdf_path):
        print(f"Error: PDF file not found at {args.pdf_path}")
        return
    
    print(f"Extracting text from {args.pdf_path}...")
    text = extract_text_from_pdf(args.pdf_path)
    
    print("Parsing questions...")
    questions = parse_questions(text)
    
    print(f"Found {len(questions)} questions")
    save_to_json(questions, args.output)

if __name__ == "__main__":
    main()
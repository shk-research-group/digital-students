import csv
import json

def convert_csv_to_json(csv_file, json_file):
    questions = []
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        csv_reader = csv.DictReader(f)
        for row in csv_reader:
            question_data = {
                "question": f"Câu {row['Câu']}. {row['Đề']}",
                "metadata": {
                    "question_id": f"q{row['Câu']}",
                    "question_position": int(row['Câu']),
                    "answer": row['Đáp án'].strip()[0] if row['Đáp án'].strip() else ""
                }
            }
            questions.append(question_data)
    
    output_data = {"questions": questions}
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    convert_csv_to_json("ECO121.csv", "exam_121.json") 
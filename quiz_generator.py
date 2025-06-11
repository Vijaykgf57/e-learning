import random
import re

def generate_quiz(text):
    # Basic stopwords list
    stop_words = {
        "the", "and", "is", "in", "to", "of", "a", "an", "for", "on", "with", "as", "by",
        "this", "that", "it", "from", "at", "are", "be", "was", "were", "or", "which", "has"
    }

    # Simple sentence splitter
    sentences = re.split(r'[.?!]\s*', text.strip())
    quiz = []

    for sentence in sentences:
        words = re.findall(r'\b[a-zA-Z]{3,}\b', sentence)
        keywords = [word for word in words if word.lower() not in stop_words]

        if len(keywords) >= 4:
            correct_answer = random.choice(keywords)
            wrong_answers = random.sample([w for w in keywords if w != correct_answer], 3)
            options = wrong_answers + [correct_answer]
            random.shuffle(options)

            blanked_sentence = re.sub(rf'\b{correct_answer}\b', "_____", sentence, flags=re.IGNORECASE)
            quiz.append({
                "question": blanked_sentence,
                "options": options,
                "answer": correct_answer
            })

        if len(quiz) >= 5:
            break

    return quiz

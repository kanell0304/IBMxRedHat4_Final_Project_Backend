

# LLM에서 받은 점수를 등급으로 변환
def score_to_grade(score:int)->str:
     
    if score>=90:
        return "S"
    elif score>=80:
        return "A"
    elif score>=70:
        return "B"
    elif score>=60:
        return "C"
    else:
        return "D"
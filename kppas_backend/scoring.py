GREEN_THRESHOLD = 0.9
AMBER_THRESHOLD = 0.6

PERCEPTION_GREEN_THRESHOLD = 4.0
PERCEPTION_AMBER_THRESHOLD = 2.5


def compute_score_and_status(value: float, target: float) -> tuple[float, str]:
    score = value / target if target else 0.0
    if score >= GREEN_THRESHOLD:
        status = "green"
    elif score >= AMBER_THRESHOLD:
        status = "amber"
    else:
        status = "red"
    return score, status


def compute_perception_status(average_rating: float) -> str:
    if average_rating >= PERCEPTION_GREEN_THRESHOLD:
        return "green"
    if average_rating >= PERCEPTION_AMBER_THRESHOLD:
        return "amber"
    return "red"

from sqlalchemy.orm import Session
from datetime import datetime
from models import Bird


def get_birds(db: Session):
    return db.query(Bird).all()


def add_birds(db: Session, bird_list: str):
    if not bird_list:
        return None

    current_time = datetime.now().timestamp()
    current_hour = datetime.now().hour

    # Reset existing birds
    active_birds = db.query(Bird).filter(Bird.currently_observed == True).all()
    for bird in active_birds:
        bird.currently_observed = False
    db.commit()

    for bird_name in bird_list:
        bird_name = bird_name.strip().lower()
        found_bird = db.query(Bird).filter(Bird.name == bird_name).first()

        if found_bird is None:
            new_bird = Bird(
                name=bird_name,
                last_seen=current_time,
                currently_observed=True,
                hourly_observations={current_hour: 1},
            )
            db.add(new_bird)
        else:
            if found_bird.hourly_observations is None:
                found_bird.hourly_observations = {}

            hour_key = str(current_hour)  # Use string keys consistently
            current_value = found_bird.hourly_observations.get(hour_key, 0)
            found_bird.hourly_observations[hour_key] = current_value + 1
            found_bird.last_seen = current_time
            found_bird.currently_observed = True

    db.commit()
    return f"Added: {bird_list}"

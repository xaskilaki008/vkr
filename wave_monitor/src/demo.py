import random
from datetime import datetime, timedelta

def wave_class_from_index(wave_index: float) -> int:
    """
    Очень простая шкала для прототипа.
    На защите можно объяснить: "класс — дискретизация индекса".
    """
    if wave_index < 0.8:
        return 1  # спокойно
    if wave_index < 1.6:
        return 2  # умеренно
    if wave_index < 2.5:
        return 3  # волнительно
    if wave_index < 3.5:
        return 4  # сильно
    return 5      # шторм

def generate_demo_point(prev_index: float | None = None) -> float:
    """
    Генератор "псевдо-волнения": плавно меняется, как реальное явление.
    """
    if prev_index is None:
        prev_index = random.uniform(0.3, 2.0)
    step = random.uniform(-0.25, 0.25)
    x = max(0.1, min(4.5, prev_index + step))
    return x

def demo_timeseries(minutes: int = 120):
    """
    Возвращает список точек за последние N минут.
    Каждая точка: (datetime, wave_index, wave_class)
    """
    now = datetime.now()
    points = []
    cur = None
    for i in range(minutes):
        ts = now - timedelta(minutes=(minutes - 1 - i))
        cur = generate_demo_point(cur)
        cls = wave_class_from_index(cur)
        points.append((ts, cur, cls))
    return points

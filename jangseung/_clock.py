"""UTC timestamps without importing ``datetime`` on every hook call.

``datetime`` costs about 0.5 ms to import, and the hook only needs the current
time as text for its records.
"""

import time


def utc_timestamp() -> str:
    """The same text as ``datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")``.

    Microseconds are cut, not rounded, and left out when zero, as ``datetime`` does.
    """

    seconds, nanoseconds = divmod(time.time_ns(), 1_000_000_000)
    microseconds = nanoseconds // 1000
    year, month, day, hour, minute, second = time.gmtime(seconds)[:6]
    # datetime folds a leap second into the second before it.
    text = f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:{min(second, 59):02d}"
    return f"{text}.{microseconds:06d}Z" if microseconds else f"{text}Z"

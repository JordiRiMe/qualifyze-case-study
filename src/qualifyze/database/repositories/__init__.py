from collections.abc import Iterator, Sequence


def _batched[T](
    records: Sequence[T],
    size: int,
) -> Iterator[Sequence[T]]:
    if size <= 0:
        raise ValueError("Batch size must be greater than zero")

    for start in range(0, len(records), size):
        yield records[start : start + size]

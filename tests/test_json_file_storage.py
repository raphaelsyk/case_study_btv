"""Round-trip tests for JsonFileStorage."""

import datetime
from pathlib import Path

from earnings_calls.models import CallIdentity, Chunk, DateRange, RawPage, Section, Speaker, Transcript, Turn
from earnings_calls.storage.json_file_storage import JsonFileStorage


def _transcript() -> Transcript:
    speaker = Speaker(name='Brian Moynihan', role='CEO')
    raw_pages = [RawPage(page_no=n, text=f'page {n}') for n in range(1, 5)]
    turn = Turn(speaker=speaker, text=[Chunk(page_no=1, text='hello world')], section=Section.MANAGEMENT_DISCUSSION)
    identity = CallIdentity(
        company='Bank of America',
        quarter_name='4Q25',
        call_date=datetime.date(2026, 1, 14),
        quarter_time_range=DateRange(start_date=datetime.date(2025, 10, 1), end_date=datetime.date(2025, 12, 31)),
    )
    return Transcript(identity=identity, participants=[speaker], turns=[turn], raw_pages=raw_pages)


def test_save_then_load_round_trips(tmp_path: Path) -> None:
    storage = JsonFileStorage(tmp_path)
    transcript = _transcript()

    saved_path = storage.save(transcript)
    loaded = storage.load('Bank of America', '4Q25')

    assert saved_path.exists()
    assert loaded == transcript


def test_save_slugifies_company_and_quarter_into_the_path(tmp_path: Path) -> None:
    storage = JsonFileStorage(tmp_path)

    saved_path = storage.save(_transcript())

    assert saved_path == tmp_path / 'bank_of_america' / '4q25.json'

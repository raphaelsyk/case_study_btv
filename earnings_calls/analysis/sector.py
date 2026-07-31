"""Maps a company to the industry-specific AI-analysis prompt variant it needs.

A fixed, hardcoded mapping for the four known companies in scope (see the "Analyzer
Module" decision in system_design/02_system_design.md) - not automatic sector
detection. A future mixed/hybrid company would need a new manual entry here.
"""

from enum import Enum


class Sector(str, Enum):
    """Which analysis-prompt variant a company's AI discussion should be read with."""

    BANK = 'bank'
    TECH = 'tech'


# Keyed on the storage slug (JsonFileStorage._slugify'd company name, e.g.
# "jpmorganchase"), not the free-text Transcript.identity.company field - that field is
# LLM-extracted per document and not guaranteed identical across a company's quarters
# (see the open company-identity-normalization note in 03_system_design_data_model.md).
_SECTOR_BY_COMPANY_SLUG = {
    'bank_of_america': Sector.BANK,
    'jpmorganchase': Sector.BANK,
    'microsoft': Sector.TECH,
    'nvidia_corp': Sector.TECH,
}


def sector_for_company(company_slug: str) -> Sector:
    """Looks up which analysis-prompt variant applies to a company's storage slug.

    Args:
        company_slug: The slugified company directory name used by JsonFileStorage.

    Returns:
        The Sector whose prompt variant should analyze this company's transcripts.

    Raises:
        KeyError: If `company_slug` isn't one of the known, mapped companies.
    """
    try:
        return _SECTOR_BY_COMPANY_SLUG[company_slug]
    except KeyError:
        raise KeyError(
            f'no sector mapping for company slug {company_slug!r} - add one to '
            f'_SECTOR_BY_COMPANY_SLUG in earnings_calls/analysis/sector.py'
        ) from None

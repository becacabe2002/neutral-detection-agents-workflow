import sqlite3
from typing import Optional
from src.config import settings
from src.utils.domain_parser import canonicalize_domain
from src.models.evidence import SourceProfile, BiasClassification, FactualReporting, CredibilityRating

class MBFCRegistry:
    def __init__(self, db_path: str = settings.MBFC_DB_PATH):
        self.db_path = db_path

    def lookup_domain(self, domain_or_url: str) -> Optional[SourceProfile]:
        domain = canonicalize_domain(domain_or_url)
        if not domain:
            return None
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sources WHERE domain = ?", (domain,))
            row = cursor.fetchone()

        if row:
            return SourceProfile(
                domain=row["domain"],
                bias_classification=BiasClassification(row["bias"]),
                factual_reporting=FactualReporting(row["factual_reporting"]),
                credibility_assessment=CredibilityRating(row["credibility"]),
                country=row["country"],
                media_type=row["media_type"],
                mbfc_url=row["mbfc_url"]
            )
        return None

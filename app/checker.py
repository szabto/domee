import whois
from datetime import datetime
from dataclasses import dataclass


@dataclass
class DomainResult:
    name: str
    available: bool
    expiry_date: str | None
    error: str | None = None


def check_domain(domain_name: str) -> DomainResult:
    """Check domain availability and expiry using python-whois."""
    try:
        w = whois.whois(domain_name)

        # If domain_name or status is None, domain is likely available
        if w.domain_name is None and w.status is None:
            return DomainResult(name=domain_name, available=True, expiry_date=None)

        # Parse expiry date
        expiry = None
        if w.expiration_date:
            exp = w.expiration_date
            if isinstance(exp, list):
                exp = exp[0]
            if isinstance(exp, datetime):
                expiry = exp.strftime("%Y-%m-%d")
            elif isinstance(exp, str):
                expiry = exp

        return DomainResult(
            name=domain_name, available=False, expiry_date=expiry
        )

    except whois.parser.PywhoisError:
        # Domain not found = available
        return DomainResult(name=domain_name, available=True, expiry_date=None)
    except Exception as e:
        return DomainResult(
            name=domain_name, available=False, expiry_date=None, error=str(e)
        )

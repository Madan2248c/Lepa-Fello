from schemas.input_models import VisitorSignalInput, CompanySeedInput
from schemas.internal_models import (
    NormalizedAccountInput,
    VisitorContext,
    CompanySeed,
)


def normalize_visitor_input(input_data: VisitorSignalInput) -> NormalizedAccountInput:
    """Convert visitor signal input into normalized internal format."""
    return NormalizedAccountInput(
        input_type="visitor_signal",
        input_id=input_data.visitor_id,
        raw_input=input_data.model_dump(),
        visitor_context=VisitorContext(
            ip_address=input_data.ip_address,
            pages_visited=input_data.pages_visited,
            time_on_site_seconds=input_data.time_on_site_seconds,
            visits_this_week=input_data.visits_this_week,
            referral_source=input_data.referral_source,
        ),
        company_seed=CompanySeed(),
    )


def normalize_company_input(input_data: CompanySeedInput) -> NormalizedAccountInput:
    """Convert company seed input into normalized internal format."""
    return NormalizedAccountInput(
        input_type="company_seed",
        input_id=input_data.company_name,
        raw_input=input_data.model_dump(),
        visitor_context=VisitorContext(),
        company_seed=CompanySeed(
            name=input_data.company_name,
            partial_domain=input_data.partial_domain,
        ),
    )

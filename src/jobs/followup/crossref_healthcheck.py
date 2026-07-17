from src.extract.crossref_extractor import check_crossref_health
from src.utils.console import progress as console_progress
from src.utils.console import success as console_success
from src.utils.console import warning as console_warning


def mask_mailto(user_agent: str) -> str:
    if "mailto:" not in user_agent:
        return user_agent

    prefix, _, suffix = user_agent.partition("mailto:")
    email, close, rest = suffix.partition(")")
    if "@" not in email:
        return user_agent

    name, _, domain = email.partition("@")
    masked_name = name[:2] + "***" if len(name) > 2 else "***"
    return f"{prefix}mailto:{masked_name}@{domain}{close}{rest}"


def main() -> None:
    health = check_crossref_health()
    status = health["response"].get("status")

    print(console_progress(f"Crossref base URL: {health['base_url']}"))
    print(
        console_progress(
            f"Crossref User-Agent: {mask_mailto(health['user_agent'])}"
        )
    )

    if health["mailto_configured"]:
        print(console_success("Crossref mailto is configured."))
    else:
        print(console_warning("Crossref mailto is not configured."))

    print(console_success(f"Crossref healthcheck status: {status}"))


if __name__ == "__main__":
    main()

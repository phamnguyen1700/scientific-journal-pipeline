from src.transform.openalex.works import clean_openalex_id


def transform_author_detail(raw: dict) -> dict:
    source_record_id = clean_openalex_id(raw.get("id"))
    summary_stats = raw.get("summary_stats") or {}

    return {
        "source_record_id": source_record_id,
        "source_record_url": raw.get("id"),
        "display_name": raw.get("display_name") or source_record_id,
        "full_name": raw.get("full_name"),
        "orcid": raw.get("orcid") or (raw.get("ids") or {}).get("orcid"),
        "works_count": raw.get("works_count"),
        "cited_by_count": raw.get("cited_by_count"),
        "h_index": summary_stats.get("h_index"),
        "i10_index": summary_stats.get("i10_index"),
        "two_year_mean_citedness": summary_stats.get("2yr_mean_citedness"),
        "raw_author_names": raw.get("raw_author_names"),
        "display_name_alternatives": raw.get("display_name_alternatives"),
        "affiliations": raw.get("affiliations"),
        "last_known_institutions": raw.get("last_known_institutions"),
        "topics": raw.get("topics"),
        "topic_share": raw.get("topic_share"),
        "x_concepts": raw.get("x_concepts"),
        "counts_by_year": raw.get("counts_by_year"),
        "works_api_url": raw.get("works_api_url"),
        "source_created_date": raw.get("created_date"),
        "source_updated_date": raw.get("updated_date"),
    }

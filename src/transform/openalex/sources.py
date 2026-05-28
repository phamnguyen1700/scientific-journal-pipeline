from src.transform.openalex.works import clean_openalex_id, transform_topic_node


def transform_source_detail(raw: dict) -> dict:
    summary_stats = raw.get("summary_stats") or {}

    return {
        "source_record_id": clean_openalex_id(raw.get("id")),
        "source_record_url": raw.get("id"),
        "display_name": raw.get("display_name"),
        "issn_l": raw.get("issn_l"),
        "issn": raw.get("issn") or [],
        "host_organization": raw.get("host_organization"),
        "host_organization_name": raw.get("host_organization_name"),
        "host_organization_lineage": raw.get("host_organization_lineage") or [],
        "type": raw.get("type"),
        "homepage_url": raw.get("homepage_url"),
        "country_code": raw.get("country_code"),
        "works_count": raw.get("works_count"),
        "oa_works_count": raw.get("oa_works_count"),
        "cited_by_count": raw.get("cited_by_count"),
        "h_index": summary_stats.get("h_index"),
        "i10_index": summary_stats.get("i10_index"),
        "two_year_mean_citedness": summary_stats.get("2yr_mean_citedness"),
        "is_oa": raw.get("is_oa"),
        "is_in_doaj": raw.get("is_in_doaj"),
        "is_core": raw.get("is_core"),
        "first_publication_year": raw.get("first_publication_year"),
        "last_publication_year": raw.get("last_publication_year"),
        "counts_by_year": raw.get("counts_by_year") or [],
        "topics": [
            topic
            for topic in (transform_topic_node(t) for t in raw.get("topics", []))
            if topic
        ],
        "topic_share": [
            topic
            for topic in (
                transform_source_topic_share(t) for t in raw.get("topic_share", [])
            )
            if topic
        ],
        "works_api_url": raw.get("works_api_url"),
        "source_created_date": raw.get("created_date"),
        "source_updated_date": raw.get("updated_date"),
    }


def transform_source_topic_share(topic: dict | None) -> dict | None:
    transformed = transform_topic_node(topic)

    if not transformed:
        return None

    transformed["topic_share"] = topic.get("value")
    return transformed

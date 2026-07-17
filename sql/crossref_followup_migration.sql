USE scientific_journal_tracking_db;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.schemas
    WHERE name = 'enrich'
)
BEGIN
    EXEC('CREATE SCHEMA enrich');
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM raw.api_sources
    WHERE source_name = 'Crossref'
)
BEGIN
    INSERT INTO raw.api_sources (source_name, base_url)
    VALUES ('Crossref', 'https://api.crossref.org');
END;
GO

IF OBJECT_ID('raw.crossref_works', 'U') IS NULL
BEGIN
    CREATE TABLE raw.crossref_works (
        raw_crossref_work_id UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),

        source_id UNIQUEIDENTIFIER NOT NULL,
        source_entity NVARCHAR(100) NOT NULL DEFAULT 'works',
        source_record_id NVARCHAR(500) NOT NULL,
        source_record_url NVARCHAR(1000) NULL,

        pipeline_run_id UNIQUEIDENTIFIER NOT NULL,

        raw_data NVARCHAR(MAX) NOT NULL,

        fetched_at DATETIME2 NOT NULL DEFAULT DATEADD(HOUR, 7, SYSUTCDATETIME()),
        last_seen_at DATETIME2 NULL,
        processed_status NVARCHAR(50) NOT NULL DEFAULT 'pending',
        process_error NVARCHAR(MAX) NULL,

        CONSTRAINT PK_raw_crossref_works
            PRIMARY KEY (raw_crossref_work_id),

        CONSTRAINT FK_raw_crossref_works_api_sources
            FOREIGN KEY (source_id)
            REFERENCES raw.api_sources(source_id),

        CONSTRAINT FK_raw_crossref_works_pipeline_runs
            FOREIGN KEY (pipeline_run_id)
            REFERENCES raw.pipeline_runs(run_id),

        CONSTRAINT UQ_raw_crossref_works_source_record
            UNIQUE (source_id, source_record_id),

        CONSTRAINT CK_raw_crossref_works_raw_data_json
            CHECK (ISJSON(raw_data) = 1),

        CONSTRAINT CK_raw_crossref_works_processed_status
            CHECK (processed_status IN ('pending', 'processed', 'failed'))
    );
END;
GO

IF OBJECT_ID('enrich.paper_source_checks', 'U') IS NULL
BEGIN
    CREATE TABLE enrich.paper_source_checks (
        check_id UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),

        paper_id UNIQUEIDENTIFIER NOT NULL,
        source_id UNIQUEIDENTIFIER NOT NULL,
        raw_crossref_work_id UNIQUEIDENTIFIER NULL,

        source_record_id NVARCHAR(500) NOT NULL,
        source_record_url NVARCHAR(1000) NULL,

        match_status NVARCHAR(50) NOT NULL,
        match_method NVARCHAR(100) NOT NULL,
        confidence_score DECIMAL(5, 4) NULL,

        summary_json NVARCHAR(MAX) NULL,
        error_message NVARCHAR(MAX) NULL,

        checked_at DATETIME2 NOT NULL DEFAULT DATEADD(HOUR, 7, SYSUTCDATETIME()),
        updated_at DATETIME2 NULL,

        CONSTRAINT PK_enrich_paper_source_checks
            PRIMARY KEY (check_id),

        CONSTRAINT FK_enrich_paper_source_checks_papers
            FOREIGN KEY (paper_id)
            REFERENCES core.papers(paper_id),

        CONSTRAINT FK_enrich_paper_source_checks_api_sources
            FOREIGN KEY (source_id)
            REFERENCES raw.api_sources(source_id),

        CONSTRAINT FK_enrich_paper_source_checks_raw_crossref_works
            FOREIGN KEY (raw_crossref_work_id)
            REFERENCES raw.crossref_works(raw_crossref_work_id),

        CONSTRAINT UQ_enrich_paper_source_checks_source_record
            UNIQUE (paper_id, source_id, source_record_id),

        CONSTRAINT CK_enrich_paper_source_checks_match_status
            CHECK (
                match_status IN (
                    'matched',
                    'not_found',
                    'not_crossref',
                    'conflict',
                    'error'
                )
            ),

        CONSTRAINT CK_enrich_paper_source_checks_confidence_score
            CHECK (
                confidence_score IS NULL
                OR confidence_score BETWEEN 0 AND 1
            ),

        CONSTRAINT CK_enrich_paper_source_checks_summary_json
            CHECK (summary_json IS NULL OR ISJSON(summary_json) = 1)
    );
END;
GO

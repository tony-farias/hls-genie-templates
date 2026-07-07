-- Salesforce Data Cloud dimensions (mocked) + HEDIS reference.
-- These tables represent the zero-copy foreign catalog federated from Salesforce
-- Data Cloud. The Lakeflow pipeline reads them as dim_member / dim_provider / dim_measure.
--
-- Seed files were uploaded by run_demo.sh to the landing volume under _seed/.
-- Params: ${CATALOG}, ${SCHEMA}, ${DC_SCHEMA}, ${VOLUME}

-- ---- member (Salesforce Data Cloud) --------------------------------------- --
CREATE TABLE IF NOT EXISTS ${CATALOG}.${DC_SCHEMA}.member (
  member_id            STRING,
  birth_date           DATE,
  sex                  STRING,
  state                STRING,
  county_fips          STRING,
  aid_category         STRING,
  chronic_conditions   STRING,
  preferred_language   STRING
) COMMENT 'Member dimension — Salesforce Data Cloud (zero-copy). Unified individual profile.';

INSERT OVERWRITE ${CATALOG}.${DC_SCHEMA}.member
SELECT member_id, CAST(birth_date AS DATE), sex, state, county_fips,
       aid_category, chronic_conditions, preferred_language
FROM read_files('/Volumes/${CATALOG}/${SCHEMA}/${VOLUME}/_seed/member.csv',
                format => 'csv', header => true);

-- ---- provider (Salesforce Data Cloud) ------------------------------------- --
CREATE TABLE IF NOT EXISTS ${CATALOG}.${DC_SCHEMA}.provider (
  provider_npi   STRING,
  specialty      STRING,
  provider_type  STRING,
  state          STRING,
  in_network     STRING
) COMMENT 'Provider dimension — Salesforce Data Cloud (zero-copy).';

INSERT OVERWRITE ${CATALOG}.${DC_SCHEMA}.provider
SELECT provider_npi, specialty, provider_type, state, in_network
FROM read_files('/Volumes/${CATALOG}/${SCHEMA}/${VOLUME}/_seed/provider.csv',
                format => 'csv', header => true);

-- ---- measure (HEDIS/CMS reference) ---------------------------------------- --
CREATE TABLE IF NOT EXISTS ${CATALOG}.${DC_SCHEMA}.measure (
  measure_id            STRING,
  measure_name          STRING,
  domain                STRING,
  regulatory_threshold  DOUBLE,
  reporting_direction   STRING,
  star_rating_flag      INT,
  high_priority_flag    INT,
  measurement_year      INT
) COMMENT 'HEDIS/CMS quality measure reference (18 measures).';

INSERT OVERWRITE ${CATALOG}.${DC_SCHEMA}.measure
SELECT measure_id, measure_name, domain, CAST(regulatory_threshold AS DOUBLE),
       reporting_direction, CAST(star_rating_flag AS INT), CAST(high_priority_flag AS INT),
       CAST(measurement_year AS INT)
FROM read_files('/Volumes/${CATALOG}/${SCHEMA}/${VOLUME}/_seed/measure.csv',
                format => 'csv', header => true);

-- HEDIS Quality demo — schemas + landing Volume.
-- Params substituted by run_demo.sh: ${CATALOG}, ${SCHEMA}, ${DC_SCHEMA}, ${VOLUME}

CREATE SCHEMA IF NOT EXISTS ${CATALOG}.${SCHEMA}
  COMMENT 'HEDIS Quality Measures demo — Lakeflow output (facts + measure performance).';

-- Schema standing in for the Salesforce Data Cloud zero-copy foreign catalog.
CREATE SCHEMA IF NOT EXISTS ${CATALOG}.${DC_SCHEMA}
  COMMENT 'Mock of Salesforce Data Cloud (zero-copy). In production this is a foreign catalog federated from Data Cloud.';

-- Managed Volume = the file landing zone Auto Loader watches.
CREATE VOLUME IF NOT EXISTS ${CATALOG}.${SCHEMA}.${VOLUME}
  COMMENT 'Landing zone for HEDIS source files (claims/, enrollment/).';

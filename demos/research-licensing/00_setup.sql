-- Research In-Licensing demo — schema + landing Volume.
-- Params substituted by run_demo.sh: ${CATALOG}, ${SCHEMA}, ${VOLUME}

CREATE SCHEMA IF NOT EXISTS ${CATALOG}.${SCHEMA}
  COMMENT 'In-licensing due-diligence demo — Lakeflow-ingested data room (docs + tables) for Genie Ontology.';

CREATE VOLUME IF NOT EXISTS ${CATALOG}.${SCHEMA}.${VOLUME}
  COMMENT 'Landing zone for the SharePoint-style in-licensing data room (data_room/).';

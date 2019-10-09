-- Copyright REFITT Team 2019. All rights reserved.
--
-- This program is free software: you can redistribute it and/or modify it under the
-- terms of the Apache License (v2.0) as published by the Apache Software Foundation.
--
-- This program is distributed in the hope that it will be useful, but WITHOUT ANY
-- WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
-- PARTICULAR PURPOSE. See the Apache License for more details.
--
-- You should have received a copy of the Apache License along with this program.
-- If not, see <https://www.apache.org/licenses/LICENSE-2.0>.

CREATE TABLE "Recommendation"."RecommendationObject"
(
    "RecommendationObjectID" bigserial NOT NULL,
    "RecommendationGroupID" bigint NOT NULL,
    "ObjectID" bigint NOT NULL,
    PRIMARY KEY ("RecommendationObjectID"),
    CONSTRAINT "RecommendationGroupID" FOREIGN KEY ("RecommendationGroupID")
        REFERENCES "Recommendation"."RecommendationGroup" ("RecommendationGroupID") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID,
    CONSTRAINT "ObjectID" FOREIGN KEY ("ObjectID")
        REFERENCES "Observation"."Object" ("ObjectID") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID
)
WITH (
    OIDS = FALSE
);

COMMENT ON TABLE "Recommendation"."RecommendationObject"
    IS 'Part of a "RecommendationGroup", from "Observation"."Object".';

COMMENT ON CONSTRAINT "RecommendationGroupID" ON "Recommendation"."RecommendationObject"
    IS 'References "RecommendationGroup"."RecommendationGroupID"';

COMMENT ON CONSTRAINT "ObjectID" ON "Recommendation"."RecommendationObject"
    IS 'References "Observation"."Object"."ObjectID"';

CREATE INDEX "RecommendationGroupID"
    ON "Recommendation"."RecommendationObject" USING btree
    ("RecommendationGroupID" ASC NULLS LAST)
    TABLESPACE pg_default;

CREATE INDEX "ObjectID"
    ON "Recommendation"."RecommendationObject" USING btree
    ("ObjectID" ASC NULLS LAST)
    TABLESPACE pg_default;
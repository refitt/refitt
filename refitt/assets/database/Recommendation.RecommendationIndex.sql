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

CREATE TABLE "Recommendation"."RecommendationIndex"
(
    "RecommendationIndexID" bigserial NOT NULL,
    "RecommendationIndex" json NOT NULL,
    "RecommendationGroupID" bigint NOT NULL,
    "UserID" bigint NOT NULL,
    PRIMARY KEY ("RecommendationIndexID"),
    CONSTRAINT "RecommendationGroupID" FOREIGN KEY ("RecommendationGroupID")
        REFERENCES "Recommendation"."RecommendationGroup" ("RecommendationGroupID") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID,
    CONSTRAINT "UserID" FOREIGN KEY ("UserID")
        REFERENCES "User"."User" ("UserID") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID
)
WITH (
    OIDS = FALSE
);

COMMENT ON TABLE "Recommendation"."RecommendationIndex"
    IS 'View of "ObjectID" from "RecommendationGroupID"';

COMMENT ON CONSTRAINT "RecommendationGroupID" ON "Recommendation"."RecommendationIndex"
    IS 'References "RecommendationGroup"."RecommendationGroupID"';

COMMENT ON CONSTRAINT "UserID" ON "Recommendation"."RecommendationIndex"
    IS 'References "User"."User"."UserID"';

CREATE INDEX "RecommendationGroupID"
    ON "Recommendation"."RecommendationIndex" USING btree
    ("RecommendationGroupID" ASC NULLS LAST)
    TABLESPACE pg_default;

CREATE INDEX "UserID"
    ON "Recommendation"."RecommendationIndex" USING btree
    ("UserID" ASC NULLS LAST)
    TABLESPACE pg_default;
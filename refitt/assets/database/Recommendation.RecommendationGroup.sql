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

CREATE TABLE "Recommendation"."Recommendation"
(
    "RecommendationGroupID" bigserial NOT NULL,
    "RecommendationGroupTime" timestamp with time zone NOT NULL,
    PRIMARY KEY ("RecommendationGroupID")
)
WITH (
    OIDS = FALSE
);

COMMENT ON TABLE "Recommendation"."Recommendation"
    IS 'Uniquely identifies a batch of recommendations.';
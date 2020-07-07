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

-- NOTES:
-- Before an observation:
--     The recommendation specifies "what" (object_id) needs to be observed by "who" (user_id),
--     "where" (facility_id), "which" filter (observation_type_id).
-- After an observation:
--     A user can "accept" or "reject" a recommendation which dictates what recommendation to
--     feed them next using the API. The observation_id is recorded after data is returned by
--     the user and can be considered complete.

CREATE TABLE IF NOT EXISTS "recommendation"."recommendation"
(
    "recommendation_id"         BIGSERIAL NOT NULL,
    "recommendation_group_id"   BIGINT    NOT NULL,
    "recommendation_time"       TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "recommendation_priority"   BIGINT    NOT NULL,
    "facility_id"               BIGINT    NOT NULL,
    "user_id"                   BIGINT    NOT NULL,
    "object_id"                 BIGINT    NOT NULL,
    "observation_type_id"       BIGINT    NOT NULL,
    "observation_id"            BIGINT,                 -- what they observed
    "predicted_observation_id"  BIGINT,                 -- what we predicted
    "recommendation_accepted"   BOOLEAN   NOT NULL DEFAULT FALSE,
    "recommendation_rejected"   BOOLEAN   NOT NULL DEFAULT FALSE,
    "recommendation_metadata"   JSONB     NOT NULL DEFAULT '{}'::jsonb,  -- e.g., {"seeing": 0.82, ...}

    PRIMARY KEY ("recommendation_id"),

    CONSTRAINT "recommendation_group_id" FOREIGN KEY ("recommendation_group_id")
        REFERENCES "recommendation"."recommendation_group" ("recommendation_group_id") MATCH FULL
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID,

    CONSTRAINT "facility_id" FOREIGN KEY ("facility_id")
        REFERENCES "profile"."facility" ("facility_id") MATCH FULL
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID,

    CONSTRAINT "user_id" FOREIGN KEY ("user_id")
        REFERENCES "profile"."user" ("user_id") MATCH FULL
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID,

    CONSTRAINT "object_id" FOREIGN KEY ("object_id")
        REFERENCES "observation"."object" ("object_id") MATCH FULL
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID,

    CONSTRAINT "observation_type_id" FOREIGN KEY ("observation_type_id")
        REFERENCES "observation"."observation_type" ("observation_type_id") MATCH FULL
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID,

    CONSTRAINT "observation_id" FOREIGN KEY ("observation_id")
        REFERENCES "observation"."observation" ("observation_id") MATCH FULL
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID,

    CONSTRAINT "predicted_observation_id" FOREIGN KEY ("predicted_observation_id")
        REFERENCES "observation"."observation" ("observation_id") MATCH FULL
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID
)
WITH (
    OIDS = FALSE
);

CREATE INDEX IF NOT EXISTS "recommendation_group_id"
    ON "recommendation"."recommendation" USING btree
    ("recommendation_group_id" ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS "facility_id"
    ON "recommendation"."recommendation" USING btree
    ("facility_id" ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS "user_id"
    ON "recommendation"."recommendation" USING btree
    ("user_id" ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS "object_id"
    ON "recommendation"."recommendation" USING btree
    ("object_id" ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS "observation_type_id"
    ON "recommendation"."recommendation" USING btree
    ("observation_type_id" ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS "predicted_observation_id"
    ON "recommendation"."recommendation" USING btree
    ("predicted_observation_id" ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS "recommendation_accepted"
    ON "recommendation"."recommendation" USING btree
    ("recommendation_accepted" ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS "recommendation_rejected"
    ON "recommendation"."recommendation" USING btree
    ("recommendation_rejected" ASC NULLS LAST);
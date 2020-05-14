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

CREATE TABLE IF NOT EXISTS "observation"."observation"
(
    "observation_id"        BIGSERIAL                NOT NULL,
    "object_id"             BIGINT                   NOT NULL,
    "observation_type_id"   BIGINT                   NOT NULL,
    "source_id"             BIGINT                   NOT NULL,
    "observation_time"      TIMESTAMP WITH TIME ZONE NOT NULL,
    "observation_value"     DOUBLE PRECISION         NOT NULL,
    "observation_error"     DOUBLE PRECISION,
    "observation_recorded"  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY ("observation_id"),

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

    CONSTRAINT "source_id" FOREIGN KEY ("source_id")
        REFERENCES "observation"."source" ("source_id") MATCH FULL
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID
)
WITH (
    OIDS = FALSE
);

CREATE INDEX IF NOT EXISTS "object_id"
    ON "observation"."observation" USING btree
    ("object_id" ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS "observation_type_id"
    ON "observation"."observation" USING btree
    ("observation_type_id" ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS "source_id"
    ON "observation"."observation" USING btree
    ("source_id" ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS "observation_time"
    ON "observation"."observation" USING btree
    ("observation_time" ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS "observation_recorded"
    ON "observation"."observation" USING btree
    ("observation_recorded" ASC NULLS LAST);
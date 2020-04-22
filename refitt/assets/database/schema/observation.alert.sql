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

CREATE TABLE IF NOT EXISTS "observation"."alert"
(
    "alert_id"       BIGSERIAL NOT NULL,
    "observation_id" BIGINT    NOT NULL,
    "alert_data"     JSONB     NOT NULL,

    PRIMARY KEY ("alert_id"),

    CONSTRAINT "observation_id" FOREIGN KEY ("observation_id")
        REFERENCES "observation"."observation" ("observation_id") MATCH FULL
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID
)
WITH (
    OIDS = FALSE
);

CREATE INDEX IF NOT EXISTS "observation_id"
    ON "observation"."alert" USING btree
    ("observation_id" ASC NULLS LAST);
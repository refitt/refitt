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

CREATE TABLE IF NOT EXISTS "model"."model"
(
    "model_id"       BIGSERIAL                NOT NULL,
    "type_id"        BIGINT                   NOT NULL,
    "model_name"     TEXT                     NOT NULL, -- e.g., "ae::prod"
    "model_hash"     CHARACTER(64)            NOT NULL, -- e.g., "ad3...d3v"
    "model_data"     BYTEA                    NOT NULL,
    "model_created"  TIMESTAMP WITH TIME ZONE NOT NULL,
    "model_accuracy" DOUBLE PRECISION,                  -- e.g., 0.84 (a percent)
    
    PRIMARY KEY ("model_id"),
	UNIQUE ("model_name"),

    CONSTRAINT "type_id" FOREIGN KEY ("type_id")
        REFERENCES "model"."type" ("type_id") MATCH FULL
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID
)
WITH (
    OIDS = FALSE
);

CREATE INDEX IF NOT EXISTS "type_id"
    ON "model"."model" USING btree
    ("type_id" ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS "model_hash"
    ON "model"."model" USING btree
    ("model_hash" ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS "model_created"
    ON "model"."model" USING btree
    ("model_created" ASC NULLS LAST);
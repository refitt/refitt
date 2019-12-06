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
    "model_id" BIGSERIAL NOT NULL,

    "model_type_id" BIGINT NOT NULL,

    "model_name" TEXT NOT NULL,
    "model_time" TIMESTAMP WITH TIME ZONE NOT NULL,
    "model_hash" CHARACTER(64),
    "model_data" BYTEA NOT NULL,
    "model_accuracy" DOUBLE PRECISION,
    
    PRIMARY KEY ("model_id"),
	UNIQUE("model_name"),

    CONSTRAINT "model_type_id" FOREIGN KEY ("model_type_id")
        REFERENCES "model"."model_type" ("model_type_id") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID
)
WITH (
    OIDS = FALSE
);

CREATE INDEX IF NOT EXISTS "model_type_id"
    ON "model"."model" USING btree
    ("model_type_id" ASC NULLS LAST);

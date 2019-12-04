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

CREATE TABLE IF NOT EXISTS "recommendation"."recommendation_object"
(
    "recommendation_object_id" bigserial NOT NULL,

    "recommendation_group_id" BIGINT NOT NULL,
    "object_id" BIGINT NOT NULL,

    PRIMARY KEY ("recommendation_object_id"),

    CONSTRAINT "recommendation_group_id" FOREIGN KEY ("recommendation_group_id")
        REFERENCES "recommendation"."recommendation_group" ("recommendation_group_id") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID,

    CONSTRAINT "object_id" FOREIGN KEY ("object_id")
        REFERENCES "observation"."object" ("object_id") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID
)
WITH (
    OIDS = FALSE
);

CREATE INDEX IF NOT EXISTS "recommendation_group_id"
    ON "recommendation"."recommendation_object" USING btree
    ("recommendation_group_id" ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS "object_id"
    ON "recommendation"."recommendation_object" USING btree
    ("object_id" ASC NULLS LAST);
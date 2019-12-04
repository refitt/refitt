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

CREATE TABLE IF NOT EXISTS "recommendation"."recommendation"
(
    "recommendation_id" bigserial NOT NULL,

    "recommendation_group_id" BIGINT NOT NULL,
    "user_id" BIGINT NOT NULL,

    PRIMARY KEY ("recommendation_id"),

    CONSTRAINT "recommendation_group_id" FOREIGN KEY ("recommendation_group_id")
        REFERENCES "recommendation"."recommendation_group" ("recommendation_group_id") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID,

    CONSTRAINT "user_id" FOREIGN KEY ("user_id")
        REFERENCES "user"."user" ("user_id") MATCH SIMPLE
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

CREATE INDEX IF NOT EXISTS "user_id"
    ON "recommendation"."recommendation" USING btree
    ("user_id" ASC NULLS LAST);
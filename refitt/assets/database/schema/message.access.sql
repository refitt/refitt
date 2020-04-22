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

CREATE TABLE IF NOT EXISTS "message"."access"
(
    "access_id"   BIGSERIAL NOT NULL,
    "consumer_id" BIGINT    NOT NULL,
    "topic_id"    BIGINT    NOT NULL,
    "message_id"  BIGINT    NOT NULL,
    "access_time" TIMESTAMP WITH TIME ZONE NOT NULL DEfAULT CURRENT_TIMESTAMP,

    PRIMARY KEY ("access_id"),

    CONSTRAINT "consumer_id" FOREIGN KEY ("consumer_id")
        REFERENCES "message"."consumer" ("consumer_id") MATCH FULL
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID,

    CONSTRAINT "topic_id" FOREIGN KEY ("topic_id")
        REFERENCES "message"."topic" ("topic_id") MATCH FULL
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID,

    CONSTRAINT "message_id" FOREIGN KEY ("message_id")
        REFERENCES "message"."message" ("message_id") MATCH FULL
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID
)
WITH (
    OIDS = FALSE
);

CREATE INDEX IF NOT EXISTS "consumer_id"
    ON "message"."access" USING btree
    ("consumer_id" ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS "topic_id"
    ON "message"."access" USING btree
    ("topic_id" ASC NULLS LAST);
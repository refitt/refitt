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

CREATE TABLE IF NOT EXISTS "message"."message"
(
    "message_id" BIGSERIAL NOT NULL,

    "message_topic_id" BIGINT NOT NULL,
    "message_level_id" BIGINT NOT NULL,
    "message_host_id" BIGINT NOT NULL,

    "message_time" TIMESTAMP WITH TIME ZONE NOT NULL,
    "message_content" TEXT NOT NULL,

    PRIMARY KEY ("message_id"),

    CONSTRAINT "message_topic_id" FOREIGN KEY ("message_topic_id")
        REFERENCES "message"."message_topic" ("message_topic_id") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID,

    CONSTRAINT "message_level_id" FOREIGN KEY ("message_level_id")
        REFERENCES "message"."message_level" ("message_level_id") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID,

    CONSTRAINT "message_host_id" FOREIGN KEY ("message_host_id")
        REFERENCES "message"."message_host" ("message_host_id") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID
)
WITH (
    OIDS = FALSE
);

CREATE INDEX IF NOT EXISTS "message_topic_id"
    ON "message"."message" USING btree
    ("message_topic_id" ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS "message_level_id"
    ON "message"."message" USING btree
    ("message_level_id" ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS "message_host_id"
    ON "message"."message" USING btree
    ("message_host_id" ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS "message_time"
    ON "message"."message" USING btree
    ("message_time" ASC NULLS LAST);
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

CREATE TABLE "Message"."Message"
(
    "MessageID" bigserial NOT NULL,
    "MessageTopicID" bigint NOT NULL,
    "MessageLevelID" bigint NOT NULL,
    "MessageHostID" bigint NOT NULL,
    "MessageTime" timestamp with time zone NOT NULL,
    "MessageContent" text NOT NULL,
    PRIMARY KEY ("MessageID"),
    CONSTRAINT "MessageTopicID" FOREIGN KEY ("MessageTopicID")
        REFERENCES "Message"."MessageTopic" ("MessageTopicID") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID,
    CONSTRAINT "MessageLevelID" FOREIGN KEY ("MessageLevelID")
        REFERENCES "Message"."MessageLevel" ("MessageLevelID") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID,
    CONSTRAINT "MessageHostID" FOREIGN KEY ("MessageHostID")
        REFERENCES "Message"."MessageHost" ("MessageHostID") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID
)
WITH (
    OIDS = FALSE
);

COMMENT ON TABLE "Message"."Message"
    IS 'Logging messages.';
COMMENT ON CONSTRAINT "MessageTopicID" ON "Message"."Message"
    IS 'References "Message"."MessageTopic". ("MessageTopicID").';
COMMENT ON CONSTRAINT "MessageLevelID" ON "Message"."Message"
    IS 'References "Message.MessageLevel" ("MessageLevelID").';
COMMENT ON CONSTRAINT "MessageHostID" ON "Message"."Message"
    IS 'References "Message"."MessageHost" ("MessageHostID").';